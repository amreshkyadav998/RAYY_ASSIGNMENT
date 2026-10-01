"""Send a correctly signed payment webhook to a running API (for manual testing).

    python scripts/send_webhook.py ord_a_1003 89900            # new payment id
    python scripts/send_webhook.py ord_a_1003 89900 pay_x --twice   # duplicate delivery
    python scripts/send_webhook.py ord_a_1003 89900 --bad-signature

Uses GATEWAY_WEBHOOK_SECRET (default whsec_local_dev_only) and API_URL (default http://localhost:8000).
"""

import argparse
import hashlib
import hmac
import json
import os
import secrets
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("order_id")
parser.add_argument("amount_paise", type=int)
parser.add_argument("payment_id", nargs="?", default=f"pay_{secrets.token_hex(4)}")
parser.add_argument("--twice", action="store_true", help="deliver the same event twice")
parser.add_argument("--bad-signature", action="store_true")
args = parser.parse_args()

secret = os.environ.get("GATEWAY_WEBHOOK_SECRET", "whsec_local_dev_only")
url = os.environ.get("API_URL", "http://localhost:8000") + "/webhooks/payment"
body = json.dumps(
    {
        "event": "payment.succeeded",
        "payment_id": args.payment_id,
        "order_id": args.order_id,
        "amount_paise": args.amount_paise,
    },
    separators=(",", ":"),
).encode()
sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
if args.bad_signature:
    sig = "0" * 64

for i in range(2 if args.twice else 1):
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", "X-Gateway-Signature": sig}
    )
    try:
        with urllib.request.urlopen(req) as r:
            print(f"delivery {i + 1}: {r.status} {r.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"delivery {i + 1}: {e.code} {e.read().decode()}")
print("payment_id:", args.payment_id)
print("body:", body.decode())
print("X-Gateway-Signature:", sig)
