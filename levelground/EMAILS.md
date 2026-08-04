# Level Ground — 5-Email Nurture Sequence

Trigger: contact joins the "Level Ground Leads" group (fires from the exit popup or the checklist form).
Build this as one Automation in MailerLite: Automations → New automation → Trigger = "Subscriber joins a group" → Level Ground Leads → add the 5 emails below with the delays noted.

All facts/numbers pulled directly from the live site copy — nothing invented, so the story stays consistent if a lead reads both.

**Personalization:** the forms capture first name into MailerLite's default `name` field. The tag below is `{$name}` — MailerLite's standard merge syntax for that field. One safety check before your first send: open the email in MailerLite's editor and confirm `{$name}` shows up highlighted/recognized as a merge tag (not plain text) — that confirms the field name matches exactly.

**Formatting & editor choice:** in MailerLite, build each email in the **plain/rich-text editor**, NOT the drag-and-drop design editor. Reasons:
- `getlevelground.com` just got authenticated as a sending domain a few days ago — it has zero sending reputation yet. Heavy-HTML marketing templates (multiple images, colored block sections) get scrutinized harder by spam filters from a brand-new domain. Plain text is safer while reputation builds.
- The brand's whole pitch is "a real builder personally reviewing your bid," not a company running a funnel. A slick designed template undercuts that — it starts looking like the marketing emails homeowners already distrust. A plain email that reads like it came from Jason's actual inbox reinforces the thing you're selling.

**Branding, font, colors — deliberately minimal:**
- **No logo image, no header graphic.** Brand identity in a plain email lives in the "From" name (set the sender as "Jason & Jessica, Level Ground") and the signature line, not visual design.
- **Font:** don't try to force the site's fonts (Fraunces/Inter) — most email clients (Outlook especially) ignore custom web fonts anyway, so it'd just fall back inconsistently. Leave the editor's default system font as-is; it supports the personal-email feel besides.
- **Body text:** default black/dark gray on white. No colored text blocks, no background color panels.
- **The one branding touch:** the two direct purchase-offer links — "Claim a founding spot" (Email 4) and "Have a builder read my bid" (Email 5) — style those as an actual button using the site's steel blue, `#5C90AC`, since those are the real conversion moments. Every other link (the checklist link in Email 1, the sample-report link in Email 3) stays a plain underlined text link, not a button.

---

## Email 1 — Instant
**Subject:** Your checklist — and who's sending it
**Preview text:** What a complete bid must include, plus a fast intro.

Hi {$name},

Here's the checklist you asked for: "What a complete bid must include" — the scopes, allowances, and contract lines a bid should never leave out.

**[Get the checklist →]** (link to getlevelground.com/checklist.html — plain text link, not a button)

Quick intro, {$name}, since you're trusting us with something this big: we're Jason & Jessica. We run a real custom-home building company — not a review site, not a lead-gen operation. We built Level Ground because we kept watching families sign contracts they didn't fully understand, then get hit with change orders nobody warned them about.

Over the next week or so we'll send a few short, honest emails — what to watch for, a real example of what we've caught, and how a full Risk & Gap Report works if you ever want a second set of eyes on your own plans or bid. No spam, no pressure. Unsubscribe any time.

Talk soon,
Jason & Jessica
Level Ground — getlevelground.com

---

## Email 2 — Day 1
**Subject:** The sentence that costs homeowners the most
**Preview text:** "Per plan allowance" sounds specific. It usually isn't.

{$name},

Most builder bids look complete. That's the problem.

A bid can list every category — countertops, electrical, site work — and still leave you exposed, because "complete" and "accurate" aren't the same thing. Here's what that looks like in real numbers, pulled from an actual bid we reviewed:

- **Countertops:** allowance listed at $5,000. Realistic cost for what the plans called for: $15,000–$22,000.
- **Site work, grading, final dirt:** not listed at all. Missing entirely.
- **Electrical:** $35,000 lump sum, no breakdown — exactly where overages hide.

Add it up and that one bid was carrying **$40,000+ of exposure** the homeowner never saw, because none of it was dishonest on paper. It's just how bids get built when nobody's checking the gaps.

The scary part isn't the number. It's timing — you don't find out until the selections meeting, when your leverage to negotiate or walk away is already gone.

Next email, {$name}, I'll show you a real budget where this played out, and what it actually cost.

— Jason

---

## Email 3 — Day 3
**Subject:** We caught $40–60k this family almost missed
**Preview text:** A real review, anonymized. Every number is a fact from an actual bid.

{$name},

Last email I talked about hidden exposure in general. Here's what it looked like on an actual project we reviewed recently (details changed to protect the family):

- The plans called for a full security, camera, and home automation package. The budget carried **$0** for it.
- The plans specified spray foam insulation. The bid priced standard fiberglass batts — **roughly half** the real cost.
- Several key allowances were set too thin to actually build from. Invisible until the selections meeting.

Total exposure: **$40,000–$60,000** the homeowner never saw coming, sitting quietly inside a bid that looked complete.

This is exactly what a Risk & Gap Report is built to catch, {$name} — a real builder reading your plans and your bid line by line, before you're locked in. Every finding is labeled by how sure we are: measured off your plans, a fact about your bid, or an honest regional estimate. No fake precision, ever.

**[See a sample report →]** (link to getlevelground.com/sample-report.html — plain text link, not a button)

— Jason

---

## Email 4 — Day 5
**Subject:** Founding price — $99 for a second set of eyes
**Preview text:** First 10 reports only. Then it's $299.

{$name}, here's the offer, plainly:

For **$99** — the founding price, first 10 reports only, then $299 — a real custom-home builder reviews your plans (and your bid, if you have one) and hands you back:

- **Missing scopes** — the line items that should be there and aren't
- **Lowball allowances** — flagged with a realistic range for what you actually want
- **Vague lump sums** — exactly where overages like to hide
- **The questions to ask your builder** before you sign, in plain English

No payment today, {$name}. We confirm your spot first, then send a secure payment link. And if you're not satisfied — full refund, no questions asked.

We never take a dime from builders, ever. You're the only person we work for.

**[Claim a founding spot →]** (link to getlevelground.com/start.html — style as a button, steel blue #5C90AC)

— Jason & Jessica

---

## Email 5 — Day 8 (last call + objection handling)
**Subject:** Last call on the founding price (+ the question everyone asks)
**Preview text:** "Will this make my builder mad?" Here's the honest answer.

{$name}, this is the last email in this short series — after this, you'll only hear from us if you reach out, or occasionally when we have something worth saying.

Before you decide, the question almost everyone asks: **"Will this make my builder mad?"**

Honest answer — a good builder welcomes an informed client. We're not here to bash builders; we are one. This report isn't ammunition for an argument. It's better questions for a calmer conversation, before you're locked into a contract.

The founding price ($99, first 10 reports, then $299) is still open, but not for long. Here's the math that matters: you're about to make the largest purchase of your life. If we catch even one lowball allowance or missing scope, the report pays for itself many times over. If we don't find anything — full refund.

**[Have a builder read my bid →]** (link to getlevelground.com/start.html — style as a button, steel blue #5C90AC)

Whatever you decide, {$name}, we're glad you're going into this with your eyes open.

— Jason & Jessica
Level Ground — getlevelground.com
