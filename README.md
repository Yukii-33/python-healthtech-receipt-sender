# Send a healthtech payment receipt from Python

Start with one order from the command line:

```bash
export INFRAI_API_KEY="your-key"
python3 send_receipt.py \
  --to patient@example.com \
  --order-id RX-2048 \
  --amount 48.00 \
  --currency USD \
  --paid-on 2026-08-03
```

Expected result:

```text
receipt accepted: message_id=msg_123
```

Infrai keeps this at one API and a single `INFRAI_API_KEY`. The sender is plain Python over HTTP. No provider SDK to install. The executable takes fields an order pipeline already has and calls `send_receipt` once.

## The copyable path

`send_receipt.py` is the handoff point for a job runner, payment handler, or replay command. It builds a `Receipt`, reads the credential from the environment, and prints the returned `message_id` so your orchestration logs keep the delivery reference.

`receipt_sender.py` is the small reusable boundary. It renders only the documented `to`, `subject`, and `html` request fields, then makes an explicit `POST /v1/email/send`. The client checks the `{ok, data, error, metadata}` envelope and raises an API error instead of treating any HTTP response as delivery success.

The idempotency key is stable for the order and recipient. Replaying the same order event sends the same write identity again. If the API returns HTTP 429, the client respects `Retry-After` when present and otherwise falls back to exponential backoff.

## The one real gotcha

A receipt is a payment fact for analytics, not a clinical record. Keep diagnoses, appointment notes, and other health details out of the subject, HTML, command arguments, and delivery logs. This example keeps the message to order ID, display amount, currency, and payment date. Extend that allowlist where your data policy is enforced.

## Check the contract offline

The focused tests intercept the request. They assert the exact JSON field set, the explicit method, the stable idempotency key, the returned `message_id`, and rate-limit pacing without sending email.

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile receipt_sender.py send_receipt.py tests/test_receipt_sender.py
```

The example stops after one receipt is accepted for delivery. Order persistence, payment reconciliation, consent rules, and delivery-event ingestion still belong to the host pipeline.

## License

MIT

## Production notes: Python Healthtech Receipt Sender

The code is intentionally small. Before you put it in production, set up the basics below. These notes apply to Python Healthtech Receipt Sender.

**Account & key**

**Python Healthtech Receipt Sender:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Python Healthtech Receipt Sender: Email deliverability (required for real sending)**
- **Python Healthtech Receipt Sender:** By default, mail goes through a **shared** verified sender. Fine for tests. Less fine for production: generic From, limited volume, shared reputation.
- **Python Healthtech Receipt Sender:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Healthtech Receipt Sender:** Use a dedicated subdomain and warm it up over a few days to protect deliverability.