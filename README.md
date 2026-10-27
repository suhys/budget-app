# 나만의 용돈 기입장 (budget_app)

파일 입출력 기반의 콘솔 가계부입니다. 수입/지출 기록, 검색, 월별 요약, 예산 경고, 카테고리 관리, CSV 가져오기/내보내기를 지원합니다.
표준 라이브러리만 사용합니다 (`pip install` 불필요).

## 실행 방법

- Python 3.10 이상
- 저장소 루트(이 README가 있는 폴더)에서 실행합니다.

```bash
python -m budget_app --help              # 전체 명령 목록
python -m budget_app <command> --help    # 명령별 사용법
python -m unittest -v                    # 테스트 실행
```

Windows에서 `python`이 안 되면 `py -m budget_app ...` 를 사용하세요.

## 저장 파일 위치 / 형식

| 항목 | 내용 |
|---|---|
| 기본 폴더 | `./data` (모든 명령에서 `--data-dir <경로>` 로 변경 가능) |
| 포맷 | JSONL (한 줄 = JSON 객체 1개, UTF-8) |
| `transactions.jsonl` | 거래 내역 `{"id","type","date","amount","category","memo","tags"}` |
| `categories.jsonl` | 카테고리 `{"name"}` |
| `budgets.jsonl` | 월 예산 `{"month","amount"}` |
| `app.log` | 실행 로그 (명령 시작/종료/실행 시간/오류 상세) |
| `backups/<시각>/` | `backup` 명령으로 만든 백업 |

**초기 실행**: 파일이 없으면 자동 생성하고 `[초기화]` 안내를 출력합니다. 카테고리 파일이 비어 있으면 기본 카테고리(food, transport, rent, shopping, salary, allowance, etc)를 자동 등록합니다 (안 A).

## 주요 명령 예시

```bash
# 거래 추가 (대화형)
$ python -m budget_app add
날짜(YYYY-MM-DD): 2024-01-15
타입(income/expense): expense
  (카테고리: food, transport, rent, shopping, salary, allowance, etc)
카테고리: food
금액(양수): 15000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): meal
[저장 완료] id=TX-000001

# 목록 (최신순)
$ python -m budget_app list --limit 3

# 검색 (조건은 모두 선택, 함께 쓰면 AND)
$ python -m budget_app search --from 2024-01-01 --to 2024-01-31 --category food --type expense --q 점심 --tag meal

# 수정 (옵션 방식으로 고정: 지정한 필드만 변경)
$ python -m budget_app update --id TX-000001 --amount 12000 --memo 저녁
# 삭제
$ python -m budget_app delete --id TX-000001

# 예산 + 월별 요약
$ python -m budget_app budget set --month 2024-01 --amount 500000
$ python -m budget_app budget show --month 2024-01
$ python -m budget_app summary --month 2024-01 --top 3

# 카테고리
$ python -m budget_app category add hobby      # 이름 생략 시 대화형 입력
$ python -m budget_app category list
$ python -m budget_app category remove hobby   # 사용 중이면 거부
$ python -m budget_app category rename food meal   # [보너스] 거래 내역도 함께 변경

# CSV
$ python -m budget_app export --out export.csv --month 2024-01
$ python -m budget_app export --out export.csv --from 2024-01-01 --to 2024-03-31
$ python -m budget_app import --from samples/import_sample.csv

# [보너스] 백업
$ python -m budget_app backup
```

## import/export CSV 스키마

| column | required | 설명 |
|---|---|---|
| date | Y | YYYY-MM-DD |
| type | Y | income / expense |
| category | Y | 등록된 카테고리 |
| amount | Y | 양수 정수 |
| memo | N | 문자열 |
| tags | N | 쉼표(,)로 구분. 셀 안에 쉼표가 있으므로 `"meal,lunch"` 처럼 따옴표로 감쌈 |

- 인코딩: UTF-8 (import는 엑셀의 BOM도 허용), 첫 줄은 헤더
- `id`는 CSV에 넣지 않습니다. import 시 새 id가 발급됩니다.
- import 정책: **잘못된 행은 건너뛰고 나머지는 저장** → `imported=N, skipped=M` + 건너뛴 줄 번호와 사유 출력
- 필수 컬럼이 헤더에 없으면 아무것도 저장하지 않고 오류 종료
- 예시 파일: `samples/import_sample.csv` (정상 5행 + 오류 3행)

## 정책 정리

| 항목 | 정책 |
|---|---|
| 입력 방식 | `add`, `category add`(이름 생략 시)는 대화형. 나머지는 옵션 방식 |
| update | **옵션 방식(안 A)으로 고정**. 수정할 옵션이 하나도 없으면 오류 |
| 잘못된 입력(대화형) | 원인 + 힌트를 보여주고 같은 항목을 다시 입력받음 |
| 잘못된 입력(옵션) | 원인 + 힌트 출력 후 종료 코드 1 |
| 없는 id | update/delete 모두 "존재하지 않는 거래 id" + 힌트, 종료 코드 1 |
| 사용 중 카테고리 삭제 | 거부 (rename 사용 안내) |
| 동일 월 예산 재설정 | 덮어씀 |
| 예산 경고 | 사용률 80% 이상 `[주의]`, 100% 초과 `[경고]` + 초과 금액 |
| 오류 출력 | 스택트레이스 없이 `[오류] 원인` / `[힌트] 해결 방법`. 예상치 못한 오류는 `app.log`에 상세 기록 |
| 종료 코드 | 정상 0 / 오류 1 / 옵션 형식 오류 2(argparse) / Ctrl+C·EOF 130 |

## 구조

```
budget_app/
├── __main__.py        # python -m budget_app 진입점
├── cli.py             # [CLI] 인자 파싱 → 명령 handler로 위임
├── commands/          # [CLI] 명령별 handler (입출력/출력 형식 담당)
│   ├── add.py  listing.py  search.py  modify.py
│   ├── report.py (summary/budget)  category.py
│   ├── transfer.py (import/export)  maintenance.py (backup)
│   └── prompt.py      # 대화형 재입력 도우미
├── services.py        # [서비스] 검색 필터, 월별 집계, CSV 행 변환
├── storage.py         # [저장소] JSONL 읽기(제너레이터)/쓰기(원자적 교체)
├── models.py          # [모델] Transaction dataclass + 값 검증
├── decorators.py      # 공통 관심사: 예외 처리 / 실행 로그 / 실행 시간
├── context.py         # 저장소 3개 준비 + 초기 실행 처리
└── errors.py          # AppError(message, hint)
tests/test_app.py      # unittest 12개
samples/import_sample.csv
```

| 계층 | 책임 | 모르는 것 |
|---|---|---|
| 모델 | 값이 올바른가 | 파일, 화면 |
| 저장소 | 어떻게 저장/읽는가 (JSONL) | 업무 규칙, 화면 |
| 서비스 | 무엇을 계산하는가 (필터, 합계, TOP N) | 파일 형식, 화면 |
| CLI | 무엇을 입력받고 어떻게 보여주는가 | 파일 형식 |

## 설계 노트

**제너레이터 스트리밍**: `JsonlFile.iter_records()`가 파일을 한 줄씩 `yield`합니다. `list`는 `heapq.nlargest(limit, 제너레이터)`로 상위 N개만 유지하고, `summary`는 한 번 순회하며 합계를 누적하고, `export`는 읽은 줄을 바로 CSV에 씁니다. 거래가 100만 건이어도 메모리에는 한 번에 한 건(또는 N건)만 올라갑니다.

**원자적 쓰기**: update/delete/rename은 원본을 읽으면서 `transactions.jsonl.tmp`에 쓰고, 끝나면 `os.replace`로 교체합니다. 중간에 프로그램이 죽어도 원본은 그대로입니다. add는 파일 끝에 한 줄만 추가(`append`)하므로 기존 데이터를 읽지 않습니다.

**데코레이터**: 모든 handler에 `@command`(= `@handle_errors` + `@log_call` + `@timed`)를 붙입니다. handler는 자기 기능만 쓰고, try/except·로그·시간 측정은 한 곳에서 관리합니다.

**타입 힌트**: `parse_amount(value: str | int) -> int`처럼 입력과 반환 타입을 명시해 "이 함수를 통과하면 양의 정수"라는 계약이 코드에 드러납니다. `TxType = Literal["income", "expense"]`로 허용 값을 타입으로 표현했습니다.

## 알려진 한계

- id는 "현재 최댓값 + 1"로 발급하므로, 가장 마지막 거래를 삭제한 뒤 추가하면 같은 번호가 재사용됩니다 (동시에 두 개가 존재하지는 않음).
- 동시에 여러 프로세스가 같은 파일을 쓰는 상황(파일 잠금)은 고려하지 않았습니다.
- `update`/`delete`는 파일 전체를 다시 쓰므로 O(N)입니다. 대량 데이터에서 잦은 수정이 필요하면 SQLite(`sqlite3` 표준 모듈)로 옮기는 것이 다음 단계입니다.

## 커밋 컨벤션

`타입: 설명` (Conventional Commits) — `feat` 기능 / `fix` 버그 / `docs` 문서 / `style` 포맷 / `refactor` 구조 / `test` 테스트 / `chore` 설정
