import io
import json
import unittest
from unittest.mock import Mock

from receipt_sender import Infrai, Receipt, send_receipt


class FakeResponse:
    def __init__(self, body: dict, status: int = 200, headers: dict | None = None) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self.status = status
        self.headers = headers or {}

    def read(self) -> bytes:
        return io.BytesIO(self._body).read()

    def close(self) -> None:
        pass


class ReceiptSenderTests(unittest.TestCase):
    def test_send_uses_documented_fields_and_stable_delivery_key(self) -> None:
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse({"ok": True, "data": {"message_id": "msg_123"}})

        infrai = Infrai("test-key", opener=opener)
        receipt = Receipt("RX-2048", "48.00", "USD", "2026-08-03")

        first = send_receipt(infrai, "patient@example.com", receipt)
        second = send_receipt(infrai, "patient@example.com", receipt)

        self.assertEqual(first, "msg_123")
        self.assertEqual(second, "msg_123")
        self.assertEqual(requests[0][0].method, "POST")
        self.assertEqual(requests[0][1], 15)
        self.assertEqual(
            set(json.loads(requests[0][0].data)), {"to", "subject", "html"}
        )
        self.assertEqual(
            requests[0][0].get_header("Idempotency-key"),
            requests[1][0].get_header("Idempotency-key"),
        )

    def test_rate_limit_honors_retry_after(self) -> None:
        opener = Mock(
            side_effect=[
                FakeResponse({}, status=429, headers={"Retry-After": "2"}),
                FakeResponse({"ok": True, "data": {"message_id": "msg_456"}}),
            ]
        )
        sleep = Mock()
        infrai = Infrai("test-key", opener=opener, sleep=sleep)

        message_id = send_receipt(
            infrai,
            "patient@example.com",
            Receipt("RX-4096", "19.00", "USD", "2026-08-03"),
        )

        self.assertEqual(message_id, "msg_456")
        sleep.assert_called_once_with(2.0)


if __name__ == "__main__":
    unittest.main()
