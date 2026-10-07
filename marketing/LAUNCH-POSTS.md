# Launch posts: ready to paste

Before posting anywhere, **read the subreddit's rules**. Many ban self-promotion or only allow it
on certain days. Lead with something genuinely useful, mention the product once, and reply to every comment.
Space posts a few days apart rather than posting everywhere on day one.

---

## 1. r/excel (or r/automate): OfficeKit

**Title:** I got tired of copy-pasting 12 monthly reports into one sheet, so I wrote a one-line merger

**Body:**
Every month I had to combine a folder of sales spreadsheets that *mostly* had the same columns,
except someone always adds "Region" or renames "E-mail" to "Email".

So I wrote a small Python tool that:
- merges any number of .xlsx and .csv files
- matches columns **by name**, so different column orders and extra columns don't break anything
- adds a `source_file` column so you can trace every row back

```
officekit excel-merge sales_*.xlsx -o all_sales.xlsx
```

The core logic is about 40 lines with openpyxl. Happy to share how it works if anyone wants to build their own.
I also packaged it with some PDF/rename/CSV-cleanup tools (link in my profile, or ask).

*(Attach: a screen recording or `marketing/images/officekit-cover.png`)*

---

## 2. r/learnpython / r/Python: free Lite edition (once it's on GitHub)

**Title:** Made a small CLI to bulk-rename files safely (preview first, handles swaps): open source

**Body:**
Built this for renaming scanned receipts: `officekit rename scans/*.jpg -t "{date}_receipt_{n:02}{ext}"`

A few things I learned that might help others writing file tools:
1. **Dry-run by default.** Nothing changes until you pass `--apply`.
2. **Two-phase rename.** Renaming a→b and b→a at once fails naively, so it renames everything to temp names first.
3. **Refuse to overwrite** files outside the batch, and refuse templates that produce duplicate names.

Code + tests: <GITHUB LINK>. Feedback welcome!

---

## 3. r/webdev / r/freelance / r/Wordpress: SiteWatch

**Title:** How do you find out when a client's site goes down or their SSL expires?

**Body:**
I manage a handful of small-business sites, and last year one client's SSL certificate expired over a
weekend. Their shop showed a big browser security warning for 2 days before anyone noticed.

I built a simple monitor for myself: it checks each site every 5 minutes, emails me when one goes
down or comes back, and warns me 14 days before any certificate expires.

It's free for up to 3 sites if it's useful to anyone: <LINK>. Mostly curious what others use.
UptimeRobot? Something self-hosted?

*(Ending with a question invites discussion, which matters more than the link.)*

---

## 4. Direct message to small web agencies (find them on Google Maps / Clutch / LinkedIn)

> Hi {name}, I noticed {agency} looks after sites for a lot of local businesses. I built a lightweight
> uptime + SSL-expiry monitor aimed at agencies (one dashboard, email alerts the moment a client site
> drops). I'm looking for 10 agencies to use the Pro plan free for 3 months in exchange for honest
> feedback. Would that be useful to you? Happy to set it up for you in 2 minutes.

Send 5–10 a day, personalised. Expect a 5–10% reply rate; that's normal.

---

## 5. Upwork profile

**Title:** Python Automation Developer | Excel, PDF & Data Workflows

**Overview:**
I turn hours of repetitive office work into a single click.

Typical projects:
• Merging and cleaning Excel/CSV reports from multiple sources
• Splitting, merging and extracting data from PDFs (invoices, contracts, statements)
• Bulk file organisation and renaming
• Web-table scraping into spreadsheets (respecting site terms)
• Scheduled scripts that run automatically and email you the result

You get clean, documented Python code with tests, and a short guide so anyone on your team can run it.
See my toolkit for examples of my work: <GITHUB LINK>

**Pricing to start** (Upwork and Fiverr price in US dollars even for UK sellers): bid $25–35/hour (about £20–28) or fixed $50–150 for small scripts. Raise your rate after your first 5 five-star reviews.

---

## 6. Fiverr gig

**Title:** I will automate your Excel, CSV or PDF task with a Python script

**Packages:**
| | Basic, $40 | Standard, $90 | Premium, $200 |
|---|---|---|---|
| Scope | One simple task (e.g. merge files) | Multi-step workflow | Full workflow + scheduling |
| Delivery | 2 days | 4 days | 7 days |
| Revisions | 1 | 2 | 3 |
| Includes | Script + instructions | + Excel/CSV formatting | + automated runs + email reports |

Fiverr shows buyers prices in their own currency and pays you out in GBP.

**Gig image:** `marketing/images/officekit-cover.png`
