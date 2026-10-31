import io
from fpdf import FPDF
from app.models import Invoice


class PDFInvoice(FPDF):
    def header(self):
        # Company Brand
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(30, 41, 59)  # Slate 800
        self.cell(0, 10, "BRIGHTLOOP SOFTWARE", ln=True, align="L")
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)  # Slate 500
        self.cell(0, 5, "Cloud Subscription & Enterprise Billing", ln=True, align="L")
        self.cell(0, 5, "support@brightloop.com | https://brightloop-demo.vercel.app", ln=True, align="L")
        self.ln(5)
        self.set_draw_color(226, 232, 240)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(226, 232, 240)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, "Brightloop Software Systems -- Auto-generated Tax Invoice", align="C", ln=True)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")


def generate_invoice_pdf(invoice: Invoice) -> bytes:
    pdf = PDFInvoice(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=30)
    pdf.add_page()

    # Invoice Metadata & Customer Box
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(100, 8, f"INVOICE {invoice.number}", ln=False)
    
    status_text = f"STATUS: {invoice.status.upper()}"
    pdf.set_font("Helvetica", "B", 10)
    if invoice.status == "paid":
        pdf.set_text_color(22, 101, 52)  # Emerald green
    elif invoice.status == "confirmed":
        pdf.set_text_color(30, 58, 138)  # Blue
    else:
        pdf.set_text_color(100, 116, 139)
    pdf.cell(90, 8, status_text, ln=True, align="R")

    pdf.ln(2)

    # Two column info
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(95, 5, "BILLED TO:", ln=False)
    pdf.cell(95, 5, "INVOICE DETAILS:", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(15, 23, 42)
    
    cust_name = invoice.customer.name if invoice.customer else "Valued Customer"
    cust_email = invoice.customer.email if invoice.customer else ""
    
    pdf.cell(95, 5, cust_name, ln=False)
    pdf.cell(95, 5, f"Invoice Date: {invoice.invoice_date}", ln=True)

    pdf.cell(95, 5, cust_email, ln=False)
    pdf.cell(95, 5, f"Payment Due: {invoice.due_date} (Net {invoice.payment_terms_days} days)", ln=True)

    pdf.cell(95, 5, f"Subscription: {invoice.subscription.number if invoice.subscription else 'N/A'}", ln=False)
    pdf.cell(95, 5, f"Billing Period: {invoice.period_start} to {invoice.period_end}", ln=True)

    pdf.ln(8)

    # Line Items Table Header
    pdf.set_fill_color(241, 245, 249)  # Slate 100
    pdf.set_text_color(51, 65, 85)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(80, 8, " Description", fill=True, border=1)
    pdf.cell(20, 8, " Qty", fill=True, border=1, align="C")
    pdf.cell(28, 8, " Unit Price", fill=True, border=1, align="R")
    pdf.cell(28, 8, " Tax Rate", fill=True, border=1, align="R")
    pdf.cell(34, 8, " Line Total", fill=True, border=1, align="R")
    pdf.ln(8)

    # Line items
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    for line in invoice.lines:
        desc_text = f" {line.description}"
        if len(desc_text) > 42:
            desc_text = desc_text[:40] + "..."
        pdf.cell(80, 7, desc_text, border=1)
        pdf.cell(20, 7, str(line.quantity), border=1, align="C")
        pdf.cell(28, 7, f"${float(line.unit_price):,.2f}", border=1, align="R")
        pdf.cell(28, 7, f"{float(line.tax_rate):.1f}%", border=1, align="R")
        pdf.cell(34, 7, f"${float(line.total):,.2f} ", border=1, align="R")
        pdf.ln(7)

    pdf.ln(4)

    # Discounts section if any
    if invoice.discounts:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(185, 28, 28)  # Red
        for disc in invoice.discounts:
            pdf.cell(156, 6, f" Discount Applied: {disc.description}", align="R")
            pdf.cell(34, 6, f"-${float(disc.discount_amount):,.2f} ", align="R")
            pdf.ln(6)

    # Totals Summary Box
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)
    
    pdf.cell(156, 6, "Subtotal:", align="R")
    pdf.cell(34, 6, f"${float(invoice.subtotal):,.2f} ", align="R")
    pdf.ln(6)

    pdf.cell(156, 6, "Tax:", align="R")
    pdf.cell(34, 6, f"${float(invoice.tax_total):,.2f} ", align="R")
    pdf.ln(6)

    if float(invoice.discount_total) > 0:
        pdf.cell(156, 6, "Total Discounts:", align="R")
        pdf.cell(34, 6, f"-${float(invoice.discount_total):,.2f} ", align="R")
        pdf.ln(6)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(156, 8, "Total Due:", align="R")
    pdf.cell(34, 8, f"${float(invoice.total):,.2f} ", align="R")
    pdf.ln(8)

    # Payment instructions note
    pdf.ln(6)
    pdf.set_fill_color(248, 250, 252)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 116, 139)
    payment_terms_note = f"Payment is due within {invoice.payment_terms_days} days of invoice date. Please make transfers to Brightloop Software Inc. Bank Account referencing invoice number {invoice.number}."
    pdf.multi_cell(190, 5, payment_terms_note, fill=True, border=1)

    return bytes(pdf.output())

