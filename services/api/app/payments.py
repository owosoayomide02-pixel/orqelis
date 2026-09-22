from typing import Protocol


class PaymentProvider(Protocol):
    name: str

    def is_live(self) -> bool: ...


class DevelopmentPaymentProvider:
    name = "development"

    def is_live(self) -> bool:
        return False
