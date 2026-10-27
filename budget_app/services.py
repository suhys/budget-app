"""서비스 계층: 저장소에서 꺼낸 데이터로 '업무 규칙'을 계산한다.

파일 형식(JSONL)도, 화면 출력도 모른다. 제너레이터를 받아 결과 값만 돌려준다.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from budget_app.models import Transaction


@dataclass(frozen=True)
class SearchFilter:
    """search 조건. None이면 해당 조건은 검사하지 않는다."""

    date_from: str | None = None
    date_to: str | None = None
    category: str | None = None
    type: str | None = None
    keyword: str | None = None
    tag: str | None = None

    def matches(self, tx: Transaction) -> bool:
        if self.date_from and tx.date < self.date_from:
            return False
        if self.date_to and tx.date > self.date_to:
            return False
        if self.category and tx.category != self.category:
            return False
        if self.type and tx.type != self.type:
            return False
        if self.keyword and self.keyword.lower() not in tx.memo.lower():
            return False
        if self.tag and self.tag not in tx.tags:
            return False
        return True


def filter_transactions(transactions: Iterable[Transaction], flt: SearchFilter) -> Iterator[Transaction]:
    """조건에 맞는 거래만 통과시키는 제너레이터 (필터 체인)."""
    return (tx for tx in transactions if flt.matches(tx))
