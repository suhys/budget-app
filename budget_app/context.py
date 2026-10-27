"""AppContext: 저장 폴더를 받아 저장소 3개를 준비하고, 초기 실행을 처리한다."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from budget_app.storage import BudgetStore, CategoryStore, TransactionRepository

FILE_NAMES = {
    "transactions": "transactions.jsonl",
    "categories": "categories.jsonl",
    "budgets": "budgets.jsonl",
}


@dataclass
class AppContext:
    data_dir: Path
    transactions: TransactionRepository
    categories: CategoryStore
    budgets: BudgetStore

    @classmethod
    def open(cls, data_dir: Path) -> "AppContext":
        data_dir.mkdir(parents=True, exist_ok=True)
        _setup_logging(data_dir / "app.log")

        ctx = cls(
            data_dir=data_dir,
            transactions=TransactionRepository(data_dir / FILE_NAMES["transactions"]),
            categories=CategoryStore(data_dir / FILE_NAMES["categories"]),
            budgets=BudgetStore(data_dir / FILE_NAMES["budgets"]),
        )
        created = [
            name
            for name, f in [
                ("transactions", ctx.transactions.file),
                ("categories", ctx.categories.file),
                ("budgets", ctx.budgets.file),
            ]
            if f.ensure()
        ]
        if created:
            print(f"[초기화] 저장 파일을 생성했습니다: {data_dir.resolve()} ({', '.join(created)})")
        if ctx.categories.seed_defaults_if_empty():
            print(f"[초기화] 기본 카테고리를 등록했습니다: {', '.join(ctx.categories.list())}")
        return ctx


def _setup_logging(log_path: Path) -> None:
    logger = logging.getLogger("budget_app")
    if any(isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_path.resolve() for h in logger.handlers):
        return
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
