"""표준 라이브러리 unittest만 사용한다. 실행: python -m unittest -v"""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from budget_app.cli import main
from budget_app.errors import ValidationError
from budget_app.models import parse_amount, parse_date, parse_type
from budget_app.storage import TransactionRepository


def run(data_dir: Path, *argv: str, inputs: list[str] | None = None) -> tuple[int, str]:
    """CLI를 실행하고 (종료 코드, 출력)을 돌려준다. inputs는 input()에 차례로 들어갈 값."""
    buf = io.StringIO()
    with redirect_stdout(buf), patch("builtins.input", side_effect=inputs or []):
        code = main([*argv, "--data-dir", str(data_dir)])
    return code, buf.getvalue()


def add(data_dir: Path, date: str, tx_type: str, category: str, amount: str, memo: str = "", tags: str = "") -> str:
    _, out = run(data_dir, "add", inputs=[date, tx_type, category, amount, memo, tags])
    return out


class ValidatorTest(unittest.TestCase):
    def test_invalid_values_raise(self) -> None:
        for func, value in [(parse_date, "2024-13-40"), (parse_amount, "0"), (parse_amount, "-1"),
                            (parse_amount, "abc"), (parse_type, "gift")]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                func(value)

    def test_amount_accepts_commas(self) -> None:
        self.assertEqual(parse_amount("15,000"), 15000)


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_first_run_creates_three_files_and_default_categories(self) -> None:
        code, out = run(self.dir, "category", "list")
        self.assertEqual(code, 0)
        for name in ("transactions", "categories", "budgets"):
            self.assertTrue((self.dir / f"{name}.jsonl").exists())
        self.assertIn("- food", out)

    def test_add_reprompts_on_invalid_date_then_saves(self) -> None:
        _, out = run(self.dir, "add", inputs=["2024-13-40", "2024-01-15", "expense", "food", "15000", "점심", "meal"])
        self.assertIn("[오류] 날짜 형식", out)
        self.assertIn("[저장 완료] id=TX-000001", out)

    def test_list_is_newest_first_with_limit(self) -> None:
        add(self.dir, "2024-01-12", "expense", "transport", "20000")
        add(self.dir, "2024-01-15", "expense", "food", "15000")
        add(self.dir, "2024-01-14", "income", "salary", "3000000")
        _, out = run(self.dir, "list", "--limit", "2")
        lines = out.strip().splitlines()[-2:]
        self.assertTrue(lines[0].startswith("TX-000002 | 2024-01-15"))
        self.assertTrue(lines[1].startswith("TX-000003 | 2024-01-14"))

    def test_search_filters(self) -> None:
        add(self.dir, "2024-01-15", "expense", "food", "15000", "Lunch", "meal")
        add(self.dir, "2024-02-01", "expense", "food", "9000", "dinner")
        _, out = run(self.dir, "search", "--q", "lunch", "--tag", "meal", "--to", "2024-01-31")
        self.assertIn("TX-000001", out)
        self.assertNotIn("TX-000002", out)

    def test_update_and_delete_missing_id_returns_nonzero(self) -> None:
        add(self.dir, "2024-01-15", "expense", "food", "15000")
        code, out = run(self.dir, "update", "--id", "TX-000001", "--amount", "12000")
        self.assertEqual(code, 0)
        self.assertEqual(next(TransactionRepository(self.dir / "transactions.jsonl").iter_all()).amount, 12000)
        code, out = run(self.dir, "delete", "--id", "TX-999999")
        self.assertNotEqual(code, 0)
        self.assertIn("[힌트]", out)
        self.assertNotIn("Traceback", out)

    def test_summary_matches_spec_example(self) -> None:
        for date, t, c, a in [("2024-01-14", "income", "salary", "3000000"), ("2024-01-03", "expense", "rent", "150000"),
                              ("2024-01-15", "expense", "food", "45000"), ("2024-01-12", "expense", "transport", "20000")]:
            add(self.dir, date, t, c, a)
        run(self.dir, "budget", "set", "--month", "2024-01", "--amount", "500000")
        _, out = run(self.dir, "summary", "--month", "2024-01", "--top", "3")
        self.assertIn("잔액: 2,785,000원", out)
        self.assertIn("사용률 43.0%", out)
        self.assertIn("1) rent 150,000원", out)

    def test_budget_over_warning(self) -> None:
        add(self.dir, "2024-01-03", "expense", "rent", "600000")
        run(self.dir, "budget", "set", "--month", "2024-01", "--amount", "500000")
        _, out = run(self.dir, "summary", "--month", "2024-01")
        self.assertIn("[경고]", out)

    def test_category_in_use_cannot_be_removed(self) -> None:
        add(self.dir, "2024-01-15", "expense", "food", "15000")
        code, _ = run(self.dir, "category", "remove", "food")
        self.assertEqual(code, 1)

    def test_export_import_roundtrip(self) -> None:
        add(self.dir, "2024-01-15", "expense", "food", "15000", "친구, 점심", "meal,lunch")
        csv_path = self.dir / "out.csv"
        run(self.dir, "export", "--out", str(csv_path), "--month", "2024-01")
        other = self.dir / "other"
        _, out = run(other, "import", "--from", str(csv_path))
        self.assertIn("imported=1, skipped=0", out)
        tx = next(TransactionRepository(other / "transactions.jsonl").iter_all())
        self.assertEqual((tx.memo, tx.tags), ("친구, 점심", ["meal", "lunch"]))

    def test_corrupted_line_reports_error_without_traceback(self) -> None:
        add(self.dir, "2024-01-15", "expense", "food", "15000")
        with (self.dir / "transactions.jsonl").open("a", encoding="utf-8") as f:
            f.write("{broken\n")
        code, out = run(self.dir, "list")
        self.assertEqual(code, 1)
        self.assertIn("2번째 줄이 손상", out)


if __name__ == "__main__":
    unittest.main()
