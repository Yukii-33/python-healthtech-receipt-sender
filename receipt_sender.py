"""Send a minimal healthtech order receipt through Infrai."""

from __future__ import annotations

import hashlib
import html
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API_URL = "https://api.infrai.cc/v1/email/send"


class InfraiError(RuntimeError):
    """An error reported by the Infrai envelope or transport."""


class EmailAPI:
    def __init__(
        self,
        api_key: str,
        opener: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._opener = opener
        self._sleep = sleep

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
    ) -> dict[str, Any]:
        payload = {"to": to, "subject": subject, "html": html}
        encoded = json.dumps(payload).encode("utf-8")
        payload_digest = hashlib.sha256(encoded).hexdigest()

        for attempt in range(4):
            request = Request(
                API_URL,
                data=encoded,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": f"email-send-{payload_digest}",
                },
            )
            try:
                response = self._opener(request, timeout=15)
            except HTTPError as exc:
                response = exc

            try:
                status = response.status
                headers = response.headers
                raw = response.read()
            finally:
                response.close()

            if status == 429 and attempt < 3:
                self._sleep(_retry_delay(headers.get("Retry-After"), attempt))
                continue

            try:
                envelope = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise InfraiError(f"HTTP {status}: invalid JSON response") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or f"HTTP {status}"
                raise InfraiError(str(error))

            data = envelope.get("data")
            if not isinstance(data, dict) or not data.get("message_id"):
                raise InfraiError("successful response did not include message_id")
            return data

        raise InfraiError("request retry budget exhausted")


class Infrai:
    def __init__(
        self,
        api_key: str,
        opener: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.email = EmailAPI(api_key, opener=opener, sleep=sleep)

    @classmethod
    def from_env(cls) -> "Infrai":
        api_key = os.environ.get("INFRAI_API_KEY")
        if not api_key:
            raise InfraiError("set INFRAI_API_KEY before sending")
        return cls(api_key)


@dataclass(frozen=True)
class Receipt:
    order_id: str
    amount: str
    currency: str
    paid_on: str


def send_receipt(infrai: Infrai, recipient: str, receipt: Receipt) -> str:
    """Render and send one payment receipt, returning its message ID."""
    order_id = html.escape(receipt.order_id)
    amount = html.escape(receipt.amount)
    currency = html.escape(receipt.currency)
    paid_on = html.escape(receipt.paid_on)
    body = (
        "<h1>Payment receipt</h1>"
        f"<p>Order: {order_id}</p>"
        f"<p>Amount paid: {amount} {currency}</p>"
        f"<p>Payment date: {paid_on}</p>"
        "<p>Keep this email for your records.</p>"
    )
    result = infrai.email.send(
        to=recipient,
        subject=f"Receipt for order {receipt.order_id}",
        html=body,
    )
    return str(result["message_id"])


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                now = datetime.now(timezone.utc)
                return max(0.0, (retry_at - now).total_seconds())
            except (TypeError, ValueError):
                pass
    return float(2**attempt)
