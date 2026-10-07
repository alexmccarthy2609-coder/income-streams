# OfficeKit: Office Automation Toolkit

Five command-line tools that take care of repetitive office tasks.

| Command | What it does |
|---|---|
| `excel-merge` | Combine any number of `.xlsx` / `.csv` files into one workbook. Columns are matched by name, and each row records the file it came from. |
| `pdf-merge` | Join PDFs in the order you give them. |
| `pdf-split` | Split a PDF into single pages or into ranges (`1-3,5,7-`). |
| `pdf-text` | Extract all text from a PDF. |
| `rename` | Bulk-rename files with a template (`invoice_{n:03}{ext}`, `{date}_{name}{ext}`). It previews changes before renaming anything. |
| `clean-csv` | Tidy a contact list: trim spaces, lowercase emails, normalise phone numbers, remove duplicates and blank rows, and flag invalid emails. |
| `scrape` | Save a table (or all links) from a web page as CSV. Respects robots.txt. |

## Install

You need Python 3.10 or newer ([python.org](https://www.python.org/downloads/)).

```bash
pip install ./officekit        # from the unzipped folder
officekit --help
```

## Examples

```bash
# Merge every monthly sales file into one workbook
officekit excel-merge sales_*.xlsx -o all_sales.xlsx

# Pull pages 1-3 and 10 onward out of a contract
officekit pdf-split contract.pdf -r "1-3,10-" -o parts/

# Rename scanned receipts by date (preview, then apply)
officekit rename scans/*.jpg -t "{date}_receipt_{n:02}{ext}"
officekit rename scans/*.jpg -t "{date}_receipt_{n:02}{ext}" --apply

# Clean an exported lead list
officekit clean-csv leads.csv -o leads_clean.csv

# Grab the 2nd table on a page
officekit scrape https://example.com/prices --table 2 -o prices.csv
```

Every tool can also be imported in your own scripts:

```python
from officekit import excel_merge
excel_merge.merge([Path("a.xlsx"), Path("b.csv")], Path("out.xlsx"))
```

## Support

Reply to your purchase receipt email with the command you ran and the error message, and you will get help within 2 working days.
