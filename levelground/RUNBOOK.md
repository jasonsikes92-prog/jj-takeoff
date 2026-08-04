# LEVEL GROUND — Fulfillment Runbook
_From "intake email arrives" to "report delivered." Every step is either automated, Claude's, or a copy-paste. Jason's only real job is the QA read._

## Two ways in
- **Reserve first** (`start.html`, and the two "Have a builder read my bid" buttons) — the pipeline below, payment at step 6.
- **Pay first** (the "Claim a founding spot" button on the pricing block) — they pay on the spot via Stripe, *before* we have their plans. Stripe emails you the receipt; skip to **Email 1B** below, then rejoin at step 3. Their $99 is already banked, so a paid customer sitting without an upload link is the one thing that must never slip.

## The pipeline at a glance
1. Netlify emails you a new **intake** submission →
2. Send **Email 1** (confirm + upload link) →
3. Files arrive → hand plans + intake details to Claude (estimating chat) →
4. Engine + Claude produce the report JSON → render in the template →
5. **Jason QA** (reports 1–10: full read; later: flagged-only) →
6. Send **Email 2** (payment link) → paid → send **Email 3** (the report PDF) →
7. Log the JSON row in `Level Ground\data\` (the database) →
8. Calendar: +6 months → **Email 4** (outcome follow-up).

Target turnaround for founding 10: **3 business days** from files received.

---

## EMAIL 1 — Reservation confirmed + upload link
*Send within one business day of an intake submission. Set up a free Dropbox "file request" or Google Drive shared folder once and reuse the pattern.*

> **Subject: Your Level Ground spot is reserved — send us your plans**
>
> Hi [Name],
>
> You're in — founding spot confirmed at $99 (regular $299).
>
> Upload your plans here, and the bid too if you have one: **[UPLOAD LINK]**
> PDFs are perfect. Whatever the builder or designer gave you is enough — don't worry about whether it's "complete."
>
> Once your files land, your report takes about 3 business days. No payment until it's underway, and if you're not satisfied with the report, it's free — no questions asked.
>
> One question meanwhile: [pull their "keeping you up at night" answer and ask one sharp follow-up — this personalizes the report and the relationship].
>
> — Jason, builder & founder, Level Ground
> getlevelground.com · You pay us, so we work for you. No referral fees from builders, ever.

## EMAIL 1B — They already paid (pay-first button) + upload link
*Send within one business day of the Stripe receipt. These people have paid and told us nothing yet — the `paid.html` page promised them this email.*

> **Subject: Payment received — now send us your plans**
>
> Hi [Name],
>
> Your founding spot is paid and locked in. One thing left: your plans.
>
> Upload them here, and the bid too if you have one: **[UPLOAD LINK]**
> PDFs are perfect. Whatever the builder or designer gave you is enough — don't worry about whether it's "complete."
>
> Your report lands within 3 business days of your files arriving. And if it doesn't earn its fee, say so and I'll refund it — no questions.
>
> While you're at it: what's the part of this build keeping you up at night? One line is plenty — it tells me where to look hardest.
>
> — Jason, builder & founder, Level Ground
> getlevelground.com · You pay us, so we work for you. No referral fees from builders, ever.

## EMAIL 2 — Files received + payment link
*Reserve-first path only. Pay-first customers have already paid — don't send them a payment link.*
> **Subject: Got your plans — your review is underway**
>
> Hi [Name],
>
> Your plans are in and the review has started. Here's the secure payment link for your founding report ($99): **[STRIPE LINK]**
>
> You'll have the report within 3 business days of payment. It'll cover: what your home should cost, any gaps or thin allowances in the bid, your home's measured quantities, and the exact questions to take back to your builder.
>
> — Jason

## EMAIL 3 — Delivery
> **Subject: Your Level Ground report is ready — read this before your next builder conversation**
>
> Hi [Name],
>
> Attached is your report. Three suggestions before you open it:
>
> 1. Read "The bottom line" first — it's one page.
> 2. Nothing in here is an accusation. Most gaps are normal bid-writing, not bad intent. Use the Questions section to have a *better* conversation with your builder, not a fight.
> 3. The checklist page is built for your phone — take it into the meeting and tap questions off as you go.
>
> If anything is unclear, reply and ask. And if the report didn't earn its fee, say so and I'll refund it — no questions.
>
> — Jason
>
> P.S. If this helped, forwarding it to one friend who's about to build is the best thank-you there is.

## EMAIL 4 — Outcome follow-up (calendar +6 months)
*This builds the accuracy dataset that becomes our moat. Never skip it.*
> **Subject: How did the build turn out?**
>
> Hi [Name],
>
> Six months ago we reviewed your plans. Two quick questions, 30 seconds:
> 1. Did you build — and with that builder?
> 2. How did the final cost land vs. the bid (roughly)?
>
> This is how we keep our reviews honest for the next family. Thank you — and if you're mid-build and something's off, reply; happy to take a look.
>
> — Jason

---

## QA checklist (Jason, before any report ships)
- [ ] Every finding tagged Measured / Fact / Estimated — no naked numbers
- [ ] Ranges you'd stand behind for THAT market (not just Middle GA reflexes)
- [ ] Tone check: advocate, not builder-basher — no accusation anywhere
- [ ] "What we can't know" present and honest
- [ ] Names/identifying details of the builder NOT in the report (we flag lines, not people)
- [ ] Second pass — "done" = checked twice

## Data banking (the flywheel — after every report)
Save the report's JSON block to `Desktop\Level Ground\data\LG-YYYY-####.json`.
That folder IS the national pricing database. Claude handles this when generating; if a report is edited during QA, the JSON gets re-saved to match.

## Edge cases
- **Plans too incomplete to measure** → be straight: offer the Pre-Bid checklist review at reduced scope, or refund and tell them what to request from their designer. Never fake a measurement.
- **Angry builder contacts you** → we flagged lines, not people; the report told the client to talk TO their builder. Reply once, politely, or not at all. Never argue in writing.
- **Customer wants us to "pick a builder"** → never. We're the advocate, not a matchmaker. It's also the bright line that keeps us legally clean.
- **Plans are for a state we have no data for** → widen the ranges, say so explicitly in the report, and label everything Estimated. Honesty is the product.
