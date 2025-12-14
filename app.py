# --- UPDATED IMPORTS ---
import streamlit as st
import pandas as pd
import os
import uuid
import io
import hashlib
import json
from datetime import datetime
import plotly.express as px
import matplotlib.pyplot as plt

# --- REPORTLAB IMPORTS ---
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    # NEW IMPORTS FOR FONTS
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# ... [Keep your CONFIGURATION, AUTH, and DATA FUNCTIONS the same] ...

# --- UPDATED PDF GENERATOR ---
def generate_pdf(member_name, member_details, year, member_since, lifetime_total, 
                 df_member_year, df_global_year, medical_df, header_msg, footer_msg):
    
    if not HAS_PDF: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # --- 1. SETUP FONTS ---
    # We try to register the Bengali font. If missing, we skip the Bengali text to prevent crashes.
    has_bengali_font = False
    try:
        # Assumes Kalpurush.ttf is in the same folder as this script
        pdfmetrics.registerFont(TTFont('Kalpurush', 'Kalpurush.ttf'))
        
        # Create a style for Bengali text
        bengali_style = ParagraphStyle(
            name='BengaliStyle',
            parent=styles['Normal'],
            fontName='Kalpurush',
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=colors.black
        )
        has_bengali_font = True
    except:
        # If font file not found, we cannot print Bengali
        st.warning("⚠️ 'Kalpurush.ttf' font file missing. Bengali text will not appear in PDF.")
        bengali_style = styles['Normal'] # Fallback

    # Custom Styles
    styles.add(ParagraphStyle(name='Highlight', parent=styles['Normal'], fontSize=12, textColor=colors.darkblue, spaceAfter=12))

    # --- 2. REPORT CONTENT ---
    
    # Title
    elements.append(Paragraph(f"Member Contribution Report", styles['Title']))
    elements.append(Spacer(1, 10))

    # Member Profile
    profile_text = [
        f"<b>Name:</b> {member_name}",
        f"<b>Member Since:</b> {member_since}",
        f"<b>Address:</b> {member_details.get('address', '-')}",
        f"<b>Phone/Email:</b> {member_details.get('phone', '-')} / {member_details.get('email', '-')}",
        f"<b>Report Year:</b> {year}"
    ]
    for line in profile_text:
        elements.append(Paragraph(line, styles['Normal']))
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>LIFETIME CONTRIBUTIONS: {CURRENCY}{lifetime_total:,.2f}</b>", styles['Highlight']))
    elements.append(Spacer(1, 15))
    
    if header_msg:
        elements.append(Paragraph(f"<i>{header_msg}</i>", styles['Italic']))
        elements.append(Spacer(1, 15))

    # Table 1: Member's Monthly Contributions
    elements.append(Paragraph(f"<b>1. Your Contributions in {year}</b>", styles['Heading3']))
    
    mem_monthly = df_member_year.groupby('Month')['Amount'].sum().reset_index()
    t1_data = [["Month", "Amount"]]
    t1_total = 0
    for m_num in range(1, 13):
        row = mem_monthly[mem_monthly['Month'] == m_num]
        amt = row['Amount'].sum() if not row.empty else 0.0
        t1_data.append([MONTH_NAMES[m_num-1], f"{amt:,.2f}"])
        t1_total += amt
    t1_data.append(["TOTAL", f"{t1_total:,.2f}"])

    t1 = Table(t1_data, colWidths=[200, 150], hAlign='LEFT')
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkgreen),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 20))

    # Table 2: Charity Overall Spending
    elements.append(Paragraph(f"<b>2. Charity Overall Donations in {year} (Impact)</b>", styles['Heading3']))
    
    global_monthly = df_global_year.groupby('Month')['Amount'].sum().reset_index()
    t2_data = [["Month", "Total Distributed"]]
    t2_total = 0
    for m_num in range(1, 13):
        row = global_monthly[global_monthly['Month'] == m_num]
        amt = row['Amount'].sum() if not row.empty else 0.0
        t2_data.append([MONTH_NAMES[m_num-1], f"{amt:,.2f}"])
        t2_total += amt
    t2_data.append(["TOTAL", f"{t2_total:,.2f}"])

    t2 = Table(t2_data, colWidths=[200, 150], hAlign='LEFT')
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.navy),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 20))

    # Charts Section
    elements.append(Paragraph(f"<b>3. Distribution Analysis ({year})</b>", styles['Heading3']))
    elements.append(Spacer(1, 10))

    fund_stats = df_global_year.groupby("Category")['Amount'].sum()
    img_fund = create_pie_chart_image(fund_stats, "By Fund Source")
    usage_stats = df_global_year.groupby("SubCategory")['Amount'].sum()
    img_usage = create_pie_chart_image(usage_stats, "By Usage")
    
    img_med = None
    if not medical_df.empty:
        med_stats = medical_df.groupby("Medical")['Amount'].sum()
        img_med = create_pie_chart_image(med_stats, "Medical Breakdown")

    # Row 1 Charts
    if img_fund and img_usage:
        chart_table_1 = Table([[img_fund, img_usage]], colWidths=[3.5*inch, 3.5*inch])
        chart_table_1.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        elements.append(chart_table_1)
        elements.append(Spacer(1, 15))
    elif img_fund: elements.append(img_fund)
    elif img_usage: elements.append(img_usage)

    # Row 2 Chart (Medical)
    if img_med:
        chart_table_2 = Table([[img_med]], colWidths=[7*inch])
        chart_table_2.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        elements.append(chart_table_2)
        elements.append(Spacer(1, 25))

    # --- ISLAMIC QUOTES SECTION (BENGALI) ---
    if has_bengali_font:
        # Border box for quotes
        elements.append(Spacer(1, 10))
        
        quran_text = """যারা আল্লাহর পথে নিজেদের মাল ব্যয় করে, তাদের (দানের) তুলনা সেই বীজের মত, যাত্থেকে সাতটি শীষ জন্মিল, প্রত্যেক শীষে একশত করে দানা এবং আল্লাহ যাকে ইচ্ছে করেন, বর্ধিত হারে দিয়ে থাকেন। বস্তুতঃ আল্লাহ প্রাচুর্যের অধিকারী, জ্ঞানময়। (সুরা বাকারাহ ২৬১)"""
        
        hadith_text = """আদী ইব্‌ন হাতিম (রাঃ) থেকে বর্ণিতঃ নবী (সাল্লাল্লাহু ‘আলাইহি ওয়া সাল্লাম) থেকে বর্ণিত। তিনি বলেন তোমরা জাহান্নামের আগুন থেকে বাঁচ (নিজেদের রক্ষা কর) যদিও তা খেজুরের টুকরা দ্বারাও হয়। (সামান্য বস্তু সাদাকা করতে পারলেও তা কর।) (সুনানে আন-নাসায়ী, হাদিস নং ২৫৫২)"""
        
        # Add to PDF
        elements.append(Paragraph("<b>Inspirational Quotes:</b>", styles['Normal']))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(quran_text, bengali_style))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(hadith_text, bengali_style))
        elements.append(Spacer(1, 20))

    # Footer Message
    if footer_msg:
        elements.append(Paragraph(footer_msg, styles['Normal']))
        elements.append(Spacer(1, 30))

    # Signature
    elements.append(Paragraph("_" * 30, styles['Normal']))
    elements.append(Paragraph("Authorized Signature", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer
