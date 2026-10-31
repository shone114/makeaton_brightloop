import io
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from app.core.database import get_db
from app.models import Subscription, Invoice
from app.common.dependencies import require_staff_or_admin

router = APIRouter(prefix="/export", tags=["Excel & Data Export"])


def apply_header_styling(sheet, columns: list[str]):
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center")
    
    sheet.append(columns)
    for col_num in range(1, len(columns) + 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align
        sheet.column_dimensions[cell.column_letter].width = max(len(columns[col_num - 1]) + 6, 15)


@router.get("/subscriptions", dependencies=[Depends(require_staff_or_admin)])
def export_subscriptions_excel(db: Session = Depends(get_db)):
    subs = db.query(Subscription).order_by(desc(Subscription.created_at)).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Subscriptions"

    headers = ["Number", "Customer Name", "Customer Email", "Plan Name", "Billing Period", "Status", "Start Date", "End Date", "Payment Terms (Days)", "Billed Through"]
    apply_header_styling(ws, headers)

    for s in subs:
        ws.append([
            s.number,
            s.customer.name if s.customer else "",
            s.customer.email if s.customer else "",
            s.plan.name if s.plan else "",
            s.plan.billing_period if s.plan else "",
            s.status.upper(),
            str(s.start_date),
            str(s.end_date),
            s.payment_terms_days,
            str(s.billed_through) if s.billed_through else "Unbilled",
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Brightloop_Subscriptions.xlsx"'},
    )


@router.get("/invoices", dependencies=[Depends(require_staff_or_admin)])
def export_invoices_excel(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).order_by(desc(Invoice.invoice_date)).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"

    headers = ["Invoice Number", "Customer Name", "Customer Email", "Subscription Ref", "Status", "Invoice Date", "Due Date", "Period Start", "Period End", "Subtotal ($)", "Tax ($)", "Discount ($)", "Grand Total ($)"]
    apply_header_styling(ws, headers)

    for inv in invoices:
        ws.append([
            inv.number,
            inv.customer.name if inv.customer else "",
            inv.customer.email if inv.customer else "",
            inv.subscription.number if inv.subscription else "",
            inv.status.upper(),
            str(inv.invoice_date),
            str(inv.due_date),
            str(inv.period_start),
            str(inv.period_end),
            float(inv.subtotal),
            float(inv.tax_total),
            float(inv.discount_total),
            float(inv.total),
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Brightloop_Invoices.xlsx"'},
    )
