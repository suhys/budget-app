"""대화형 입력 도우미: 잘못 입력하면 원인/힌트를 보여주고 다시 묻는다."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from budget_app.errors import AppError

T = TypeVar("T")


def ask(label: str, parse: Callable[[str], T]) -> T:
    """올바른 값이 들어올 때까지 반복해서 입력받는다."""
    while True:
        raw = input(f"{label}: ")
        try:
            return parse(raw)
        except AppError as e:
            print(f"[오류] {e.message}")
            if e.hint:
                print(f"[힌트] {e.hint}")
