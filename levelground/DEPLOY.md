# Level Ground — Launch checklist (site goes live in ~15 minutes)

The `site\` folder is the complete website. Seven pages:
- `index.html` — landing page
- `start.html` — intake form (reserve a founding report)
- `checklist.html` — free magnet ("What a complete bid must include")
- `thanks.html` — post-submit page
- `sample-report.html` — the sample Risk & Gap Report
- `privacy.html`, `terms.html` — legal pages, footer-linked

Forms run on **Formspree** — two dedicated endpoints, zero backend:
- Checklist signup (`index.html`) → `formspree.io/f/xgojddlv`
- Intake / report reservation (`start.html`) → `formspree.io/f/mrewjjyl`

This works on any static host, including Vercel.

## 1. Deploy on Vercel (free, ~5–10 min)

You already have a Vercel account (used for Bezerks). Since this site is plain HTML with no Git repo, the fastest path is the **Vercel CLI** — no GitHub setup required:

1. Open a terminal (PowerShell) and install the CLI once:
   ```
   npm i -g vercel
   ```
2. Move into the site folder:
   ```
   cd "C:\Users\jason\OneDrive\Desktop\Level Ground\site"
   ```
3. Deploy:
   ```
   vercel
   ```
   - It opens your browser to log in (use your existing Vercel account) — approve it.
   - Answers to the prompts: **Set up and deploy? Y** · **Which scope?** your account · **Link to existing project? N** · **Project name?** `level-ground` (or accept default) · **Directory?** press Enter (current folder) · **Override settings? N**
4. It gives you a preview URL (`level-ground-xxxx.vercel.app`). Open it and click through every page.
5. Ship it to production:
   ```
   vercel --prod
   ```
   That's your live URL until the custom domain is connected.

_(Alternative, if you'd rather not touch a terminal: create an empty GitHub repo, push the `site` folder to it, then in the Vercel dashboard → Add New → Project → Import that repo. Slower to set up once, but every future edit auto-deploys on push — ask Claude if you want this switched on later.)_

## 2. Connect getlevelground.com (~5 min)
1. Vercel dashboard → your project → **Settings → Domains** → Add `getlevelground.com`.
2. Vercel shows you the DNS records to add (usually an A record + a CNAME for `www`). Log in wherever you bought the domain → add those records.
3. Wait for DNS to propagate (minutes to a few hours). HTTPS certificate is automatic.

## 3. Confirm the forms work (~2 min)
1. On the live site, submit the checklist form and the intake form yourself with a test email.
2. Check the inbox tied to your Formspree account — you should get both, one from each form (checklist and intake are now separate Formspree forms, so check both in the dashboard).
3. If nothing arrives, check Formspree's dashboard → each form → Submissions (it logs everything even if email delivery lags).

## 4. Analytics (optional now, recommended before the FB post)
Vercel Analytics (built in, free tier available in the dashboard) or a free GA4 snippet — ask Claude to add either.

## Still pending (before taking money)
- [ ] Georgia LLC for Level Ground (~$100, online) — firewall from J&J
- [ ] Fresh Stripe account under the LLC → payment links for the founding 10
- [ ] Trademark screen on "Level Ground" in this category
- [ ] The Gate 1 Facebook post (drafted, waiting on you)

## The flow as built (no payments needed yet)
FB post → getlevelground.com → they either:
a) grab the checklist (you get their email via Formspree), or
b) reserve a founding report via the intake form (you get all their build details via Formspree).
You reply with the secure upload link (Google Drive/Dropbox request link works fine for the first 10) and a payment link when Stripe is live.
