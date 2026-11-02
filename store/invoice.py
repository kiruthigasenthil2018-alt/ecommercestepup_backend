from io import BytesIO
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DARK = colors.HexColor("#2F4F4F")

def build_invoice(o):
    buf = BytesIO(); st = getSampleStyleSheet(); S = settings.STORE
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm, title=f"Invoice {o.number}")
    h = ParagraphStyle("h", parent=st["Title"], textColor=DARK, alignment=0, fontSize=24, spaceAfter=2)
    sm = ParagraphStyle("sm", parent=st["Normal"], fontSize=9, leading=12)
    rs = lambda n: f"Rs. {n:,}"
    el = [Paragraph("StepUp.in", h), Paragraph(f"{S['address']}<br/>Phone: {S['phone']} &nbsp;|&nbsp; stepup@gmail.com", sm), Spacer(1, 8),
          Paragraph("<b>TAX INVOICE / BILL</b>", st["Heading3"])]
    meta = [["Invoice no", f"#{o.number}", "Date", o.created.strftime("%d %b %Y, %I:%M %p")],
            ["Payment", o.get_payment_display() + (f" (**** {o.card_last4})" if o.card_last4 else ""), "Order status", o.get_status_display()]]
    t = Table(meta, colWidths=[28*mm, 62*mm, 22*mm, 62*mm]); t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    el += [t, Spacer(1, 8), Paragraph(f"<b>Bill to / Ship to</b><br/>{o.first_name} {o.last_name}<br/>{o.address}{', ' + o.landmark if o.landmark else ''}<br/>{o.city}, {o.state} - {o.pincode}<br/>Phone: {o.phone} | {o.email}", sm), Spacer(1, 10)]
    rows = [["#", "Item", "Size", "Qty", "Price", "Amount"]] + [[i + 1, Paragraph(x.name, sm), x.size, x.quantity, rs(x.price), rs(x.price * x.quantity)] for i, x in enumerate(o.items.all())]
    it = Table(rows, colWidths=[8*mm, 82*mm, 14*mm, 12*mm, 28*mm, 30*mm], repeatRows=1)
    it.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), .4, colors.grey), ("ALIGN", (3, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    tot = [["Subtotal", rs(o.subtotal or o.total)]]
    if o.discount: tot.append([f"First-order offer ({settings.FIRST_ORDER['percent']}% off)", "- " + rs(o.discount)])
    tot += [["Delivery", "Free"], ["TOTAL", rs(o.total)]]
    tt = Table(tot, colWidths=[60*mm, 35*mm], hAlign="RIGHT"); tt.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 10), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("LINEABOVE", (0, -1), (-1, -1), .8, DARK)]))
    el += [it, Spacer(1, 8), tt, Spacer(1, 10)]
    if o.gift: el.append(Paragraph(f"<b>Free gift included:</b> {settings.FIRST_ORDER['gift']} (first-order offer)", sm))
    el += [Spacer(1, 14), Paragraph("Thank you for shopping with StepUp.in! 7-day easy return &amp; exchange. This is a computer-generated bill.", sm)]
    doc.build(el); return buf.getvalue()
