"""search: 기간/카테고리/타입/키워드/태그 조건 검색 (최신순)."""

from __future__ import annotations

import argparse

from budget_app.commands.listing import DEFAULT_LIMIT, latest, positive_int, print_rows
from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, command
from budget_app.errors import ValidationError
from budget_app.models import parse_category_name, parse_date, parse_type
from budget_app.services import SearchFilter, filter_transactions


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser("search", help="조건 검색 (최신순)", parents=[common])
    p.add_argument("--from", dest="date_from", help="시작일 YYYY-MM-DD (포함)")
    p.add_argument("--to", dest="date_to", help="종료일 YYYY-MM-DD (포함)")
    p.add_argument("--category", help="카테고리")
    p.add_argument("--type", help="income / expense")
    p.add_argument("--q", help="메모 키워드 (대소문자 무시)")
    p.add_argument("--tag", help="태그")
    p.add_argument("--limit", type=positive_int, default=DEFAULT_LIMIT, help=f"출력 개수 (기본 {DEFAULT_LIMIT})")
    p.set_defaults(handler=search)


def build_filter(args: argparse.Namespace) -> SearchFilter:
    flt = SearchFilter(
        date_from=parse_date(args.date_from) if args.date_from else None,
        date_to=parse_date(args.date_to) if args.date_to else None,
        category=parse_category_name(args.category) if args.category else None,
        type=parse_type(args.type) if args.type else None,
        keyword=args.q,
        tag=args.tag.strip() if args.tag else None,
    )
    if flt.date_from and flt.date_to and flt.date_from > flt.date_to:
        raise ValidationError("--from 이 --to 보다 늦습니다.", "예: --from 2024-01-01 --to 2024-01-31")
    return flt


@command
def search(ctx: AppContext, args: argparse.Namespace) -> int:
    flt = build_filter(args)
    matched = filter_transactions(ctx.transactions.iter_all(), flt)
    print_rows(latest(matched, args.limit), "조건에 맞는 거래가 없습니다.")
    return EXIT_OK
