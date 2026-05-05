"""
Reconcile Stripe webhooks + crypto tx hashes with agent100_charges — MAY03_2026 stub.

Usage:
  python scripts/agent100/reconcile.py
  python scripts/agent100/reconcile.py --cancel-subs   # gated; not implemented in stub
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cancel-subs", action="store_true", help="Cancel Agent100 Stripe subscriptions (manual gate)")
    args = ap.parse_args()
    if args.cancel_subs:
        print("reconcile: --cancel-subs requires explicit Stripe integration (stub).", file=sys.stderr)
        return 1
    if not os.environ.get("STRIPE_SECRET_KEY"):
        print("reconcile: no STRIPE_SECRET_KEY — nothing to do.")
        return 0
    print("reconcile: pull Stripe balance/charges and upsert agent100_charges (stub).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
