"""Command-line entry point for one order receipt."""

from __future__ import annotations

import argparse

from receipt_sender import Infrai, Receipt, send_receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a healthtech payment receipt.")
    parser.add_argument("--to", required=True, help="recipient email address")
    parser.add_argument("--order-id", required=True, help="stable backend order ID")
    parser.add_argument("--amount", required=True, help="display amount, such as 48.00")
    parser.add_argument("--currency", default="USD", help="currency code")
    parser.add_argument("--paid-on", required=True, help="payment date, such as 2026-08-03")
    args = parser.parse_args()

    receipt = Receipt(
        order_id=args.order_id,
        amount=args.amount,
        currency=args.currency,
        paid_on=args.paid_on,
    )
    message_id = send_receipt(Infrai.from_env(), args.to, receipt)
    print(f"receipt accepted: message_id={message_id}")


if __name__ == "__main__":
    main()
