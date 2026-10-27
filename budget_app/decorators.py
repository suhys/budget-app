"""공통 관심사(예외 처리 / 실행 로그 / 실행 시간 측정)를 데코레이터로 분리한다.

각 command handler는 "자기 기능"만 작성하고, 아래 데코레이터를 붙여서
try/except, 로그, 시간 측정 코드를 반복하지 않는다.

적용 순서 (바깥 → 안):
    @handle_errors   # 가장 바깥: 어떤 예외든 여기서 최종 처리
    @log_call        # 시작/종료/실패를 app.log에 기록
    @timed           # 순수 실행 시간 측정
    def handler(...)
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import ParamSpec

from budget_app.errors import AppError

P = ParamSpec("P")
logger = logging.getLogger("budget_app")

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130


def handle_errors(func: Callable[P, int]) -> Callable[P, int]:
    """예외를 '원인 + 힌트' 메시지로 바꾸고 0이 아닌 종료 코드를 반환한다. 스택트레이스는 숨긴다."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return func(*args, **kwargs)
        except AppError as e:
            print(f"[오류] {e.message}")
            if e.hint:
                print(f"[힌트] {e.hint}")
            return EXIT_ERROR
        except (KeyboardInterrupt, EOFError):
            print("\n[취소] 입력이 중단되어 작업을 취소했습니다. 저장된 내용은 없습니다.")
            return EXIT_INTERRUPTED
        except OSError as e:
            print(f"[오류] 파일을 처리할 수 없습니다: {e.strerror} ({e.filename})")
            print("[힌트] 경로와 권한을 확인하거나 --data-dir 로 다른 폴더를 지정하세요.")
            return EXIT_ERROR
        except Exception:  # 예상하지 못한 버그도 사용자에게 스택트레이스를 보이지 않는다
            logger.exception("unexpected error in %s", func.__name__)
            print("[오류] 예상하지 못한 오류가 발생했습니다.")
            print("[힌트] data 폴더의 app.log 에 상세 내용이 기록되어 있습니다.")
            return EXIT_ERROR

    return wrapper


def log_call(func: Callable[P, int]) -> Callable[P, int]:
    """명령 시작/종료/실패를 로그 파일에 남긴다."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        logger.info("start %s", func.__name__)
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            logger.warning("fail  %s: %s", func.__name__, e)
            raise  # 처리는 handle_errors에게 맡긴다
        logger.info("end   %s (exit=%s)", func.__name__, result)
        return result

    return wrapper


def timed(func: Callable[P, int]) -> Callable[P, int]:
    """실행 시간을 측정해 로그에 남긴다 (예외가 나도 finally로 기록)."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info("time  %s %.2fms", func.__name__, elapsed_ms)

    return wrapper


def command(func: Callable[P, int]) -> Callable[P, int]:
    """세 데코레이터를 올바른 순서로 한 번에 적용하는 단축 데코레이터."""
    return handle_errors(log_call(timed(func)))
