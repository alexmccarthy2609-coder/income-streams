# Invoice Generator

A web app for freelancers and small businesses to create, save and download
professional PDF invoices. Built with Python, FastAPI (web framework),
SQLAlchemy + SQLite (database) and fpdf2 (PDF library).

**Features:** sign up / log in · business details saved once and reused ·
saved clients (added automatically when you invoice someone new) ·
invoice history with edit, re-download and delete · automatic invoice numbers ·
dashboard with money owed, overdue and paid this month · mark invoices paid ·
overdue invoices flagged automatically · chart of money received per month ·
Free plan (3 invoices/month) and Pro plan (£6/month, unlimited) paid through Stripe.

## Files
| File | What it does |
|------|--------------|
| `main.py` | The web server: every page and what happens when a form is submitted |
| `db.py` | The database tables: users, clients, invoices, invoice items |
| `auth.py` | Password hashing and checking who is logged in |
| `pdf.py` | Draws the invoice PDF |
| `billing.py` | Free/Pro plans, the monthly limit, and talking to Stripe |
| `setup_stripe.py` | One-off script that creates the Pro plan in your Stripe account |
| `.env.example` | Template for your secret settings (copy it to `.env`) |
| `../render.yaml` | Tells Render how to run the app and its database online |
| `templates/` | The HTML pages (`base.html` is the shared layout and menu) |
| `static/style.css` | How everything looks |
| `tests/` | Automated checks that the app works |
| `requirements.txt` | The Python libraries the app needs |

Your data is stored in `invoices.db`, created automatically the first time you run the app.
Delete that file to start again from scratch. If you used an older version of the
app, your existing `invoices.db` is upgraded automatically when the app starts.

## Run it on your computer
1. Install Python 3.11+ from https://www.python.org/downloads/
   (Windows: tick **"Add Python to PATH"** during install).
2. Open a terminal (Windows: "Command Prompt"; Mac: "Terminal") in this folder.
3. Create a private space for the libraries and install them:
   ```
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # Mac / Linux
   pip install -r requirements.txt
   ```
4. Start the app:
   ```
   uvicorn main:app --reload
   ```
5. Open http://127.0.0.1:8000 in your browser and create an account.
   Press `Ctrl+C` in the terminal to stop.

## Run the tests
```
pytest
```
You should see `25 passed`. Run this after every change to check nothing broke.

## Set up payments (Stripe)
The app works without this; the Upgrade button stays greyed out until it's done.
Everything below uses Stripe's **test mode**, so no real money moves.

1. Create a free account at https://stripe.com. Make sure **Test mode** is switched on (top right).
2. Copy `.env.example` to a new file called `.env`.
3. In Stripe go to **Developers → API keys**, copy the **Secret key** (starts `sk_test_`) and
   paste it into `.env` as `STRIPE_SECRET_KEY=sk_test_...`
4. Create the Pro plan in your Stripe account:
   ```
   python setup_stripe.py
   ```
   Copy the `STRIPE_PRICE_ID=price_...` line it prints into `.env`.
5. Restart the app, log in, click **Upgrade**, then **Upgrade to Pro**. On Stripe's page pay with
   the test card `4242 4242 4242 4242`, any future expiry date, any CVC. You're now on Pro.
6. To let customers cancel or change card, switch on the customer portal once:
   Stripe dashboard → **Settings → Billing → Customer portal** → **Activate**.

### Webhooks (so cancellations and failed payments are noticed)
Stripe tells the app about changes by calling `/stripe/webhook`. On your own computer:
1. Install the Stripe CLI: https://docs.stripe.com/stripe-cli
2. Run `stripe login`, then:
   ```
   stripe listen --forward-to localhost:8000/stripe/webhook
   ```
3. Copy the `whsec_...` secret it prints into `.env` as `STRIPE_WEBHOOK_SECRET`, restart the app,
   and leave `stripe listen` running while you test.

Once the app is online (step 5) you'll add the webhook in the Stripe dashboard instead.

## Put it online (Render)
The repository includes `render.yaml`, which sets up the app **and** a Postgres database in one go.

1. Sign up at https://render.com using **Sign in with GitHub**.
2. Click **New → Blueprint**, connect the `income-streams` repository, and click **Apply**.
3. Render asks for the secret settings (leave the Stripe ones blank for now if you haven't set up Stripe):
   - `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`: same values as your `.env`
   - `STRIPE_WEBHOOK_SECRET`: from step 5 below
   - `CONTACT_EMAIL`: the email customers can reach you on (shown on the Privacy and Terms pages)
4. Wait for the build to finish (a few minutes). Your app is live at the `https://....onrender.com`
   address Render shows. `SECRET_KEY` and the database are filled in automatically.
5. **Stripe webhook:** Stripe dashboard → **Developers → Webhooks → Add endpoint**:
   - URL: `https://YOUR-APP.onrender.com/stripe/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.created`,
     `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy the signing secret (`whsec_...`) into Render → your service → **Environment** →
     `STRIPE_WEBHOOK_SECRET`, then save (the app restarts).

Every time new code is pushed to GitHub, Render redeploys automatically.

**Free vs paid hosting:** the blueprint starts on Render's free plans. Free apps go to sleep when
nobody uses them (the first visit then takes ~1 minute) and free databases expire after a limited time,
so before real customers rely on it, switch the web service to **Starter** and the database to a paid
plan in the Render dashboard.

### Running the tests against Postgres (optional)
```
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/empty_test_db pytest
```

## Roadmap
- [x] Step 1: Form → PDF invoice
- [x] Step 2: User accounts, saved clients and invoices
- [x] Step 3: Dashboard (paid / unpaid / overdue)
- [x] Step 4: Stripe subscriptions (free + paid plan)
- [x] Step 5: Ready to deploy online (Render) + landing page, privacy and terms pages
