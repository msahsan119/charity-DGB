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
    from reportlab.lib.enums import TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Charity Management System", layout="wide", page_icon="💚")

USER_FILE = "users.json"
MEMBERS_FILE = "members.json"
FONT_FILE_NAME = "custom_font.ttf" 
CURRENCY = "€"

INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

# --- QUOTES ---
QURAN_QUOTE = """ "The example of those who spend their wealth in the way of Allah is like a seed [of grain] which grows seven spikes, in each spike is a hundred grains. And Allah multiplies [His reward] for whom He wills. And Allah is all-Encompassing and Knowing." (Surah Al-Baqarah 2:261)"""
HADITH_QUOTE = """The Prophet (peace and blessings of Allah be upon him) said: "Protect yourselves from the Fire, even with half a date." (Sunan an-Nasa'i, 2552)"""

# --- 2. AUTHENTICATION & FILE FUNCTIONS ---
def get_user_db_file(username):
    clean_name = "".join(x for x in username if x.isalnum())
    return f"data_{clean_name}.csv"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_json_file(filename):
    if not os.path.exists(filename): return {}
    try:
        with open(filename, 'r') as f: return json.load(f)
    except: return {}

def save_json_file(filename, data):
    with open(filename, 'w') as f: json.dump(data, f)

def check_login(username, password):
    users = load_json_file(USER_FILE)
    if "admin" not in users: users["admin"] = hash_password("admin")
    if username in users and users[username] == hash_password(password): return True
    return False

# --- 3. SESSION INIT ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'show_reset_confirm' not in st.session_state: st.session_state.show_reset_confirm = False
if 'custom_font_path' not in st.session_state: st.session_state.custom_font_path = None

# =========================================================
# LOGIN SCREEN
# =========================================================
if not st.session_state.authenticated:
    st.title("🔒 Charity System Login")
    
    with st.sidebar:
        st.header("⚙️ Admin Tools")
        if os.path.exists(USER_FILE):
            with open(USER_FILE, "r") as f:
                st.download_button("💾 Backup Logins", f, "users_backup.json", "application/json")
        up_users = st.file_uploader("Restore Logins", type=['json'])
        if up_users:
            save_json_file(USER_FILE, json.load(up_users))
            st.success("Restored!")

    tabs = st.tabs(["Login", "Register"])
    with tabs[0]:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if check_login(u, p):
                    st.session_state.authenticated = True
                    st.session_state.username = u
                    st.rerun()
                else: st.error("Invalid credentials")
    with tabs[1]:
        with st.form("reg"):
            nu = st.text_input("New Username")
            np = st.text_input("New Password", type="password")
            if st.form_submit_button("Register"):
                users = load_json_file(USER_FILE)
                if nu in users: st.error("Exists")
                else:
                    users[nu] = hash_password(np)
                    save_json_file(USER_FILE, users)
                    st.success("Created! Please Login.")
    st.stop()

# =========================================================
# MAIN APP
# =========================================================
CURRENT_DB_FILE = get_user_db_file(st.session_state.username)

def load_data():
    expected_cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                     "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical", "Amount"]
    if os.path.exists(CURRENT_DB_FILE):
        try:
            df = pd.read_csv(CURRENT_DB_FILE)
            for col in expected_cols:
                if col not in df.columns: df[col] = ""
            return df
        except: return pd.DataFrame(columns=expected_cols)
    return pd.DataFrame(columns=expected_cols)

def save_data(df):
    df.to_csv(CURRENT_DB_FILE, index=False)

def get_fund_balance(df, fund_category, group_filter="All"):
    if df.empty: return 0.0
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    temp_df = df.copy()
    if group_filter != "All":
        temp_df = temp_df[temp_df['Group'] == group_filter]
    income = temp_df[(temp_df['Type'] == 'Incoming') & (temp_df['Category'] == fund_category)]['Amount'].sum()
    expense = temp_df[(temp_df['Type'] == 'Outgoing') & (temp_df['Category'] == fund_category)]['Amount'].sum()
    return income - expense

# --- HELPER: PIE CHART ---
def create_pie_chart_image(data_series, title):
    if data_series.empty: return None
    plt.figure(figsize=(6, 6))
    wedges, texts, autotexts = plt.pie(
        data_series, labels=data_series.index, autopct='%1.1f%%', 
        startangle=140, colors=plt.cm.Pastel1.colors, textprops={'fontsize': 10}
    )
    plt.title(title, fontsize=14, fontweight='bold')
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=400)
    img_buf.seek(0)
    plt.close()
    return Image(img_buf, width=3.2*inch, height=3.2*inch)

# --- ADVANCED PDF GENERATOR ---
# FIXED: Added df_summary_year to arguments
def generate_pdf(member_name, member_details, year, member_since, lifetime_total, 
                 df_member_year, df_donations_year, df_summary_year, medical_df, header_msg, footer_msg, custom_font_path=None):
    
    if not HAS_PDF: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # 1. SETUP FONTS
    font_name = 'Helvetica'
    if custom_font_path and os.path.exists(custom_font_path):
        try:
            pdfmetrics.registerFont(TTFont('Bengali', custom_font_path))
            font_name = 'Bengali'
        except: pass

    # Styles
    style_center = ParagraphStyle(name='Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12)
    style_title = ParagraphStyle(name='BigTitle', parent=styles['Title'], fontSize=20, textColor=colors.darkgreen, spaceAfter=5)
    style_normal = ParagraphStyle(name='MyNormal', parent=styles['Normal'], fontName=font_name, leading=14)
    style_bold = ParagraphStyle(name='MyBold', parent=styles['Normal'], fontName='Helvetica-Bold')
    style_highlight = ParagraphStyle(name='Highlight', parent=styles['Normal'], fontSize=12, textColor=colors.darkblue, spaceAfter=12)
    style_quote = ParagraphStyle(name='Quote', parent=styles['Normal'], fontSize=9, textColor=colors.darkgray, spaceAfter=10, leading=12, leftIndent=20, rightIndent=20)
    style_month = ParagraphStyle(name='Month', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.darkred, spaceBefore=6, spaceAfter=4)

    # 2. HEADER
    elements.append(Paragraph("Bismillah hir Rahmanir Rahim", style_center))
    elements.append(Paragraph("Sadaka Group Berlin", style_title))
    elements.append(Paragraph("Member Contribution Report", styles['Heading2']))
    elements.append(Spacer(1, 10))

    # 3. QUOTES
    elements.append(Paragraph(QURAN_QUOTE, style_quote))
    elements.append(Paragraph(HADITH_QUOTE, style_quote))
    elements.append(Spacer(1, 15))

    # 4. MEMBER DETAILS
    grp_name = member_details.get('group', 'Group')
    profile_text = [
        f"<b>Name:</b> {member_name}",
        f"<b>Member Since:</b> {member_since}",
        f"<b>Address:</b> {member_details.get('address', '-')}",
        f"<b>Phone/Email:</b> {member_details.get('phone', '-')} / {member_details.get('email', '-')}",
        f"<b>Report Year:</b> {year}"
    ]
    for line in profile_text:
        elements.append(Paragraph(line, style_normal))
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>LIFETIME CONTRIBUTIONS: {CURRENCY}{lifetime_total:,.2f}</b>", style_highlight))
    elements.append(Spacer(1, 15))
    
    # 5. APPRECIATION
    if header_msg:
        elements.append(Paragraph(f"<i>{header_msg}</i>", style_normal))
        elements.append(Spacer(1, 15))

    # 6. TABLE 1: Contributions
    elements.append(Paragraph(f"<b>1. Your Contributions in {year}</b>", style_bold))
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

    # 7. TABLE 2: DONATION LIST
    elements.append(Paragraph(f"<b>2. Complete Donation List ({grp_name}s) in {year}</b>", style_bold))
    
    if df_donations_year.empty:
        elements.append(Paragraph("No donations recorded for this period.", style_normal))
    else:
        grand_don_total = 0
        df_donations_year = df_donations_year.sort_values('Month')
        
        for m_num in range(1, 13):
            m_df = df_donations_year[df_donations_year['Month'] == m_num]
            if not m_df.empty:
                m_name = MONTH_NAMES[m_num-1]
                elements.append(Paragraph(f"<b>{m_name}</b>", style_month))
                
                t_dist_data = [["Beneficiary", "Address", "Reason", "Responsible", "Amount"]]
                m_total = 0
                for _, row in m_df.iterrows():
                    t_dist_data.append([
                        str(row['Name_Details']),
                        str(row['Address']),
                        str(row['Reason']),
                        str(row['Responsible']),
                        f"{row['Amount']:,.2f}"
                    ])
                    m_total += row['Amount']
                
                t_dist_data.append(["", "", "", "Total:", f"{m_total:,.2f}"])
                grand_don_total += m_total
                
                t_dist = Table(t_dist_data, colWidths=[100, 100, 100, 90, 60], hAlign='LEFT')
                t_dist.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.darkred),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('FONTNAME', (-1,-1), (-1,-1), 'Helvetica-Bold'),
                    ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
                    ('ALIGN', (0,0), (3,-1), 'LEFT'),
                ]))
                elements.append(t_dist)
                elements.append(Spacer(1, 10))
        
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"<b>TOTAL DONATIONS: {CURRENCY}{grand_don_total:,.2f}</b>", style_highlight))
    
    elements.append(Spacer(1, 20))

    # 8. TABLE 3: GROUP MONTHLY SUMMARY
    elements.append(Paragraph(f"<b>3. Group Financial Summary ({grp_name}s) in {year}</b>", style_bold))
    
    t3_data = [["Month", "Income", "Donation", "Balance"]]
    
    if df_summary_year.empty:
         monthly_stats = pd.DataFrame()
    else:
        monthly_stats = df_summary_year.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
        
    if 'Incoming' not in monthly_stats: monthly_stats['Incoming'] = 0.0
    if 'Outgoing' not in monthly_stats: monthly_stats['Outgoing'] = 0.0
    
    for m_num in range(1, 13):
        inc = monthly_stats.loc[m_num, 'Incoming'] if m_num in monthly_stats.index else 0
        don = monthly_stats.loc[m_num, 'Outgoing'] if m_num in monthly_stats.index else 0
        bal = inc - don
        t3_data.append([
            MONTH_NAMES[m_num-1],
            f"{inc:,.2f}",
            f"{don:,.2f}",
            f"{bal:,.2f}"
        ])

    t3 = Table(t3_data, colWidths=[120, 100, 100, 100], hAlign='LEFT')
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.navy),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 25))

    # 9. CHARTS
    elements.append(Paragraph(f"<b>4. Distribution Analysis ({year})</b>", style_bold))
    elements.append(Spacer(1, 10))

    fund_stats = df_donations_year.groupby("Category")['Amount'].sum()
    img_fund = create_pie_chart_image(fund_stats, "By Fund Source")
    usage_stats = df_donations_year.groupby("SubCategory")['Amount'].sum()
    img_usage = create_pie_chart_image(usage_stats, "By Usage")
    img_med = None
    if not medical_df.empty:
        med_stats = medical_df.groupby("Medical")['Amount'].sum()
        img_med = create_pie_chart_image(med_stats, "Medical Breakdown")

    # Layout: Row 1
    if img_fund and img_usage:
        chart_table_1 = Table([[img_fund, img_usage]], colWidths=[3.5*inch, 3.5*inch])
        chart_table_1.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        elements.append(chart_table_1)
        elements.append(Spacer(1, 15))
    elif img_fund: elements.append(img_fund)
    elif img_usage: elements.append(img_usage)

    # Layout: Row 2
    if img_med:
        chart_table_2 = Table([[img_med]], colWidths=[7*inch])
        chart_table_2.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        elements.append(chart_table_2)
        elements.append(Spacer(1, 25))

    # 10. Footer & Signature
    if footer_msg:
        elements.append(Paragraph(footer_msg, style_normal))
        elements.append(Spacer(1, 30))

    elements.append(Paragraph("_" * 30, style_normal))
    elements.append(Paragraph("Authorized Signature", style_normal))

    doc.build(elements)
    buffer.seek(0)
    return buffer

if 'df' not in st.session_state:
    st.session_state.df = load_data()

if 'members_db' not in st.session_state:
    st.session_state.members_db = load_json_file(MEMBERS_FILE)

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    if st.button("Logout", key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()
    st.divider()
    
    st.markdown("### 🛠️ Admin Tools")
    st.info("Upload .ttf font if using non-English characters.")
    font_file = st.file_uploader("Upload Font", type=['ttf'])
    if font_file:
        with open(FONT_FILE_NAME, "wb") as f:
            f.write(font_file.getbuffer())
        st.session_state.custom_font_path = FONT_FILE_NAME
        st.success("Font Loaded!")

    st.divider()
    st.error("⚠️ Danger Zone")
    csv_backup = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("1️⃣ Download Data First", csv_backup, f"archive_{st.session_state.username}_{datetime.now().strftime('%Y-%m-%d')}.csv", "text/csv")
    
    if st.button("2️⃣ Reset All Data"):
        st.session_state.show_reset_confirm = True
    
    if st.session_state.show_reset_confirm:
        st.warning("Are you sure? This deletes ALL transactions and members!")
        c_yes, c_no = st.columns(2)
        if c_yes.button("YES, Delete"):
            empty_df = pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical", "Amount"])
            save_data(empty_df)
            st.session_state.df = empty_df
            save_json_file(MEMBERS_FILE, {})
            st.session_state.members_db = {}
            st.session_state.show_reset_confirm = False
            st.success("Reset Complete")
            st.rerun()
        if c_no.button("Cancel"):
            st.session_state.show_reset_confirm = False
            st.rerun()

    st.divider()
    with st.expander("🛠️ Restore Data"):
        uploaded = st.file_uploader("Upload CSV", type=['csv'])
        if uploaded:
            st.session_state.df = pd.read_csv(uploaded)
            save_data(st.session_state.df)
            st.success("Restored!")
            st.rerun()

# --- DASHBOARD ---
st.title("Charity Management System")
df = st.session_state.df
curr_yr = int(datetime.now().year)

if not df.empty:
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    tot_inc = df[df['Type'] == 'Incoming']['Amount'].sum()
    yr_inc = df[(df['Type'] == 'Incoming') & (df['Year'] == curr_yr)]['Amount'].sum()
    tot_don = df[df['Type'] == 'Outgoing']['Amount'].sum()
    yr_don = df[(df['Type'] == 'Outgoing') & (df['Year'] == curr_yr)]['Amount'].sum()
else:
    tot_inc = yr_inc = tot_don = yr_don = 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Income", f"{CURRENCY}{tot_inc:,.2f}")
c2.metric(f"Income ({curr_yr})", f"{CURRENCY}{yr_inc:,.2f}")
c3.metric("Total Donation", f"{CURRENCY}{tot_don:,.2f}")
c4.metric(f"Donation ({curr_yr})", f"{CURRENCY}{yr_don:,.2f}")

st.divider()
st.markdown("#### 💰 Fund Balances")
fund_filter = st.radio("Show Balances For:", ["All", "Brother", "Sister"], horizontal=True, key="fund_filter")
fund_cols = st.columns(len(INCOME_TYPES))
for i, fund in enumerate(INCOME_TYPES):
    bal = get_fund_balance(df, fund, fund_filter)
    fund_cols[i].metric(label=fund, value=f"{CURRENCY}{bal:,.2f}")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1. Transaction", "2. Activities Log", "3. Donation List", "4. Analysis", "5. Member Report", "6. Overall Summary"])

# === TAB 1: TRANSACTION ===
with tab1:
    st.subheader("Transaction Management")
    
    with st.expander("➕ Register New Member / View List", expanded=False):
        c_left, c_right = st.columns([1, 1])
        with c_left:
            with st.form("new_member_form", clear_on_submit=True):
                nm_id = st.text_input("Member ID (Optional)")
                nm_name = st.text_input("Full Name *")
                nm_group = st.radio("Group", ["Brother", "Sister"], horizontal=True)
                nm_phone = st.text_input("Phone")
                nm_email = st.text_input("Email *")
                nm_addr = st.text_input("Address")
                if st.form_submit_button("Save Member"):
                    if nm_name and nm_email:
                        mid = nm_id if nm_id else str(uuid.uuid4())[:6]
                        st.session_state.members_db[nm_name] = {"id": mid, "group": nm_group, "phone": nm_phone, "email": nm_email, "address": nm_addr}
                        save_json_file(MEMBERS_FILE, st.session_state.members_db)
                        st.success(f"Member '{nm_name}' registered!")
                        st.rerun()
                    else: st.error("Name and Email required.")
        with c_right:
            st.markdown("##### 📋 Registered Members")
            if st.session_state.members_db:
                mem_data = [{"Name": k, "ID": v.get("id"), "Group": v.get("group"), "Phone": v.get("phone")} for k, v in st.session_state.members_db.items()]
                st.dataframe(pd.DataFrame(mem_data), use_container_width=True, hide_index=True)
            else: st.info("No members registered.")

    st.markdown("---")
    st.write("#### New Entry")
    
    t_type = st.radio("Select Type:", ["Incoming", "Outgoing"], horizontal=True, key="t_select")
    
    # EXTERNAL VARIABLES
    sel_group = "N/A"; sel_category = ""; sel_sub_category = ""; sel_medical = ""; out_grp = "N/A"; current_balance = 0.0
    
    if t_type == "Outgoing":
        st.info("ℹ️ Donation Details:")
        col_grp, col_cat = st.columns(2)
        out_grp = col_grp.radio("Donation Group:", ["Brother", "Sister"], horizontal=True, key="out_grp")
        sel_category = col_cat.selectbox("Select Fund Source", INCOME_TYPES, key="out_cat")
        current_balance = get_fund_balance(df, sel_category)
        if current_balance > 0: col_cat.success(f"Available: {CURRENCY}{current_balance:,.2f}")
        else: col_cat.error(f"Low Balance: {CURRENCY}{current_balance:,.2f}")
        
        sel_sub_category = st.selectbox("Donation Usage", OUTGOING_TYPES, key="out_sub")
        if sel_sub_category == "Medical help":
            med_choice = st.selectbox("Medical Condition", MEDICAL_SUB_TYPES, key="out_med")
            sel_medical = st.text_input("Specify", key="out_med_txt") if med_choice == "Other" else med_choice
    
    with st.form("txn_form", clear_on_submit=True):
        c_date, c_amt = st.columns(2)
        date_val = c_date.date_input("Date", datetime.today())
        amount = c_amt.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=5.0)
        
        member_name, address, reason, responsible = "", "", "", ""
        category, sub_category, medical, group = "", "", "", ""
        
        if t_type == "Incoming":
            st.write("#### 📥 Income Details")
            c1, c2 = st.columns(2)
            group_sel = c1.radio("Group Filter", ["Brother", "Sister"], horizontal=True)
            valid_mems = [n for n, d in st.session_state.members_db.items() if d.get('group') == group_sel]
            valid_mems.sort()
            member_name = c2.selectbox("Select Member", valid_mems) if valid_mems else c2.text_input("Member Name")
            category = st.selectbox("Category", INCOME_TYPES)
            group = group_sel
            sub_category = ""
            medical = ""
        else:
            st.write("#### 📤 Beneficiary & Responsible")
            c1, c2 = st.columns(2)
            member_name = c1.text_input("Beneficiary Name")
            address = c2.text_input("Address")
            c3, c4 = st.columns(2)
            reason = c3.text_input("Reason")
            all_mems = sorted(list(st.session_state.members_db.keys()))
            responsible = c4.selectbox("Responsible Person", ["Select..."] + all_mems)
            category, sub_category, medical, group = sel_category, sel_sub_category, sel_medical, out_grp
        
        if st.form_submit_button("💾 Save Transaction", type="primary"):
            if t_type == "Outgoing" and amount > current_balance:
                st.error(f"Insufficient funds in {category}!")
            elif amount > 0 and member_name:
                new_row = {
                    "ID": str(uuid.uuid4()), "Date": str(date_val), 
                    "Year": int(date_val.year), "Month": int(date_val.month),
                    "Type": t_type, "Group": group, "Name_Details": member_name, 
                    "Address": address, "Reason": reason, "Responsible": responsible,
                    "Category": category, "SubCategory": sub_category, "Medical": medical, "Amount": amount
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("Saved!")
                st.rerun()
            else: st.error("Name and Amount required")

# === TAB 2: LOG ===
with tab2:
    st.subheader("Activities Log")
    f1, f2, f3, f4 = st.columns(4)
    f_yr = f1.selectbox("Filter Year", ["All"] + sorted(list(set(df['Year'].astype(str)))) if not df.empty else ["All"])
    f_tp = f2.selectbox("Filter Type", ["All", "Incoming", "Outgoing"])
    f_gr = f3.selectbox("Filter Group", ["All", "Brother", "Sister"])
    
    view = df.copy()
    if f_yr != "All": view = view[view['Year'] == int(f_yr)]
    if f_tp != "All": view = view[view['Type'] == f_tp]
    if f_gr != "All": view = view[view['Group'] == f_gr]
    
    def get_mem_id(name):
        return st.session_state.members_db.get(name, {}).get("id", "N/A")
    view['Member ID'] = view['Name_Details'].apply(get_mem_id)
    
    st.dataframe(view[["Member ID", "Name_Details", "Type", "Group", "Category", "SubCategory", "Amount"]], use_container_width=True)
    
    st.markdown("### ✏️ Edit / Delete Transaction")
    if not view.empty:
        view['Label'] = view.apply(lambda x: f"{x['Date']} | {x['Name_Details']} | {CURRENCY}{x['Amount']}", axis=1)
        txn_map = dict(zip(view['Label'], view['ID']))
        selected_label = st.selectbox("Select Transaction:", ["None"] + list(txn_map.keys()))
        
        if selected_label != "None":
            sel_id = txn_map[selected_label]
            row = df[df['ID'] == sel_id].iloc[0]
            st.info(f"Editing: {selected_label}")
            with st.form("edit_txn_form"):
                e_date = st.date_input("Date", datetime.strptime(row['Date'], "%Y-%m-%d"))
                e_amt = st.number_input("Amount", value=float(row['Amount']))
                
                if row['Type'] == "Incoming":
                    e_cat = st.selectbox("Category", INCOME_TYPES, index=INCOME_TYPES.index(row['Category']) if row['Category'] in INCOME_TYPES else 0)
                    e_sub = ""; e_med = ""
                else:
                    e_cat = st.selectbox("Fund Source", INCOME_TYPES, index=INCOME_TYPES.index(row['Category']) if row['Category'] in INCOME_TYPES else 0)
                    e_sub = st.selectbox("Usage", OUTGOING_TYPES, index=OUTGOING_TYPES.index(row['SubCategory']) if row['SubCategory'] in OUTGOING_TYPES else 0)
                    e_med = st.text_input("Medical Details", value=row['Medical'])
                
                col_up, col_del = st.columns(2)
                if col_up.form_submit_button("✅ Update"):
                    idx = st.session_state.df[st.session_state.df['ID'] == sel_id].index[0]
                    st.session_state.df.at[idx, 'Date'] = str(e_date)
                    st.session_state.df.at[idx, 'Year'] = int(e_date.year)
                    st.session_state.df.at[idx, 'Month'] = int(e_date.month)
                    st.session_state.df.at[idx, 'Amount'] = e_amt
                    st.session_state.df.at[idx, 'Category'] = e_cat
                    st.session_state.df.at[idx, 'SubCategory'] = e_sub
                    st.session_state.df.at[idx, 'Medical'] = e_med
                    save_data(st.session_state.df)
                    st.success("Updated!"); st.rerun()
                if col_del.form_submit_button("❌ Delete"):
                    st.session_state.df = st.session_state.df[st.session_state.df['ID'] != sel_id]
                    save_data(st.session_state.df)
                    st.warning("Deleted!"); st.rerun()

# === TAB 3: DONATION LIST ===
with tab3:
    st.subheader("Donation List (Outgoing)")
    d_yr = st.selectbox("Year", ["All"] + sorted(list(set(df['Year'].astype(str)))) if not df.empty else ["All"], key="don_yr")
    d_grp = st.selectbox("Filter Group", ["All", "Brother", "Sister"], key="don_grp")
    don_df = df[df['Type'] == 'Outgoing'].copy()
    if d_yr != "All": don_df = don_df[don_df['Year'] == int(d_yr)]
    if d_grp != "All": don_df = don_df[don_df['Group'] == d_grp]
    if not don_df.empty:
        st.dataframe(don_df[["Date", "Name_Details", "Address", "Reason", "Responsible", "Amount"]], use_container_width=True)
        st.success(f"**Total Donations: {CURRENCY}{don_df['Amount'].sum():,.2f}**")
    else: st.info("No donations found.")

# === TAB 4: ANALYSIS ===
with tab4:
    st.subheader("Analysis")
    c1, c2, c3 = st.columns(3)
    a_grp = c1.selectbox("Group", ["All", "Brother", "Sister"], key="an_grp")
    a_yr = c2.selectbox("Year", ["All"] + sorted(list(set(df['Year'].astype(str)))) if not df.empty else ["All"], key="an_yr")
    
    an_df = df.copy()
    if a_grp != "All": an_df = an_df[an_df['Group'] == a_grp]
    if a_yr != "All": an_df = an_df[an_df['Year'] == int(a_yr)]
    
    if not an_df.empty:
        st.markdown("##### 📅 Month-wise Income vs Outgoing")
        month_agg = an_df.groupby(['Month', 'Type'])['Amount'].sum().reset_index().sort_values('Month')
        month_agg['Month Name'] = month_agg['Month'].apply(lambda x: MONTH_NAMES[int(x)-1])
        fig_bar = px.bar(month_agg, x='Month Name', y='Amount', color='Type', barmode='group')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("---")
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            st.write("**📥 Incoming Categories**")
            idf = an_df[an_df['Type']=='Incoming']
            if not idf.empty: st.plotly_chart(px.pie(idf, values='Amount', names='Category'), use_container_width=True)
            else: st.caption("No data")
        with c_p2:
            st.write("**📤 Outgoing Usage**")
            odf = an_df[an_df['Type']=='Outgoing']
            if not odf.empty: st.plotly_chart(px.pie(odf, values='Amount', names='SubCategory'), use_container_width=True)
            else: st.caption("No data")
        with c_p3:
            st.write("**🏥 Medical Breakdown**")
            mdf = an_df[(an_df['Type']=='Outgoing') & (an_df['SubCategory']=='Medical help')]
            if not mdf.empty: st.plotly_chart(px.pie(mdf, values='Amount', names='Medical'), use_container_width=True)
            else: st.caption("No medical data")
        
        st.markdown("### 📋 Filtered Data Table")
        st.dataframe(an_df[["Date", "Name_Details", "Type", "Category", "Amount"]], use_container_width=True)
    else: st.info("No data.")

# === TAB 5: MEMBER REPORT ===
with tab5:
    st.subheader("Member Report")
    c1, c2, c3 = st.columns(3)
    mat_grp = c1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mg")
    reg_mems = [n for n, d in st.session_state.members_db.items() if (mat_grp == "All" or d.get('group') == mat_grp)]
    trans_mems = df[df['Type'] == 'Incoming']
    if mat_grp != "All": trans_mems = trans_mems[trans_mems['Group'] == mat_grp]
    all_visible_mems = sorted(list(set(reg_mems + trans_mems['Name_Details'].unique().tolist())))
    
    if all_visible_mems:
        target = c2.selectbox("Select Member", all_visible_mems)
        tyear = c3.selectbox("Select Year", ["All"] + sorted(list(set(df['Year'].astype(str)))))
        
        mem_info = st.session_state.members_db.get(target, {})
        all_time_df = df[(df['Name_Details'] == target) & (df['Type'] == 'Incoming')]
        lifetime_total = all_time_df['Amount'].sum()
        mem_since = all_time_df['Date'].min() if not all_time_df.empty else "N/A"
        
        st.markdown(f"## 👤 {target}")
        i1, i2, i3 = st.columns(3)
        i1.info(f"**Member Since:** {mem_since}")
        i2.success(f"**Lifetime Total:** {CURRENCY}{lifetime_total:,.2f}")
        
        with st.container():
            st.markdown(f"**Details:** {mem_info.get('address', '-')} | {mem_info.get('phone', '-')} | {mem_info.get('email', '-')}")

        st.divider()
        with st.expander("PDF Options"):
            h = st.text_area("Header", "We appreciate your generous contributions.")
            f = st.text_area("Footer", "Please contact admin for discrepancies.")

        if tyear == "All":
            year_df = all_time_df
            year_filter = None
            
            # FIXED LOGIC for PDF
            group_filter = mem_info.get('group', 'All') 
            if group_filter == 'All' and mat_grp != 'All': group_filter = mat_grp
            
            if group_filter == 'All':
                 global_out_year = df[df['Type'] == 'Outgoing']
            else:
                 global_out_year = df[(df['Type'] == 'Outgoing') & (df['Group'] == group_filter)]
            
            summary_source_df = df
            if group_filter != 'All': summary_source_df = df[df['Group'] == group_filter]
                 
            medical_df_year = global_out_year[global_out_year['SubCategory'] == 'Medical help']
        else:
            year_filter = int(tyear)
            year_df = all_time_df[all_time_df['Year'] == year_filter]
            
            group_filter = mem_info.get('group', 'All')
            if group_filter == 'All' and mat_grp != 'All': group_filter = mat_grp
            
            if group_filter == 'All':
                global_out_year = df[(df['Type'] == 'Outgoing') & (df['Year'] == year_filter)]
                summary_source_df = df[df['Year'] == year_filter]
            else:
                global_out_year = df[(df['Type'] == 'Outgoing') & (df['Year'] == year_filter) & (df['Group'] == group_filter)]
                summary_source_df = df[(df['Year'] == year_filter) & (df['Group'] == group_filter)]
                
            medical_df_year = global_out_year[global_out_year['SubCategory'] == 'Medical help']

        if not year_df.empty:
            st.markdown(f"#### 📅 Contributions in {tyear}")
            st.dataframe(year_df[["Date", "Category", "Amount"]], use_container_width=True)
            year_total = year_df['Amount'].sum()
            st.success(f"**Total for {tyear}: {CURRENCY}{year_total:,.2f}**")
            
            if HAS_PDF:
                font_path = st.session_state.get('custom_font_path', None)
                pdf = generate_pdf(target, mem_info, tyear, mem_since, lifetime_total, 
                                   year_df, global_out_year, summary_source_df, medical_df_year, h, f, font_path)
                st.download_button("📄 Download Official PDF Report", pdf, f"{target}_Report_{tyear}.pdf", "application/pdf", type="primary")
        else: st.info(f"No contributions found for {tyear}.")
    else: st.info("No members found.")

# === TAB 6: OVERALL SUMMARY ===
with tab6:
    st.subheader("Overall Monthly Summary")
    sum_year = st.selectbox("Select Year for Summary", sorted(list(set(df['Year'].astype(str)))))
    if sum_year:
        year_df = df[df['Year'] == int(sum_year)]
        
        def render_summary(dframe):
            if dframe.empty: return
            monthly_stats = dframe.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
            if 'Incoming' not in monthly_stats: monthly_stats['Incoming'] = 0.0
            if 'Outgoing' not in monthly_stats: monthly_stats['Outgoing'] = 0.0
            
            summary_table = []
            t_in, t_out, t_bal = 0, 0, 0
            for m_num in range(1, 13):
                inc = monthly_stats.loc[m_num, 'Incoming'] if m_num in monthly_stats.index else 0
                don = monthly_stats.loc[m_num, 'Outgoing'] if m_num in monthly_stats.index else 0
                bal = inc - don
                summary_table.append({"Month": MONTH_NAMES[m_num-1], "Income": inc, "Donation": don, "Balance": bal})
                t_in += inc; t_out += don; t_bal += bal
                
            st.dataframe(pd.DataFrame(summary_table).style.format({"Income": "€{:.2f}", "Donation": "€{:.2f}", "Balance": "€{:.2f}"}), use_container_width=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Year Income", f"€{t_in:,.2f}"); c2.metric("Year Donation", f"€{t_out:,.2f}"); c3.metric("Net Balance", f"€{t_bal:,.2f}")

        t_all, t_bro, t_sis = st.tabs(["All", "Brothers", "Sisters"])
        with t_all: render_summary(year_df)
        with t_bro: render_summary(year_df[(year_df['Group'] == 'Brother') | (year_df['Type'] == 'Outgoing')])
        with t_sis: render_summary(year_df[(year_df['Group'] == 'Sister') | (year_df['Type'] == 'Outgoing')])
