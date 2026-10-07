# Putting OfficeKit on sale on Gumroad (about 20 minutes)

You need these three files (sent to you in chat; also rebuildable with `python build_product.py`):
- `officekit-1.0.0.zip`: the product buyers download
- `officekit-cover.png`: 1280×720 cover
- `officekit-thumbnail.png`: 600×600 thumbnail

Gumroad's menus change occasionally. If a button is named slightly differently, look for the nearest match.

---

## 1. Create your account
1. Go to **gumroad.com** and tap **Start selling** (or Sign up).
2. Sign up with your email and pick a username. It becomes your store address
   (`USERNAME.gumroad.com`), so choose something professional.

## 2. Create the product
1. Go to **Products → New product**.
2. Fill in:
   - **Name:** `OfficeKit: Automate Spreadsheets, PDFs & File Admin with Python`
   - **Type:** Digital product
   - **Currency:** GBP (£). If it isn't offered here, set it in the product's settings or under Settings → Payments
   - **Price:** `9` (launch price; raise it to 15 after your first ~50 sales or a month)
3. Tap **Next: Customize** (or similar).

## 3. Fill in the product page
**Description** (paste this):

> Stop copy-pasting between spreadsheets. OfficeKit merges Excel files, splits and merges PDFs,
> bulk-renames files, cleans contact lists and scrapes web tables, each in one command.
>
> **Hours a week go on jobs a computer should do:**
> - Copying 12 monthly spreadsheets into one
> - Pulling pages out of a PDF to send a client
> - Renaming 300 scanned receipts one at a time
> - Removing duplicates from a lead list before importing it
>
> OfficeKit does each of these in one command.
>
> **What you get**
> - 7 tools: excel-merge, pdf-merge, pdf-split, pdf-text, rename, clean-csv, scrape
> - Works on Windows, Mac & Linux (needs free Python 3.10+)
> - Previews changes before renaming anything
> - Plain, readable Python code with tests, so you can adapt it
> - Commercial use allowed, including client work
> - Free updates
>
> **Who it's for:** admins, bookkeepers, virtual assistants, analysts, and anyone who knows a little Python.

- **Cover:** upload `officekit-cover.png`
- **Thumbnail:** upload `officekit-thumbnail.png`
- **Summary / "You'll get" line** (if shown): `7 Python automation tools + source code + commercial license`
- **URL slug** (under settings / custom permalink): `officekit`, so your link is `USERNAME.gumroad.com/l/officekit`

## 4. Upload the file
1. Open the **Content** tab.
2. Upload `officekit-1.0.0.zip`.
3. Add a line of text above it: *"Unzip, then follow README.md to install. Takes 2 minutes."*

## 5. Set up payouts (so the money reaches you)
1. **Settings → Payments**: add your bank details and complete the tax form Gumroad asks for.
2. Gumroad pays out to UK bank accounts weekly, and collects and pays UK/EU VAT for you, so you don't need to register for VAT.
3. Gumroad takes a fee per sale (10% + $0.50, taken automatically). There are no monthly costs.

## 6. Test, then publish
1. Tap **Publish**.
2. Open your product link in a private/incognito browser tab and check that it looks right.
3. Optional: create a 100%-off discount code for yourself (**Checkout → Discounts**) and "buy" it,
   to see exactly what a customer receives. Delete the code afterwards.

## 7. Tell Claude your product link
Once it's live, the link needs adding in two places:
- The free Lite edition (`build_product.py`, `STORE_URL`), which points readers to the paid version
- The launch posts in `marketing/LAUNCH-POSTS.md`
