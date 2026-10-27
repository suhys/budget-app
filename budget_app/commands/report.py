"""budget set/show + summary"""

from __future__ import annotations

import argparse
from datetime import date

from budget_app.commands.listing import positive_int
from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, command
from budget_app.errors import NotFoundError
from budget_app.models import parse_amount, parse_month
from budget_app.services import BUDGET_WARN_RATIO, MonthlySummary, monthly_summary

DEFAULT_TOP = 3


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p_sum = subparsers.add_parser("summary", help="월별 요약 + 예산 사용률", parents=[common])
    p_sum.add_argument("--month", help="YYYY-MM (기본: 이번 달)")
    p_sum.add_argument("--top", type=positive_int, default=DEFAULT_TOP, help=f"지출 TOP N (기본 {DEFAULT_TOP})")
    p_sum.set_defaults(handler=summary)

    p_bud = subparsers.add_parser("budget", help="월 예산 설정/조회", parents=[common])
    sub = p_bud.add_subparsers(dest="action", metavar="<action>", required=True)
    p_set = sub.add_parser("set", help="예산 설정 (같은 월이면 덮어씀)", parents=[common])
    p_set.add_argument("--month", required=True, help="YYYY-MM")
    p_set.add_argument("--amount", required=True, help="양의 정수")
    p_set.set_defaults(handler=budget_set)
    p_show = sub.add_parser("show", help="예산 조회", parents=[common])
    p_show.add_argument("--month", required=True, help="YYYY-MM")
    p_show.set_defaults(handler=budget_show)


def won(n: int) -> str:
    return f"{n:,}원"


def print_summary(s: MonthlySummary, top: int) -> None:
    print(f"[{s.month} 요약] 거래 {s.count}건")
    if s.count == 0:
        print("  해당 월의 거래가 없습니다.")
    print(f"총 수입: {won(s.income)}")
    print(f"총 지출: {won(s.expense)}")
    print(f"잔액: {won(s.balance)}")

    ratio = s.usage_ratio
    if s.budget is None:
        print("예산: 미설정 (budget set --month YYYY-MM --amount 금액)")
    else:
        print(f"예산: {won(s.budget)} (사용률 {ratio * 100:.1f}%)")
        if s.expense > s.budget:
            print(f"[경고] 예산을 {won(s.expense - s.budget)} 초과했습니다!")
        elif ratio is not None and ratio >= BUDGET_WARN_RATIO:
            print(f"[주의] 예산의 {ratio * 100:.0f}%를 사용했습니다. 남은 예산 {won(s.budget - s.expense)}")

    print(f"\n지출 TOP {top}")
    if not s.top_categories:
        print("  (지출 없음)")
    for rank, (category, amount) in enumerate(s.top_categories, start=1):
        print(f"{rank}) {category} {won(amount)}")


@command
def summary(ctx: AppContext, args: argparse.Namespace) -> int:
    month = parse_month(args.month) if args.month else date.today().strftime("%Y-%m")
    result = monthly_summary(ctx.transactions.iter_all(), month, args.top, ctx.budgets.get(month))
    print_summary(result, args.top)
    return EXIT_OK


@command
def budget_set(ctx: AppContext, args: argparse.Namespace) -> int:
    month = parse_month(args.month)
    amount = parse_amount(args.amount)
    ctx.budgets.set(month, amount)
    print(f"[저장 완료] {month} 예산 {won(amount)}")
    return EXIT_OK


@command
def budget_show(ctx: AppContext, args: argparse.Namespace) -> int:
    month = parse_month(args.month)
    amount = ctx.budgets.get(month)
    if amount is None:
        raise NotFoundError(f"{month} 예산이 설정되지 않았습니다.", f"budget set --month {month} --amount 500000")
    print(f"{month} 예산: {won(amount)}")
    return EXIT_OK
