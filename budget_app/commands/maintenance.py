"""[보너스] backup: 저장 파일 3개를 시각별 폴더로 복사한다."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime

from budget_app.context import FILE_NAMES, AppContext
from budget_app.decorators import EXIT_OK, command


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser("backup", help="저장 파일 백업 (data/backups/<시각>/)", parents=[common])
    p.set_defaults(handler=backup)


@command
def backup(ctx: AppContext, args: argparse.Namespace) -> int:
    target = ctx.data_dir / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    target.mkdir(parents=True, exist_ok=True)
    for file_name in FILE_NAMES.values():
        shutil.copy2(ctx.data_dir / file_name, target / file_name)
    print(f"[백업 완료] {target}")
    print("[복원 방법] 이 폴더의 .jsonl 파일 3개를 data 폴더에 덮어쓰세요.")
    return EXIT_OK
