"""Turns invoice data into a PDF file using the fpdf2 library."""

from pathlib import Path

from fpdf import FPDF

# DejaVu Sans (free to redistribute, licence in fonts/) can draw €, accents and
# the curly quotes phones type, which the PDF built-in fonts can't.
FONTS = Path(__file__).parent / "fonts"
FONT = "DejaVu"


def clean(text: str) -> str:
    # Drop invisible control characters that would show as boxes.
    return "".join(c for c in text if c in "\n\t" or c.isprintable())


def money(amount: float, symbol: str) -> str:
    return f"{symbol}{amount:,.2f}"


def build_invoice_pdf(inv: dict) -> bytes:
    """inv is a dict built in main.py. Returns the finished PDF as bytes."""
    sym = inv["currency_symbol"]
    pdf = FPDF(format="A4")
    pdf.add_font(FONT, "", str(FONTS / "DejaVuSans.ttf"))
    pdf.add_font(FONT, "B", str(FONTS / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    width = pdf.w - 40  # usable page width

    # --- Header: "INVOICE" on the left, invoice details on the right ---
    pdf.set_font(FONT, "B", 26)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(width / 2, 12, "INVOICE")
    pdf.set_font(FONT, "", 10)
    pdf.set_text_color(60, 60, 60)
    details = f"Invoice #: {inv['invoice_number']}\nDate: {inv['invoice_date']}\n"
    # UK invoices must show when the work was done; only print it when it differs.
    if inv.get("supply_date") and inv["supply_date"] != inv["invoice_date"]:
        details += f"Supply date: {inv['supply_date']}\n"
    details += f"Due: {inv['due_date']}"
    pdf.multi_cell(width / 2, 5, clean(details), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # --- From / Bill to, side by side ---
    top = pdf.get_y()
    business_details = inv["business_details"]
    if inv.get("vat_number"):
        business_details = f"{business_details}\nVAT No: {inv['vat_number']}".strip()
    for i, (label, name, address) in enumerate([
        ("FROM", inv["business_name"], business_details),
        ("BILL TO", inv["client_name"], inv["client_details"]),
    ]):
        pdf.set_xy(20 + i * width / 2, top)
        pdf.set_font(FONT, "B", 9)
        pdf.set_text_color(130, 130, 130)
        pdf.cell(width / 2, 5, label, new_x="LEFT", new_y="NEXT")
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(width / 2 - 5, 6, clean(name), align="L", new_x="LEFT", new_y="NEXT")
        pdf.set_font(FONT, "", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(width / 2 - 5, 5, clean(address), align="L", new_x="LEFT", new_y="NEXT")
    pdf.set_xy(20, max(pdf.get_y(), top + 30) + 8)

    # --- Line items table ---
    cols = [width * 0.52, width * 0.12, width * 0.18, width * 0.18]
    pdf.set_fill_color(37, 99, 235)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(FONT, "B", 10)
    for w, title, align in zip(cols, ["Description", "Qty", "Unit price", "Amount"], "LRRR"):
        pdf.cell(w, 9, title, fill=True, align=align)
    pdf.ln()

    pdf.set_font(FONT, "", 10)
    pdf.set_text_color(20, 20, 20)
    for n, item in enumerate(inv["items"]):
        pdf.set_fill_color(*((245, 247, 250) if n % 2 else (255, 255, 255)))
        # Long descriptions wrap onto extra lines; the row grows to fit.
        desc = clean(item["description"])
        lines = pdf.multi_cell(cols[0] - 2, 5, desc, align="L", dry_run=True, output="LINES")
        row_h = max(8, 5 * len(lines) + 3)
        if pdf.get_y() + row_h > pdf.page_break_trigger:
            pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        pdf.rect(x, y, width, row_h, style="F")
        pdf.set_xy(x + 1, y + 1.5)
        pdf.multi_cell(cols[0] - 2, 5, desc, align="L")
        pdf.set_xy(x + cols[0], y)
        for w, text in zip(cols[1:], [
            f"{item['quantity']:g}",
            money(item["unit_price"], sym),
            money(item["amount"], sym),
        ]):
            pdf.cell(w, 8, text, align="R")
        pdf.set_xy(x, y + row_h)

    # --- Totals, right-aligned ---
    pdf.ln(4)
    label_w, value_w = width * 0.25, width * 0.18
    totals = [("Subtotal", inv["subtotal"])]
    if inv["tax_rate"]:
        tax_name = "VAT" if inv.get("vat_number") else "Tax"
        totals.append((f"{tax_name} ({inv['tax_rate']:g}%)", inv["tax"]))
    for label, value in totals:
        pdf.set_x(20 + width - label_w - value_w)
        pdf.cell(label_w, 7, label, align="R")
        pdf.cell(value_w, 7, money(value, sym), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20 + width - label_w - value_w)
    pdf.set_font(FONT, "B", 12)
    pdf.cell(label_w, 10, "Total due", align="R")
    pdf.set_text_color(37, 99, 235)
    pdf.cell(value_w, 10, money(inv["total"], sym), align="R", new_x="LMARGIN", new_y="NEXT")

    # --- Notes / payment instructions ---
    if inv["notes"]:
        pdf.ln(8)
        pdf.set_text_color(130, 130, 130)
        pdf.set_font(FONT, "B", 9)
        pdf.cell(0, 5, "NOTES / PAYMENT DETAILS", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(60, 60, 60)
        pdf.set_font(FONT, "", 10)
        pdf.multi_cell(0, 5, clean(inv["notes"]), align="L")

    return bytes(pdf.output())
