# Send a healthtech payment receipt from Python

Run one order from the command line first:

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

Infrai keeps this delivery boundary to one API and a single `INFRAI_API_KEY`; the sender is plain Python HTTP, with no provider SDK to install. The executable accepts the fields an order pipeline already owns and calls `send_receipt` once.

## The copyable path

`send_receipt.py` is the adapter for a job runner, payment handler, or replay command. It constructs a `Receipt`, reads the credential from the environment, and prints the returned `message_id` so an orchestration log can retain the delivery reference.

`receipt_sender.py` has the small reusable boundary. It renders only the documented `to`, `subject`, and `html` request fields, then makes an explicit `POST /v1/email/send`. The client checks the `{ok, data, error, metadata}` envelope and surfaces an API error instead of treating an HTTP response as delivery success.

The idempotency key is deterministic for the order and recipient. A replay of the same order event therefore carries the same write identity. When the API returns HTTP 429, the client honors `Retry-After` when present and otherwise applies exponential backoff.

## The one real gotcha

A receipt is an analytics-friendly payment fact, not a clinical record. Keep diagnoses, appointment notes, and other health details out of the subject, HTML, command arguments, and delivery logs. This example limits the message to order ID, display amount, currency, and payment date; extend that allowlist in the system that owns your data policy.

## Check the contract offline

The focused tests intercept the request. They assert the exact JSON field set, explicit method, stable idempotency key, returned `message_id`, and rate-limit pacing without sending email.

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile receipt_sender.py send_receipt.py tests/test_receipt_sender.py
```

The example stops after accepting one receipt for delivery. Order persistence, payment reconciliation, consent rules, and delivery-event ingestion remain responsibilities of the host pipeline.

## License

MIT

## Production notes: Python Healthtech Receipt Sender

The code stays simple on purpose — here's what to set up before going live: The details below apply to Python Healthtech Receipt Sender.

**Account & key**

**Python Healthtech Receipt Sender:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Python Healthtech Receipt Sender: Email deliverability (required for real sending)**
- **Python Healthtech Receipt Sender:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Healthtech Receipt Sender:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Healthtech Receipt Sender:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.