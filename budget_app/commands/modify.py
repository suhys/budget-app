"""update / delete

update 방식은 '(안 A) 옵션 방식'으로 고정한다:
    update --id <id> [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]
지정한 필드만 바뀌고 나머지는 그대로 유지된다.
"""

from __future__ import annotations

import argparse
from dataclasses import replace

from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, command
from budget_app.errors import ValidationError
from budget_app.models import Transaction, parse_amount, parse_date, parse_tags, parse_type


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p_up = subparsers.add_parser("update", help="거래 수정 (옵션 방식)", parents=[common])
    p_up.add_argument("--id", required=True, help="수정할 거래 id (예: TX-000012)")
    p_up.add_argument("--date", help="YYYY-MM-DD")
    p_up.add_argument("--type", help="income / expense")
    p_up.add_argument("--category", help="등록된 카테고리")
    p_up.add_argument("--amount", help="양의 정수")
    p_up.add_argument("--memo", help="메모 (빈 문자열 \"\" 이면 삭제)")
    p_up.add_argument("--tags", help="쉼표로 구분 (빈 문자열 \"\" 이면 삭제)")
    p_up.set_defaults(handler=update)

    p_del = subparsers.add_parser("delete", help="거래 삭제", parents=[common])
    p_del.add_argument("--id", required=True, help="삭제할 거래 id")
    p_del.set_defaults(handler=delete)


def collect_changes(ctx: AppContext, args: argparse.Namespace) -> dict[str, object]:
    """입력된 옵션만 검증해 {필드: 새 값} 으로 모은다. 파일을 쓰기 전에 모두 검증한다."""
    changes: dict[str, object] = {}
    if args.date is not None:
        changes["date"] = parse_date(args.date)
    if args.type is not None:
        changes["type"] = parse_type(args.type)
    if args.category is not None:
        changes["category"] = ctx.categories.require(args.category)
    if args.amount is not None:
        changes["amount"] = parse_amount(args.amount)
    if args.memo is not None:
        changes["memo"] = args.memo.strip()
    if args.tags is not None:
        changes["tags"] = parse_tags(args.tags)
    if not changes:
        raise ValidationError(
            "수정할 항목이 없습니다.",
            "예: update --id TX-000001 --amount 12000 --memo 저녁",
        )
    return changes


@command
def update(ctx: AppContext, args: argparse.Namespace) -> int:
    changes = collect_changes(ctx, args)

    def apply(tx: Transaction) -> Transaction:
        return replace(tx, **changes)  # 원본은 그대로, 바뀐 필드만 반영한 새 객체

    before = ctx.transactions.replace(args.id, apply)
    after = replace(before, **changes)
    print(f"[수정 완료] id={args.id}")
    print(f"  전: {before.format_row()}")
    print(f"  후: {after.format_row()}")
    return EXIT_OK


@command
def delete(ctx: AppContext, args: argparse.Namespace) -> int:
    removed = ctx.transactions.delete(args.id)
    print(f"[삭제 완료] {removed.format_row()}")
    return EXIT_OK
