"""category add / list / remove"""

from __future__ import annotations

import argparse

from budget_app.commands.prompt import ask
from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, command
from budget_app.errors import ValidationError
from budget_app.models import parse_category_name


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser("category", help="카테고리 관리 (add/list/remove)", parents=[common])
    sub = p.add_subparsers(dest="action", metavar="<action>", required=True)

    p_add = sub.add_parser("add", help="카테고리 추가 (이름 생략 시 대화형 입력)", parents=[common])
    p_add.add_argument("name", nargs="?", help="카테고리명")
    p_add.set_defaults(handler=category_add)

    p_list = sub.add_parser("list", help="카테고리 목록", parents=[common])
    p_list.set_defaults(handler=category_list)

    p_rm = sub.add_parser("remove", help="카테고리 삭제 (사용 중이면 거부)", parents=[common])
    p_rm.add_argument("name", help="삭제할 카테고리명")
    p_rm.set_defaults(handler=category_remove)

    p_rn = sub.add_parser("rename", help="[보너스] 카테고리 이름 변경 (거래 내역도 함께 변경)", parents=[common])
    p_rn.add_argument("old", help="기존 이름")
    p_rn.add_argument("new", help="새 이름")
    p_rn.set_defaults(handler=category_rename)


@command
def category_add(ctx: AppContext, args: argparse.Namespace) -> int:
    name = args.name if args.name else ask("카테고리명", parse_category_name)
    name = ctx.categories.add(name)
    print(f"[저장 완료] category={name}")
    return EXIT_OK


@command
def category_list(ctx: AppContext, args: argparse.Namespace) -> int:
    names = ctx.categories.list()
    if not names:
        print("등록된 카테고리가 없습니다. 'category add' 로 추가하세요.")
    for name in names:
        print(f"- {name}")
    return EXIT_OK


@command
def category_remove(ctx: AppContext, args: argparse.Namespace) -> int:
    name = ctx.categories.require(args.name)
    used = ctx.transactions.count_by_category(name)
    if used:
        raise ValidationError(
            f"'{name}' 카테고리를 사용 중인 거래가 {used}건 있어 삭제할 수 없습니다.",
            f"해당 거래를 수정/삭제하거나 'category rename {name} <새이름>' 으로 이름을 바꾸세요.",
        )
    ctx.categories.remove(name)
    print(f"[삭제 완료] category={name}")
    return EXIT_OK


@command
def category_rename(ctx: AppContext, args: argparse.Namespace) -> int:
    old = ctx.categories.require(args.old)
    new = ctx.categories.rename(old, args.new)
    changed = ctx.transactions.rename_category(old, new)
    print(f"[변경 완료] {old} -> {new} (거래 {changed}건 함께 변경)")
    return EXIT_OK
