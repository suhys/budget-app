"""add: 대화형으로 거래 1건을 입력받아 저장한다."""

from __future__ import annotations

import argparse

from budget_app.commands.prompt import ask
from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, command
from budget_app.models import Transaction, parse_amount, parse_date, parse_tags, parse_type


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser("add", help="거래 추가 (대화형 입력)", parents=[common])
    p.set_defaults(handler=add)


@command
def add(ctx: AppContext, args: argparse.Namespace) -> int:
    date = ask("날짜(YYYY-MM-DD)", parse_date)
    tx_type = ask("타입(income/expense)", parse_type)
    print(f"  (카테고리: {', '.join(ctx.categories.list())})")
    category = ask("카테고리", ctx.categories.require)
    amount = ask("금액(양수)", parse_amount)
    memo = input("메모(선택): ").strip()
    tags = parse_tags(input("태그(쉼표로 구분, 없으면 엔터): "))

    tx = Transaction(
        id=ctx.transactions.next_id(),
        type=tx_type,
        date=date,
        amount=amount,
        category=category,
        memo=memo,
        tags=tags,
    )
    ctx.transactions.add(tx)
    print(f"[저장 완료] id={tx.id}")
    return EXIT_OK
