"""모델 계층: 데이터 구조와 값 검증.

파일·입출력을 전혀 모른다. "이 값이 올바른가"만 책임진다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from budget_app.errors import ValidationError

TxType = Literal["income", "expense"]
VALID_TYPES: tuple[str, ...] = ("income", "expense")


# ---------- 개별 값 검증 함수 (str -> 정규화된 값) ----------

def parse_date(value: str) -> str:
    """'YYYY-MM-DD' 문자열을 검증해 그대로 반환한다. 2024-13-40 같은 값은 거부."""
    text = value.strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).",
            "예: 2024-01-15",
        ) from None
    return text


def parse_month(value: str) -> str:
    """'YYYY-MM' 문자열을 검증해 반환한다."""
    text = value.strip()
    try:
        datetime.strptime(text, "%Y-%m")
    except ValueError:
        raise ValidationError(
            "월 형식이 올바르지 않습니다 (YYYY-MM).",
            "예: 2024-01",
        ) from None
    return text


def parse_type(value: str) -> TxType:
    text = value.strip().lower()
    if text not in VALID_TYPES:
        raise ValidationError(
            f"허용되지 않는 타입입니다: '{value}'",
            "income 또는 expense 중 하나를 입력하세요.",
        )
    return text  # type: ignore[return-value]


def parse_amount(value: str | int) -> int:
    """양의 정수만 허용한다. 0, 음수, 소수, 문자는 거부."""
    try:
        amount = int(str(value).strip().replace(",", ""))
    except ValueError:
        raise ValidationError(
            f"금액은 숫자여야 합니다: '{value}'",
            "예: 15000 (쉼표 없이 정수로 입력)",
        ) from None
    if amount <= 0:
        raise ValidationError(
            f"금액은 0보다 커야 합니다: {amount}",
            "양의 정수를 입력하세요. 수입/지출 구분은 타입으로 합니다.",
        )
    return amount


def parse_category_name(value: str) -> str:
    text = value.strip().lower()
    if not text:
        raise ValidationError("카테고리명이 비어 있습니다.", "예: food")
    if any(ch in text for ch in ",|\n"):
        raise ValidationError(
            f"카테고리명에 사용할 수 없는 문자가 있습니다: '{value}'",
            "쉼표(,), 세로줄(|) 없이 입력하세요.",
        )
    return text


def parse_tags(value: str) -> list[str]:
    """'meal, lunch' -> ['meal', 'lunch']. 빈 문자열이면 빈 리스트."""
    return [tag.strip() for tag in value.split(",") if tag.strip()]


# ---------- 데이터 모델 ----------

@dataclass
class Transaction:
    """거래 1건. 저장소에는 to_dict() 결과가 JSON 한 줄로 저장된다."""

    id: str
    type: TxType
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def month(self) -> str:
        return self.date[:7]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        """파일에서 읽은 dict를 검증하며 Transaction으로 변환한다."""
        try:
            return cls(
                id=str(data["id"]),
                type=parse_type(str(data["type"])),
                date=parse_date(str(data["date"])),
                amount=parse_amount(data["amount"]),
                category=str(data["category"]),
                memo=str(data.get("memo", "")),
                tags=list(data.get("tags", [])),
            )
        except KeyError as e:
            raise ValidationError(f"필수 필드가 없습니다: {e}") from None

    def format_row(self) -> str:
        return " | ".join(
            [self.id, self.date, f"{self.type:<7}", self.category, str(self.amount), self.memo]
        )
