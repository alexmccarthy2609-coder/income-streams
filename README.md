# Income Streams

Products, each in its own folder:

| | Stream | Model | Folder |
|---|---|---|---|
| 1 | **OfficeKit**: office automation toolkit (Excel, PDF, rename, CSV, scraping) | One-off sale, $12–19 on Gumroad / Lemon Squeezy. Also serves as your **freelance portfolio** | [`toolkit/`](toolkit/) |
| 2 | **SiteWatch**: website uptime & SSL monitoring | SaaS: free tier + $9/month Pro via Stripe | [`sitewatch/`](sitewatch/) |
| 3 | **Invoice app**: invoice generator for freelancers and small businesses (built, not yet online) | SaaS: Free + Pro (£6/month) | [`invoice-app/`](invoice-app/) |

**Why OfficeKit + SiteWatch:** OfficeKit can earn within days and needs no hosting. SiteWatch takes longer to build an
audience, but subscriptions add up month after month. The freelance work OfficeKit attracts also pays
the bills while SiteWatch grows.

## 30-day launch plan

**Week 1: OfficeKit live**
- [ ] `cd toolkit && python build_product.py`, then upload `dist/officekit-1.0.0.zip` to Gumroad or Lemon Squeezy
- [ ] Paste the listing copy from `toolkit/SALES-PAGE.md`; replace `YOUR-DOMAIN` in the README with your support email
- [ ] Record a 30-second screen capture of `excel-merge` merging 20 files; post it to r/excel and r/automate

**Week 2: freelance**
- [ ] Create Upwork + Fiverr profiles: "I automate Excel, PDF & data tasks with Python"
- [ ] Use the OfficeKit demo as your portfolio; bid on 3–5 small automation jobs a day
- [ ] Every client job is a candidate for a new OfficeKit tool (v1.1, v1.2…)

**Week 3: SiteWatch live**
- [ ] Follow `sitewatch/README.md` → "Go live" (host + domain + Resend + Stripe test mode)
- [ ] Monitor your own sites with it for a few days, then switch Stripe to live mode

**Week 4: SiteWatch customers**
- [ ] Post in r/webdev, r/freelance and r/Wordpress; DM 20 small web agencies offering free Pro for feedback
- [ ] Track: signups, active sites, free→Pro conversion

## Marketing assets (`marketing/`)
- `images/`: Gumroad cover + SiteWatch screenshots (regenerate with `python marketing/make_images.py`)
- `LAUNCH-POSTS.md`: Reddit posts, agency outreach message, Upwork profile, Fiverr gig
- Free OfficeKit Lite for GitHub: `cd toolkit && python build_product.py --lite`

## Running costs
Domain ~$12/year · hosting $0–5/month · Resend free tier · Stripe/Gumroad take a % per sale only.

## Realistic expectations
Most products earn nothing for the first few weeks; marketing matters as much as the code.
Judge each stream after ~60 days of real promotion. Keep the ones that get traction and drop the ones that don't.

## Development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e toolkit pytest && (cd toolkit && pytest -q)
pip install -r sitewatch/requirements.txt && (cd sitewatch && pytest -q)
```
