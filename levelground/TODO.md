# LEVEL GROUND — Master TODO (running list)
_Updated: 2026-07-05 · Claude keeps this current every session. ✅ = done · 🔨 = in progress · ⬜ = open_

## 🚀 LAUNCH BLOCKERS — Jason (the only things standing between us and live)
- ⬜ **Deploy the site on Vercel** (switched from Netlify — Jason already runs Vercel for Bezerks): `npm i -g vercel` → `cd site` → `vercel` → `vercel --prod` → connect getlevelground.com DNS (steps: `DEPLOY.md`, ~15 min)
- ⬜ **Test both forms live** (submit a test entry, confirm it lands in the Formspree-connected inbox)
- ⬜ **Gate 1 Facebook post** — the founding story (draft ready; add your years + name)
- ✅ **Georgia LLC + EIN** — done 7/27/26. Stripe account exists under "Level Ground Consulting LLC" (`acct_1TxdajDHi7G4DAVZ`); test-mode webhook endpoint created and the whole checkout verified against it
- ✅ **Deployed to production** 7/27/26 — all API routes live and verified on getlevelground.com; Stripe's registered endpoint delivers successfully (`pending_webhooks: 0`)
- ⚠️ **The live buy button is in TEST MODE** until live activation — a real customer can't pay on it. Either finish activation or point "Claim a founding spot" back at start.html for now
- ⬜ **Activate Stripe live mode** (LLC legal name + EIN + bank), then: restricted `rk_` key → live webhook endpoint → 4 env vars in Vercel as *Sensitive* → one real $99 charge and refund. Steps in `STRIPE.md`

## Jason — soon after launch
- ⬜ Eyeball @getlevelground handle on Instagram + TikTok, register if free (YouTube/X look open)
- ⬜ Generate remaining site media (founder jobsite photo is the big one — real photo, not AI)
- ⬜ Attorney once revenue starts: review Terms/Privacy, E&O quote, trademark screen on "Level Ground"

## Claude — build queue (in order)
- ✅ Brand + FB cover (J&J blues, level motif)
- ✅ Landing page w/ real case study, email magnet, founding cap, refund guarantee
- ✅ Risk & Gap Report template (JSON-driven = database row format)
- ✅ Intake form (start.html — maps to report schema, no-payment reserve flow)
- ✅ Checklist magnet + thanks page
- ✅ Fulfillment RUNBOOK + email templates (`RUNBOOK.md`)
- ✅ Privacy + Terms pages (in site folder, footer-linked)
- ✅ Social content starter pack — 10 posts + filming batch list (`SOCIAL.md`)
- ⬜ "If it's not written, it's not included" graphic for Post 3 (on request)
- ⬜ GA4/analytics snippet once Jason has the account (or Netlify Analytics — his call)
- ⬜ Orders tracker → JARVIS integration (new-intake Telegram alert, "Waiting on QA" list)
- ⬜ Welcome email sequence for checklist subscribers (needs an ESP account — free MailerLite/Brevo when list starts growing)
- ⬜ Pre-Bid Report sample variant (sample-report.html is currently the bid-gap type)
- 🔨 Stripe checkout — code built + tested end-to-end against a throwaway sandbox (`STRIPE.md`). Still blocked on the real LLC/Stripe account before it can take a live dollar.

## Parking lot (post-launch)
- Reddit/forum version of the founding post (stripped of promotion)
- Landing-page interactive teaser ("spot the gap in this bid") as second magnet
- Course outline ("Build Your Own Home") once report demand is proven
- Builder-side engine product — DIFFERENT brand, never under Level Ground
- Outcome-tracking automation (6-month "what did it really cost?" emails → accuracy dataset)
