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

# --- REPORTLAB IMPORTS (For PDF) ---
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Charity Management System", layout="wide", page_icon="💚")

USER_FILE = "users.json"
MEMBERS_FILE = "members.json"
CURRENCY = "€"

INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

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

def get_fund_balance(df, fund_category):
    if df.empty: return 0.0
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    income = df[(df['Type'] == 'Incoming') & (df['Category'] == fund_category)]['Amount'].sum()
    expense = df[(df['Type'] == 'Outgoing') & (df['Category'] == fund_category)]['Amount'].sum()
    return income - expense

# --- HELPER: Create Pie Chart Image for PDF ---
def create_pie_chart_image(data_series, title):
    if data_series.empty: return None
    
    # Create Matplotlib Figure
    plt.figure(figsize=(5, 4))
    # Use a nice color map
    wedges, texts, autotexts = plt.pie(
        data_series, 
        labels=data_series.index, 
        autopct='%1.1f%%', 
        startangle=140, 
        textprops={'fontsize': 9},
        colors=plt.cm.Pastel1.colors
    )
    plt.title(title, fontsize=12, fontweight='bold')
    
    # Save to Buffer
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300) # High Resolution
    img_buf.seek(0)
    plt.close()
    
    return Image(img_buf, width=4*inch, height=3*inch, hAlign='CENTER')

# --- ADVANCED PDF GENERATOR ---
def generate_pdf(member_name, member_details, year, member_since, lifetime_total, 
                 df_member_year, df_global_year, medical_df, header_msg, footer_msg):
    
    if not HAS_PDF: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    styles.add(ParagraphStyle(name='Highlight', parent=styles['Normal'], fontSize=12, textColor=colors.darkblue, spaceAfter=12))

    # 1. Title
    elements.append(Paragraph(f"Member Contribution Report", styles['Title']))
    elements.append(Spacer(1, 10))

    # 2. Member Profile
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
    # Highlight Total
    elements.append(Paragraph(f"<b>LIFETIME CONTRIBUTIONS: {CURRENCY}{lifetime_total:,.2f}</b>", styles['Highlight']))
    elements.append(Spacer(1, 15))
    
    # 3. Appreciation Box
    if header_msg:
        elements.append(Paragraph(f"<i>{header_msg}</i>", styles['Italic']))
        elements.append(Spacer(1, 15))

    # 4. Table 1: Member's Monthly Contributions
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
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 20))

    # 5. Table 2: Charity Overall Spending
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
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 25))

    # 6. Charts Section
    elements.append(Paragraph(f"<b>3. Distribution Analysis ({year})</b>", styles['Heading3']))
    
    # Chart 1: By Fund Source (Category)
    fund_stats = df_global_year.groupby("Category")['Amount'].sum()
    img1 = create_pie_chart_image(fund_stats, "Distribution by Fund Source")
    if img1: elements.append(img1)
    
    elements.append(Spacer(1, 15))

    # Chart 2: By Usage (SubCategory)
    usage_stats = df_global_year.groupby("SubCategory")['Amount'].sum()
    img2 = create_pie_chart_image(usage_stats, "Distribution by Usage")
    if img2: elements.append(img2)
    
    elements.append(Spacer(1, 15))

    # Chart 3: Medical Breakdown
    if not medical_df.empty:
        med_stats = medical_df.groupby("Medical")['Amount'].sum()
        img3 = create_pie_chart_image(med_stats, "Medical Breakdown")
        if img3: elements.append(img3)

    elements.append(Spacer(1, 25))

    # 7. Footer & Signature
    if footer_msg:
        elements.append(Paragraph(footer_msg, styles['Normal']))
        elements.append(Spacer(1, 30))

    elements.append(Paragraph("_" * 30, styles['Normal']))
    elements.append(Paragraph("Authorized Signature", styles['Normal']))

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
    
    st.error("⚠️ Danger Zone")
    csv_backup = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("1️⃣ Download Data First", csv_backup, f"archive_{st.session_state.username}_{datetime.now().strftime('%Y-%m-%d')}.csv", "text/csv")
    
    if st.button("2️⃣ Reset All Transactions"):
        st.session_state.show_reset_confirm = True
    
    if st.session_state.show_reset_confirm:
        st.warning("Are you sure? This deletes all transactions!")
        c_yes, c_no = st.columns(2)
        if c_yes.button("YES, Delete"):
            empty_df = pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical", "Amount"])
            save_data(empty_df)
            st.session_state.df = empty_df
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
fund_cols = st.columns(len(INCOME_TYPES))
for i, fund in enumerate(INCOME_TYPES):
    bal = get_fund_balance(df, fund)
    fund_cols[i].metric(label=fund, value=f"{CURRENCY}{bal:,.2f}")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Transaction", "2. Activities Log", "3. Analysis", "4. Member Report", "5. Overall Summary"])

# === TAB 1: TRANSACTION ===
with tab1:
    st.subheader("Transaction Management")
    
    with st.expander("➕ Register New Member", expanded=False):
        with st.form("new_member_form"):
            nm_name = st.text_input("Member Name (Full Name)")
            nm_group = st.radio("Group", ["Brother", "Sister"], horizontal=True)
            c1, c2, c3 = st.columns(3)
            nm_phone = c1.text_input("Phone")
            nm_email = c2.text_input("Email")
            nm_addr = c3.text_input("Address")
            if st.form_submit_button("Save New Member"):
                if nm_name:
                    st.session_state.members_db[nm_name] = {"group": nm_group, "phone": nm_phone, "email": nm_email, "address": nm_addr}
                    save_json_file(MEMBERS_FILE, st.session_state.members_db)
                    st.success(f"Member '{nm_name}' registered!")
                    st.rerun()
                else: st.error("Name required.")

    st.markdown("---")
    st.write("#### New Entry")
    
    t_type = st.radio("Select Type:", ["Incoming", "Outgoing"], horizontal=True, key="t_select")
    
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
            reason = c3.text_input("Reason / Note")
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
    
    cols = ["Date", "Type", "Name_Details", "Category", "SubCategory", "Medical", "Address", "Amount"]
    edited = st.data_editor(view[cols], column_config={"Amount": st.column_config.NumberColumn(format="€%.2f")}, use_container_width=True, num_rows="dynamic", key="log_edit")
    
    if st.button("Save Edits"):
        if f_yr == "All" and f_tp == "All" and f_gr == "All":
            st.session_state.df.update(edited)
            save_data(st.session_state.df)
            st.success("Updated!")
            st.rerun()
        else: st.warning("Reset filters to 'All' to save edits.")

# === TAB 3: ANALYSIS ===
with tab3:
    st.subheader("Analysis")
    if not df.empty:
        st.markdown("### 📥 Income Analysis")
        c1, c2 = st.columns(2)
        grp = c1.selectbox("Group", ["All", "Brother", "Sister"], key="a")
        cat = c2.selectbox("Category", ["All"] + INCOME_TYPES)
        
        adf = df[df['Type'] == 'Incoming']
        if grp != "All": adf = adf[adf['Group'] == grp]
        if cat != "All": adf = adf[adf['Category'] == cat]
        
        if not adf.empty:
            # --- CHANGED: TABLE INSTEAD OF CHART ---
            st.dataframe(adf[["Date", "Name_Details", "Group", "Category", "Amount"]], use_container_width=True)
            stats = adf.groupby("Name_Details")['Amount'].sum().reset_index().sort_values("Amount", ascending=False)
            st.success(f"Total: {CURRENCY}{stats['Amount'].sum():,.2f}")
        else: st.info("No income data.")
        
        st.divider()
        st.markdown("### 📤 Donation Analysis")
        out_df = df[df['Type'] == 'Outgoing']
        if not out_df.empty:
            col_fund, col_use = st.columns(2)
            with col_fund:
                st.write("**By Fund Source**")
                fig_fund = px.pie(out_df, values='Amount', names='Category')
                st.plotly_chart(fig_fund, use_container_width=True)
            with col_use:
                st.write("**By Usage**")
                fig_use = px.pie(out_df, values='Amount', names='SubCategory')
                st.plotly_chart(fig_use, use_container_width=True)
            
            st.write("**Medical Breakdown**")
            med_df = out_df[out_df['SubCategory'] == 'Medical help']
            if not med_df.empty:
                fig_med = px.pie(med_df, values='Amount', names='Medical')
                st.plotly_chart(fig_med, use_container_width=True)
            else: st.info("No Medical data")
        else: st.info("No donations.")

# === TAB 4: MEMBER REPORT ===
with tab4:
    st.subheader("Member Report")
    c1, c2, c3 = st.columns(3)
    mat_grp = c1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mg")
    reg_mems = [name for name, d in st.session_state.members_db.items() if (mat_grp == "All" or d.get('group') == mat_grp)]
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
            st.markdown(f"**Details:** {mem_info.get('address', '-')} | {mem_info.get('phone', '-')}")

        st.divider()
        with st.expander("PDF Options"):
            h = st.text_area("Header", "We appreciate your generous contributions.")
            f = st.text_area("Footer", "Please contact admin for discrepancies.")

        if tyear == "All":
            year_df = all_time_df
            year_filter = None
            global_out_year = df[df['Type'] == 'Outgoing']
            medical_df_year = global_out_year[global_out_year['SubCategory'] == 'Medical help']
        else:
            year_filter = int(tyear)
            year_df = all_time_df[all_time_df['Year'] == year_filter]
            global_out_year = df[(df['Type'] == 'Outgoing') & (df['Year'] == year_filter)]
            medical_df_year = global_out_year[global_out_year['SubCategory'] == 'Medical help']

        if not year_df.empty:
            st.markdown(f"#### 📅 Contributions in {tyear}")
            st.dataframe(year_df[["Date", "Category", "Amount"]], use_container_width=True)
            year_total = year_df['Amount'].sum()
            st.success(f"**Total for {tyear}: {CURRENCY}{year_total:,.2f}**")
            
            if HAS_PDF:
                pdf = generate_pdf(target, mem_info, tyear, mem_since, lifetime_total, 
                                   year_df, global_out_year, medical_df_year, h, f)
                st.download_button("📄 Download Official PDF Report", pdf, f"{target}_Report_{tyear}.pdf", "application/pdf")
        else: st.info(f"No contributions found for {tyear}.")
    else: st.info("No members found.")

# === TAB 5: OVERALL SUMMARY ===
with tab5:
    st.subheader("Overall Monthly Summary")
    sum_year = st.selectbox("Select Year for Summary", sorted(list(set(df['Year'].astype(str)))))
    
    if sum_year:
        year_df = df[df['Year'] == int(sum_year)]
        monthly_stats = year_df.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
        
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
            
        sum_df = pd.DataFrame(summary_table)
        st.dataframe(sum_df.style.format({"Income": "€{:.2f}", "Donation": "€{:.2f}", "Balance": "€{:.2f}"}), use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Year Income", f"€{t_in:,.2f}")
        c2.metric("Year Donation", f"€{t_out:,.2f}")
        c3.metric("Net Balance", f"€{t_bal:,.2f}")
        
