# LEVEL GROUND — Stripe integration

Payments only. **No Connect** — every dollar lands in the Level Ground LLC, and
nobody else gets paid out of a report fee. Revisit only if you ever put other
builders on the roster writing reports for a cut.

## What's here

| File | Does |
| --- | --- |
| `site/lib/stripe.js` | Stripe client (API version pinned), the two price tiers, founding-cap count |
| `site/api/create-checkout.js` | Mints a Checkout Session. Public for the button; bearer token unlocks admin extras |
| `site/api/stripe-webhook.mjs` | Verifies Stripe's signature, logs paid + refunded |
| `site/api/pricing.js` | GET — what a visitor would be charged right now |
| `site/live-price.js` | Rewrites advertised prices once the founding 10 are gone |
| `site/paid.html` | Post-payment page (`success_url`) |

Prices live **only** on the server (`lib/stripe.js`): `founding` $99, `standard`
$299. The browser never sends an amount, so nobody can pay themselves a discount.

## Two ways a session gets created

**The button.** "Claim a founding spot" on the pricing block POSTs an empty body
to `/api/create-checkout` and redirects to Stripe. No auth — anyone can start a
checkout, which is what a buy button is. What they *cannot* do is name their own
price: a `tier` from an unauthenticated caller is rejected `403`, so nobody buys a
$299 report for $99. Stripe collects the email. The `<a href>` still points at
`start.html`, so with JS off — or if checkout is unreachable — visitors fall back
to the reserve flow instead of hitting a dead button.

**Your emailed links.** With the bearer token you can prefill an email, attach a
`reference`, and pin a `tier` to honour a price you already promised.

The founding cap counts completed Checkout Sessions tagged
`metadata.product = risk_gap_report` — Stripe is the source of truth, so no
database is needed. Under 10 sold → $99, otherwise $299. Passing an explicit
`tier` overrides that, for honouring a price you already promised someone.

## Keeping the advertised price honest

The pages are authored with the founding price in the markup, so while spots
remain `live-price.js` does nothing — no flash, no layout shift. Once the 10th
report sells, it rewrites all eight places that said $99 (the pricing block, the
button label, both "from $99" cards on the landing page, and the banner and
submit button on `start.html`).

`/api/pricing` is cached `max-age=0, s-maxage=60` — the CDN absorbs the load, but
browsers always revalidate. Don't drop the `max-age=0`: without it a visitor's
browser pins a stale price for the life of its cache, which is the exact failure
this exists to prevent.

If `/api/pricing` fails the page is left as authored, showing the founding price.
That's the deliberate choice — Stripe Checkout always shows the true amount before
anyone pays, so the worst case is an optimistic page, never a surprise charge.
**Raising the standard price means editing the markup too**, not just `TIERS`, or
the page will advertise the old number until the founding spots run out.

## Accounts

Test/sandbox: **`acct_1TxdajDHi7G4DAVZ`** — "Level Ground Consulting LLC sandbox"
([dashboard](https://dashboard.stripe.com/acct_1TxdajDHi7G4DAVZ/test/dashboard)).
Everything below has been verified against it.

Do **not** use `acct_1T9VwNEISK4hdc6V` (GATX Enterprises LLC) — that's a different
entity that also lives on this machine, and the Stripe CLI defaults to it when no
`--api-key` or `--config` is passed.

## Webhook endpoints

**Test mode — created, `we_1TxruRDHi7G4DAVZMFMgMbzL`.** URL
`https://www.getlevelground.com/api/stripe-webhook`, events
`checkout.session.completed` + `charge.refunded`, status enabled.

**Live mode — not created.** It needs a live key, which is deliberately not kept
anywhere in this project. Create it yourself in the Dashboard (live mode on →
Developers → Webhooks → Add endpoint), same URL and same two events.

### There are two different signing secrets — don't mix them

| Where | Which secret | Comes from |
| --- | --- | --- |
| Local dev | the one `stripe listen` prints on startup | rotates each `stripe listen` |
| Deployed test | this endpoint's secret | Dashboard → Webhooks → the endpoint |
| Deployed live | the live endpoint's secret | created when you add the live endpoint |

They are not interchangeable. Using the local `stripe listen` secret on the
deployed site makes every real webhook fail signature verification with a 400.

## Environment variables

All four are set on **Production** as *Sensitive* (2026-07-27). Never commit them.

**Setting them from a shell: don't pipe the value.** `"value" | vercel env add`
appends a newline, which Stripe rejects — it cost a broken deploy and shows up as
`connection to Stripe` errors and `signing secret contains whitespace`. Write the
value to a file with no trailing newline and redirect:
`cmd /c "vercel env add NAME production --sensitive < value.txt"`. Env changes
only take effect on the **next deploy**.

| Name | Value |
| --- | --- |
| `STRIPE_SECRET_KEY` | Restricted key (`rk_…`) with `checkout_sessions` read **and** write. Read is what the founding cap needs. Don't ship a full `sk_` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` from the webhook endpoint you create in the Dashboard |
| `LG_ADMIN_TOKEN` | Long random string you invent — the password for `create-checkout` |
| `SITE_ORIGIN` | `https://www.getlevelground.com` |

## Sending a client their payment link

This is Email 2 in `RUNBOOK.md`. Replace `[STRIPE LINK]` with the `url` this returns:

```bash
curl -X POST https://www.getlevelground.com/api/create-checkout -H "Authorization: Bearer $LG_ADMIN_TOKEN" -H "Content-Type: application/json" -d '{"email":"client@example.com","name":"Client Name","reference":"PR-109"}'
```

## ⚠ The live site is currently in TEST MODE

`STRIPE_SECRET_KEY` in Vercel production is a **test** key, because live mode
isn't activated yet. Everything works — but the "Claim a founding spot" button
leads to a Stripe page with a TEST MODE banner, and **a real customer cannot pay
on it**. Either finish live activation below, or point the button back at
`start.html` (drop the `id="foundingBtn"`) and redeploy until you're ready.

## Before the first live dollar

1. ~~Georgia LLC~~ — done, with EIN (2026-07-27).
2. ~~Deploy~~ — done 2026-07-27; all endpoints verified in production.
3. **Activate live mode** on `acct_1TxdajDHi7G4DAVZ` — Stripe will want the LLC's
   legal name, EIN, address, and a bank account.
4. Create a **restricted** API key with only `checkout_sessions: write` and
   `checkout_sessions: read` (the read permission is what the founding cap needs).
5. Add the **live** webhook endpoint (see above) and copy its signing secret.
6. Set the four env vars in Vercel as *Sensitive*.
7. Dashboard → Payment methods — turn on what you want. The code deliberately
   does not hardcode payment types, so this is configured without a deploy.
8. Run one real $99 charge on a live card, then refund it from the Dashboard.

## Two things deliberately NOT done

- **Stripe Tax is off.** Turning on `automatic_tax` without an active Georgia
  registration makes Stripe collect nothing while the Dashboard says tax is on.
  Ask the CPA whether this service is taxable in GA before touching it.
- **No CSP header.** The site uses inline `<style>` and `<script>` throughout, so
  a Content-Security-Policy needs `'unsafe-inline'` to avoid breaking the page —
  worth doing properly as its own task, not bolted on blind.

## Notes for whoever touches this next

The webhook runs on the **Edge runtime**, and that is not a style preference.
Vercel's Node runtime always parses a JSON body: there is no `req.rawBody`, the
stream is already drained, and `config.api.bodyParser = false` is ignored. Stripe
signatures are computed over the exact raw bytes, so verification can never pass
there. Edge gives a Web `Request`, and `request.text()` returns those bytes.
Verified against Vercel CLI 57. If you move this handler back to Node, signature
verification will fail closed and every webhook will 400.
