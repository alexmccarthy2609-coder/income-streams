# SiteWatch: uptime & SSL monitoring SaaS

Users sign up with just an email and add websites. SiteWatch checks every site every 5 minutes and emails the owner when a site
goes down, when it recovers, and 14 days before its SSL certificate expires.

- **Free:** 3 sites · **Pro:** 50 sites, as a monthly Stripe subscription
- Python + FastAPI + SQLite, all in one process, cheap to host ($5/month handles thousands of sites)
- Login uses a private dashboard link sent by email (no passwords to manage)
- Blocks private and internal addresses so users can't make your server probe your own network

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000, sign up, and copy the dashboard link from the console log
pytest -q
```

## Go live (about an hour)

1. **Host:** deploy the Dockerfile to Railway, Fly.io or Render (attach a volume at `/data`), or to any $5 VPS.
   Run **one** instance, since the checker runs inside the web process.
2. **Domain:** point `sitewatch.yourdomain.com` at it and set `BASE_URL`.
3. **Email:** create a free [Resend](https://resend.com) or Brevo account, verify your domain, and fill in the `SMTP_*` settings.
4. **Stripe:**
   - Create a product "SiteWatch Pro" with a recurring $9/month price, then a **Payment Link** for it → `STRIPE_PAYMENT_LINK`.
   - Developers → Webhooks → add `https://sitewatch.yourdomain.com/stripe/webhook` with the events
     `checkout.session.completed` and `customer.subscription.deleted` → `STRIPE_WEBHOOK_SECRET`.
   - Settings → Billing → Customer portal → enable it and copy the link → `STRIPE_PORTAL_LINK`.
   - Test the whole flow in Stripe **test mode** before switching to live keys.
5. Copy `.env.example` to `.env`, fill it in, and deploy.

## Getting customers

Focus on **freelance web developers and small agencies**. They manage many client sites and lose clients
when a site goes down unnoticed, which makes the 50-site Pro plan an easy sell.
- Post in r/webdev, r/freelance and r/Wordpress, Indie Hackers, and WordPress/Webflow Facebook groups
- Launch on Product Hunt once a few people are using it
- Write "how to monitor SSL expiry for free" style posts that link to the free tier
- Offer free Pro to your first 10 agency users in exchange for feedback and testimonials

## Ideas for later versions
Public status pages, Slack/SMS alerts, 1-minute checks on a higher tier, keyword checks ("page must contain X").
