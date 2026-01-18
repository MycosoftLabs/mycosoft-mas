# Stripe Payment Integration - Complete

**Date:** January 17, 2026  
**Status:** ✅ Core Integration Complete

---

## Overview

A comprehensive payment system has been integrated for NatureOS using Stripe, covering:
- **Subscription Management** (Free, Pro, Enterprise tiers)
- **Hardware/Device Sales** (MycoBrain sensors)
- **API Usage Metering**
- **Premium Feature Gates**

---

## Stripe Products Created

All products have been successfully created in the Stripe Test Dashboard:

### Subscription Products

| Product | Monthly Price | Annual Price |
|---------|---------------|--------------|
| NatureOS Pro | $29/month | $276/year ($23/mo) |
| NatureOS Enterprise | $99/month | $948/year ($79/mo) |

### Hardware Products (One-time)

| Product | Price |
|---------|-------|
| MycoBrain Basic | $149 |
| MycoBrain Pro | $299 |
| MycoBrain Enterprise Pack (5x) | $1,199 |

### Premium Features (Add-ons)

| Feature | Monthly Price |
|---------|---------------|
| CREP Dashboard | $19/month |
| AI Studio Pro | $39/month |

---

## Price IDs Reference

```typescript
export const STRIPE_PRICE_IDS = {
  SUBSCRIPTION: {
    PRO_MONTHLY: 'price_1SqiwoExoi95oZvKcua6i8hJ',
    PRO_ANNUAL: 'price_1SqiwoExoi95oZvKqJbN4ZuW',
    ENTERPRISE_MONTHLY: 'price_1SqiwoExoi95oZvK0hMU8j4Z',
    ENTERPRISE_ANNUAL: 'price_1SqiwoExoi95oZvKbtaEPlQd',
  },
  HARDWARE: {
    MYCOBRAIN_BASIC: 'price_1SqiwpExoi95oZvKQRRemolb',
    MYCOBRAIN_PRO: 'price_1SqiwpExoi95oZvK36WGrmuT',
    MYCOBRAIN_ENTERPRISE_PACK: 'price_1SqiwpExoi95oZvKvO3DS6si',
  },
  FEATURES: {
    CREP_DASHBOARD: 'price_1SqiwqExoi95oZvKyHcmNjLw',
    AI_STUDIO: 'price_1SqiwqExoi95oZvK2XtSbXBi',
  },
};
```

---

## Files Created

### Configuration
- `lib/stripe/config.ts` - Stripe SDK setup and price ID constants
- `lib/stripe/server.ts` - Server-side Stripe operations
- `lib/stripe/client.ts` - Client-side Stripe.js utilities
- `lib/stripe/billing.ts` - Billing sync functions

### API Routes
- `app/api/stripe/checkout/route.ts` - Subscription checkout
- `app/api/stripe/checkout-product/route.ts` - Product purchases
- `app/api/stripe/portal/route.ts` - Customer billing portal
- `app/api/stripe/webhooks/route.ts` - Webhook handler
- `app/api/usage/track/route.ts` - API usage metering
- `app/api/billing/route.ts` - Billing info endpoint

### Pages
- `app/pricing/page.tsx` - Pricing plans (updated with Stripe checkout)
- `app/shop/page.tsx` - MycoBrain device store
- `app/billing/page.tsx` - User billing management
- `app/billing/success/page.tsx` - Post-checkout success page
- `app/orders/success/page.tsx` - Post-purchase success page

### Database Migration
- `supabase/migrations/20260119000000_add_stripe_billing_to_profiles_and_api_usage.sql`
  - Adds `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`, `current_period_end` to profiles
  - Creates `api_usage` table for metering

---

## Manual Steps Required

### 1. Get Publishable Key from Stripe Dashboard

1. Go to https://dashboard.stripe.com/test/apikeys
2. Log in to your Stripe account
3. Copy the **Publishable key** (starts with `pk_test_`)
4. Update `.env.local`:
   ```
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_51SqidzExoi95oZvK...
   ```

### 2. Set Up Webhook Secret

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click "Add endpoint"
3. Enter your endpoint URL:
   - **Local:** Use Stripe CLI for local testing
   - **Production:** `https://mycosoft.com/api/stripe/webhooks`
4. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the **Signing secret** (starts with `whsec_`)
6. Update `.env.local`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

### 3. Local Webhook Testing with Stripe CLI

```bash
# Install Stripe CLI
# Windows:
scoop install stripe

# Mac:
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to localhost
stripe listen --forward-to localhost:3001/api/stripe/webhooks

# This will output a webhook signing secret - use this for local testing
```

---

## Testing Checklist

### Pricing Page
- [x] Page loads at `/pricing`
- [x] Monthly/Annual toggle works
- [x] All three plans display correctly
- [ ] "Start Free Trial" button initiates Stripe Checkout (requires auth)

### Shop Page
- [x] Page loads at `/shop`
- [x] All three products display correctly
- [x] Quantity selectors work
- [ ] "Buy Now" button initiates Stripe Checkout (requires auth)

### Billing Page
- [x] Page loads at `/billing`
- [x] Shows loading state for unauthenticated users
- [ ] Displays subscription info for authenticated users
- [ ] "Go to Customer Portal" button works

### Webhook Processing
- [ ] `checkout.session.completed` updates profile
- [ ] `customer.subscription.updated` syncs status
- [ ] `customer.subscription.deleted` downgrades to free

---

## Test Card Numbers

For testing Stripe Checkout in test mode:

| Card | Number |
|------|--------|
| Success | 4242 4242 4242 4242 |
| Requires Auth | 4000 0025 0000 3155 |
| Decline | 4000 0000 0000 9995 |

Use any future expiry date and any 3-digit CVC.

---

## Environment Variables Summary

```env
# Stripe (Test Mode)
STRIPE_SECRET_KEY=rk_test_51SqidzExoi95oZvK...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_51SqidzExoi95oZvK...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application
NEXT_PUBLIC_BASE_URL=http://localhost:3001
```

---

## Next Steps

1. **Get Publishable Key** - Log into Stripe Dashboard and copy it
2. **Configure Webhook** - Set up webhook endpoint and get secret
3. **Apply Migration** - Run the Supabase migration for billing columns
4. **Test End-to-End** - Complete a test purchase with test card
5. **Production Setup** - Switch to live keys for production

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Pricing Page  │────▶│  Checkout Route  │────▶│ Stripe Checkout │
│   /pricing      │     │  /api/stripe/... │     │   (Hosted)      │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Billing Page  │◀───│  Webhook Route   │◀────│ Stripe Webhooks │
│   /billing      │     │  /api/stripe/... │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │    Supabase      │
                        │  profiles table  │
                        └──────────────────┘
```

---

## Support

For issues with payments:
- Check Stripe Dashboard for payment logs
- Review webhook delivery status
- Check Supabase logs for sync issues

**Stripe Account:** acct_1SqidzExoi95oZvK (Mycosoft sandbox)
