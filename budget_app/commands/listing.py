"""list: 최신순 거래 목록 (--limit N)."""

from __future__ import annotations

import argparse
import heapq
from collections.abc import Iterable

from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, command
from budget_app.models import Transaction

DEFAULT_LIMIT = 20


def positive_int(value: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"정수를 입력하세요: '{value}'") from None
    if n <= 0:
        raise argparse.ArgumentTypeError(f"1 이상이어야 합니다: {n}")
    return n


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser("list", help="거래 목록 (최신순)", parents=[common])
    p.add_argument("--limit", type=positive_int, default=DEFAULT_LIMIT, help=f"출력 개수 (기본 {DEFAULT_LIMIT})")
    p.set_defaults(handler=list_transactions)


def sort_key(tx: Transaction) -> tuple[str, str]:
    """최신순 기준: 날짜 → 같은 날짜면 id(나중에 입력한 것)."""
    return (tx.date, tx.id)


def latest(transactions: Iterable[Transaction], limit: int) -> list[Transaction]:
    """제너레이터를 받아 상위 limit개만 유지한다 (전체를 정렬하지 않음 → 메모리 O(limit))."""
    return heapq.nlargest(limit, transactions, key=sort_key)


def print_rows(rows: list[Transaction], empty_message: str) -> None:
    if not rows:
        print(empty_message)
        return
    for tx in rows:
        print(tx.format_row())


@command
def list_transactions(ctx: AppContext, args: argparse.Namespace) -> int:
    rows = latest(ctx.transactions.iter_all(), args.limit)
    print_rows(rows, "거래 내역이 없습니다. 'add' 로 첫 거래를 추가하세요.")
    return EXIT_OK
