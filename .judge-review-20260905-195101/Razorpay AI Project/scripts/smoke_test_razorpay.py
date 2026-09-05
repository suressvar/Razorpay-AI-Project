"""Razorpay Test Mode Smoke Test Script.

Validates that provided Razorpay test credentials work against the genuine Razorpay API
by creating a test payment link and verifying response payload structure.

Usage:
    python scripts/smoke_test_razorpay.py --key-id rzp_test_... --key-secret ...
    or
    python scripts/smoke_test_razorpay.py (reads from .env)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from recovery_autopilot.config import settings
from recovery_autopilot.integrations.razorpay.client import GenuineRazorpayTestClient, RazorpayGatewayError


async def main():
    parser = argparse.ArgumentParser(description="Razorpay Test Mode Verification Smoke Test")
    parser.add_argument("--key-id", default=os.getenv("RAZORPAY_KEY_ID", settings.RAZORPAY_KEY_ID), help="Razorpay Key ID (rzp_test_...)")
    parser.add_argument("--key-secret", default=os.getenv("RAZORPAY_KEY_SECRET", settings.RAZORPAY_KEY_SECRET), help="Razorpay Key Secret")
    args = parser.parse_args()

    key_id = args.key_id
    key_secret = args.key_secret

    print("=" * 60)
    print("  Razorpay Test Mode Smoke Verification")
    print("=" * 60)

    if not key_id or not key_secret:
        print("[!] ERROR: RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be supplied.")
        print("    Pass them as CLI arguments or set them in your .env file.")
        sys.exit(1)

    if not key_id.startswith("rzp_test_"):
        print(f"[!] SAFETY ERROR: Key ID '{key_id}' does not start with 'rzp_test_'.")
        print("    Live keys (rzp_live_*) are strictly forbidden for smoke tests.")
        sys.exit(1)

    print(f"[*] Initializing GenuineRazorpayTestClient with Key ID: {key_id[:12]}...")

    try:
        client = GenuineRazorpayTestClient(key_id=key_id, key_secret=key_secret)
        print("[*] Dispatching test payment link creation request (Amount: INR 10.00 / 1000 paise)...")

        response = await client.create_payment_link(
            amount_paise=1000,
            currency="INR",
            description="Buildathon Smoke Test Payment Link",
            customer_name="Razorpay Buildathon Judge",
            customer_email="judge@buildathon.example.com",
            customer_phone="+919876543210",
            idempotency_key=f"smoke_test_{int(asyncio.get_event_loop().time() * 1000)}",
        )

        print("\n[SUCCESS] Test Payment Link Created Successfully!")
        print(f"  - Payment Link ID: {response.get('id')}")
        print(f"  - Short URL:       {response.get('short_url')}")
        print(f"  - Amount (Paise):  {response.get('amount')} (INR {response.get('amount', 0) / 100:.2f})")
        print(f"  - Status:          {response.get('status')}")
        print(f"  - Created At:      {response.get('created_at')}")
        print("\nRazorpay Test Mode credentials are valid and verified.")

    except RazorpayGatewayError as e:
        print(f"\n[!] Razorpay Gateway Error: {e.message} (HTTP {e.status_code})")
        print(f"    Raw Details: {e.details}")
        sys.exit(2)
    except Exception as e:
        print(f"\n[!] Unexpected Error during smoke test: {e}")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())
