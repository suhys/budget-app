"""CLI 계층: 명령어를 파싱하고 각 command 모듈의 handler로 위임한다.

새 명령을 추가할 때는 commands/ 에 모듈을 만들고 COMMAND_MODULES에 한 줄만 추가한다.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from budget_app.commands import add, category, listing
from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, handle_errors

DEFAULT_DATA_DIR = Path("data")

COMMAND_MODULES = [add, listing, category]


def build_parser() -> argparse.ArgumentParser:
    # 모든 하위 명령이 공유하는 옵션 (명령 뒤에 써도 동작하도록 parent로 전달)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--data-dir",
        type=Path,
        # SUPPRESS: 하위 parser의 기본값이 상위에서 준 값을 덮어쓰지 않도록 한다
        default=argparse.SUPPRESS,
        help="저장 폴더 경로 (기본: ./data)",
    )

    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="나만의 용돈 기입장 - 콘솔 가계부",
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for module in COMMAND_MODULES:
        module.register(subparsers, common)
    return parser


@handle_errors
def _run(args: argparse.Namespace) -> int:
    ctx = AppContext.open(getattr(args, "data_dir", DEFAULT_DATA_DIR))
    return args.handler(ctx, args)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "handler", None):
        parser.print_help()
        return EXIT_OK
    return _run(args)
