"""
Provision Stripe customers + crypto wallet bookkeeping — idempotent (stub).

Requires env: STRIPE_SECRET_KEY, treasury paths. Does not print secrets.
Real implementation: create Customer per agent100_*, attach payment method, subscription.

MAY03_2026 — stub exits 0 with no-op unless AGENT100_PAYMENTS_DRY_RUN=0 and keys present.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if os.environ.get("AGENT100_PAYMENTS_DRY_RUN", "1") != "0":
        print("provision_payments: dry run (set AGENT100_PAYMENTS_DRY_RUN=0 + Stripe env to execute).")
        return 0
    if not os.environ.get("STRIPE_SECRET_KEY"):
        print("STRIPE_SECRET_KEY required.", file=sys.stderr)
        return 1
    print("provision_payments: live path not implemented in stub — use Stripe Dashboard or extend script.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
