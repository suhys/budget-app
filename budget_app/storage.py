"""저장소 계층: JSONL 파일 입출력만 담당한다.

- 포맷: JSONL (한 줄 = JSON 객체 1개)
- 파일 3개로 분리: transactions.jsonl / categories.jsonl / budgets.jsonl
- 읽기는 항상 제너레이터(yield)로 한 줄씩 → 파일이 커져도 메모리 사용량이 일정
- 수정/삭제는 '임시 파일에 다시 쓰고 os.replace로 교체' → 중간에 죽어도 원본이 깨지지 않음
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

from budget_app.errors import NotFoundError, StorageError, ValidationError
from budget_app.models import Transaction, parse_category_name

DEFAULT_CATEGORIES: tuple[str, ...] = ("food", "transport", "rent", "shopping", "salary", "allowance", "etc")
ID_PREFIX = "TX-"


class JsonlFile:
    """JSONL 파일 하나를 감싸는 저수준 클래스."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def ensure(self) -> bool:
        """파일이 없으면 빈 파일을 만든다. 새로 만들었으면 True."""
        if self.path.exists():
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()
        return True

    def iter_records(self) -> Iterator[dict[str, Any]]:
        """파일을 한 줄씩 읽어 dict를 하나씩 yield한다 (전체를 메모리에 올리지 않음)."""
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    raise StorageError(
                        f"{self.path.name} {line_no}번째 줄이 손상되었습니다.",
                        f"해당 줄을 수정/삭제하거나 backup 폴더에서 복원하세요: {self.path}",
                    ) from None

    def append(self, record: dict[str, Any]) -> None:
        """기존 내용을 읽지 않고 맨 끝에 한 줄만 추가한다."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def rewrite(self, records: Iterable[dict[str, Any]]) -> None:
        """records(제너레이터 가능)를 임시 파일에 쓴 뒤 원본과 원자적으로 교체한다."""
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(tmp, self.path)


class TransactionRepository:
    """거래 내역 저장소. Transaction 객체 단위로 읽고 쓴다."""

    def __init__(self, path: Path) -> None:
        self.file = JsonlFile(path)

    def iter_all(self) -> Iterator[Transaction]:
        """모든 거래를 파일 순서대로 하나씩 yield (스트리밍)."""
        for record in self.file.iter_records():
            try:
                yield Transaction.from_dict(record)
            except ValidationError as e:
                raise StorageError(
                    f"transactions 파일에 잘못된 데이터가 있습니다: {e.message}",
                    f"id={record.get('id')} 줄을 확인하세요.",
                ) from None

    def next_id(self) -> str:
        """가장 큰 번호 + 1. 파일을 스트리밍하며 최댓값만 기억한다."""
        max_no = 0
        for tx in self.iter_all():
            try:
                max_no = max(max_no, int(tx.id.removeprefix(ID_PREFIX)))
            except ValueError:
                continue
        return f"{ID_PREFIX}{max_no + 1:06d}"

    def add(self, tx: Transaction) -> None:
        self.file.append(tx.to_dict())

    def get(self, tx_id: str) -> Transaction:
        for tx in self.iter_all():
            if tx.id == tx_id:
                return tx
        raise NotFoundError(f"존재하지 않는 거래 id입니다: {tx_id}", "list 명령으로 id를 확인하세요.")

    def replace(self, tx_id: str, transform: Callable[[Transaction], Transaction | None]) -> Transaction:
        """id가 일치하는 거래에 transform을 적용해 파일을 다시 쓴다.

        transform이 None을 반환하면 그 거래는 삭제된다.
        읽기(제너레이터) → 변환 → 임시 파일 쓰기가 한 줄 단위로 흘러가므로 메모리에 전체를 올리지 않는다.
        """
        self.get(tx_id)  # 없으면 여기서 NotFoundError (파일은 건드리지 않음)
        target: list[Transaction] = []

        def stream() -> Iterator[dict[str, Any]]:
            for tx in self.iter_all():
                if tx.id == tx_id:
                    target.append(tx)
                    new_tx = transform(tx)
                    if new_tx is None:
                        continue
                    yield new_tx.to_dict()
                else:
                    yield tx.to_dict()

        self.file.rewrite(stream())
        return target[0]

    def delete(self, tx_id: str) -> Transaction:
        return self.replace(tx_id, lambda tx: None)

    def count_by_category(self, category: str) -> int:
        return sum(1 for tx in self.iter_all() if tx.category == category)

    def rename_category(self, old: str, new: str) -> int:
        changed = 0

        def stream() -> Iterator[dict[str, Any]]:
            nonlocal changed
            for tx in self.iter_all():
                if tx.category == old:
                    tx.category = new
                    changed += 1
                yield tx.to_dict()

        self.file.rewrite(stream())
        return changed


class CategoryStore:
    """카테고리 목록. 한 줄 = {"name": "food"}."""

    def __init__(self, path: Path) -> None:
        self.file = JsonlFile(path)

    def seed_defaults_if_empty(self) -> bool:
        """(안 A) 카테고리 파일이 비어 있으면 기본 카테고리를 자동 생성한다."""
        if any(True for _ in self.file.iter_records()):
            return False
        self.file.rewrite({"name": name} for name in DEFAULT_CATEGORIES)
        return True

    def list(self) -> list[str]:
        return [str(r["name"]) for r in self.file.iter_records()]

    def exists(self, name: str) -> bool:
        return any(r["name"] == name for r in self.file.iter_records())

    def require(self, name: str) -> str:
        """존재하는 카테고리면 그대로 반환, 아니면 NotFoundError."""
        name = parse_category_name(name)
        if not self.exists(name):
            raise NotFoundError(
                f"존재하지 않는 카테고리입니다: '{name}'",
                f"사용 가능: {', '.join(self.list())} / 새로 만들려면: category add {name}",
            )
        return name

    def add(self, name: str) -> str:
        name = parse_category_name(name)
        if self.exists(name):
            raise ValidationError(f"이미 존재하는 카테고리입니다: '{name}'")
        self.file.append({"name": name})
        return name

    def remove(self, name: str) -> None:
        name = self.require(name)
        self.file.rewrite(r for r in self.file.iter_records() if r["name"] != name)

    def rename(self, old: str, new: str) -> str:
        old = self.require(old)
        new = parse_category_name(new)
        if self.exists(new):
            raise ValidationError(f"이미 존재하는 카테고리입니다: '{new}'")
        self.file.rewrite({"name": new if r["name"] == old else r["name"]} for r in self.file.iter_records())
        return new


class BudgetStore:
    """월별 예산. 한 줄 = {"month": "2024-01", "amount": 500000}."""

    def __init__(self, path: Path) -> None:
        self.file = JsonlFile(path)

    def get(self, month: str) -> int | None:
        for r in self.file.iter_records():
            if r["month"] == month:
                return int(r["amount"])
        return None

    def set(self, month: str, amount: int) -> None:
        """같은 월이 있으면 덮어쓰고(upsert), 없으면 추가한다."""
        found = False

        def stream() -> Iterator[dict[str, Any]]:
            nonlocal found
            for r in self.file.iter_records():
                if r["month"] == month:
                    found = True
                    yield {"month": month, "amount": amount}
                else:
                    yield r
            if not found:
                yield {"month": month, "amount": amount}

        self.file.rewrite(stream())
