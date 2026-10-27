"""import / export (CSV)

CSV 스키마 (UTF-8, 첫 줄 헤더):
    date,type,category,amount,memo,tags
    - date, type, category, amount 필수 / memo, tags 선택
    - tags는 쉼표 구분 → CSV 셀 안에서는 따옴표로 감싼다 ("meal,lunch")
id는 CSV에 포함하지 않는다. import 시 새 id가 발급된다.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from budget_app.context import AppContext
from budget_app.decorators import EXIT_OK, command
from budget_app.errors import AppError, ValidationError
from budget_app.models import Transaction, parse_amount, parse_date, parse_month, parse_tags, parse_type
from budget_app.services import CSV_COLUMNS, REQUIRED_COLUMNS, SearchFilter, filter_transactions, to_csv_row

MAX_REPORTED_ERRORS = 10


def register(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    p_exp = subparsers.add_parser("export", help="CSV로 내보내기", parents=[common])
    p_exp.add_argument("--out", required=True, type=Path, help="저장할 CSV 경로")
    p_exp.add_argument("--month", help="YYYY-MM (--from/--to 와 함께 쓸 수 없음)")
    p_exp.add_argument("--from", dest="date_from", help="시작일 YYYY-MM-DD")
    p_exp.add_argument("--to", dest="date_to", help="종료일 YYYY-MM-DD")
    p_exp.set_defaults(handler=export_csv)

    p_imp = subparsers.add_parser("import", help="CSV에서 가져오기", parents=[common])
    p_imp.add_argument("--from", dest="source", required=True, type=Path, help="읽을 CSV 경로")
    p_imp.set_defaults(handler=import_csv)


def export_filter(args: argparse.Namespace) -> SearchFilter:
    if args.month and (args.date_from or args.date_to):
        raise ValidationError("--month 와 --from/--to 는 함께 쓸 수 없습니다.", "둘 중 하나만 지정하세요.")
    if args.month:
        month = parse_month(args.month)
        return SearchFilter(date_from=f"{month}-01", date_to=f"{month}-31")
    return SearchFilter(
        date_from=parse_date(args.date_from) if args.date_from else None,
        date_to=parse_date(args.date_to) if args.date_to else None,
    )


@command
def export_csv(ctx: AppContext, args: argparse.Namespace) -> int:
    flt = export_filter(args)
    count = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        # 제너레이터 → 한 줄씩 바로 CSV로 기록 (전체를 메모리에 모으지 않음)
        for tx in filter_transactions(ctx.transactions.iter_all(), flt):
            writer.writerow(to_csv_row(tx))
            count += 1
    print(f"[완료] {args.out} ({count} records)")
    return EXIT_OK


def row_to_transaction(ctx: AppContext, row: dict[str, str], tx_id: str) -> Transaction:
    return Transaction(
        id=tx_id,
        date=parse_date(row.get("date") or ""),
        type=parse_type(row.get("type") or ""),
        category=ctx.categories.require(row.get("category") or ""),
        amount=parse_amount(row.get("amount") or ""),
        memo=(row.get("memo") or "").strip(),
        tags=parse_tags(row.get("tags") or ""),
    )


@command
def import_csv(ctx: AppContext, args: argparse.Namespace) -> int:
    if not args.source.exists():
        raise ValidationError(f"파일을 찾을 수 없습니다: {args.source}", "경로를 확인하세요.")

    imported = skipped = 0
    errors: list[str] = []
    next_no = int(ctx.transactions.next_id().removeprefix("TX-"))

    # utf-8-sig: 엑셀이 붙이는 BOM이 있어도 첫 컬럼명이 깨지지 않게 한다
    with args.source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValidationError(
                f"CSV 헤더에 필수 컬럼이 없습니다: {', '.join(missing)}",
                f"첫 줄을 다음과 같이 맞추세요: {','.join(CSV_COLUMNS)}",
            )
        for line_no, row in enumerate(reader, start=2):  # 1번 줄은 헤더
            try:
                tx = row_to_transaction(ctx, row, f"TX-{next_no:06d}")
            except AppError as e:  # 잘못된 행은 건너뛰고 계속 진행
                skipped += 1
                errors.append(f"  {line_no}번째 줄: {e.message}")
                continue
            ctx.transactions.add(tx)
            next_no += 1
            imported += 1

    print(f"[완료] imported={imported}, skipped={skipped}")
    for msg in errors[:MAX_REPORTED_ERRORS]:
        print(msg)
    if len(errors) > MAX_REPORTED_ERRORS:
        print(f"  ... 외 {len(errors) - MAX_REPORTED_ERRORS}건")
    return EXIT_OK
