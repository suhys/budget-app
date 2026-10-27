"""사용자에게 보여줄 오류 타입.

모든 예상 가능한 오류는 AppError로 통일한다.
CLI는 AppError를 잡아 '원인 + 해결 힌트'만 출력하고 스택트레이스는 숨긴다.
"""

from __future__ import annotations


class AppError(Exception):
    """사용자에게 보여줄 오류. message(원인)와 hint(해결 방법)를 가진다."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class ValidationError(AppError):
    """입력값 검증 실패 (날짜 형식, 음수 금액 등)."""


class NotFoundError(AppError):
    """존재하지 않는 id / 카테고리 / 예산."""


class StorageError(AppError):
    """저장 파일을 읽거나 쓸 수 없음 (손상된 줄, 권한 문제 등)."""
