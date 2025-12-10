import streamlit as st
import pandas as pd
import os
import uuid
import io
import hashlib
import json
from datetime import datetime
import plotly.express as px

# --- REPORTLAB IMPORTS (For PDF) ---
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Charity Management System", layout="wide", page_icon="💚")

USER_FILE = "users.json"
MEMBERS_FILE = "members.json" # New file for member details
CURRENCY = "€"

INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]

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
    # Default Admin
    if "admin" not in users: users["admin"] = hash_password("admin")
    
    if username in users and users[username] == hash_password(password): return True
    return False

# --- 3. SESSION INIT ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'username' not in st.session_state: st.session_state.username = ""

# =========================================================
# LOGIN SCREEN
# =========================================================
if not st.session_state.authenticated:
    st.title("🔒 Charity System Login")
    
    with st.sidebar:
        st.header("⚙️ Admin Tools")
        # Backup Users
        if os.path.exists(USER_FILE):
            with open(USER_FILE, "r") as f:
                st.download_button("💾 Backup Logins", f, "users_backup.json", "application/json")
        # Restore Users
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

# --- PDF GENERATOR (UPDATED) ---
def generate_pdf(member_name, member_details, year, dataframe, header_msg, footer_msg, grand_total):
    if not HAS_PDF: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph(f"Contribution Report", styles['Title']))
    elements.append(Spacer(1, 10))
    
    # Member Details Block
    elements.append(Paragraph(f"<b>Member Name:</b> {member_name}", styles['Normal']))
    elements.append(Paragraph(f"<b>Group:</b> {member_details.get('group', '-')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Address:</b> {member_details.get('address', '-')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Phone:</b> {member_details.get('phone', '-')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Email:</b> {member_details.get('email', '-')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Report Year:</b> {year}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Header Message
    if header_msg:
        elements.append(Paragraph(header_msg, styles['Italic']))
        elements.append(Spacer(1, 12))
    
    # Table Data
    df_reset = dataframe.reset_index()
    data = [df_reset.columns.to_list()] + df_reset.values.tolist()
    clean_data = []
    for row in data:
        clean_row = []
        for item in row:
            if isinstance(item, (float, int)): clean_row.append(f"{item:,.2f}")
            else: clean_row.append(str(item))
        clean_data.append(clean_row)
    clean_data.append([""] * (len(clean_data[0]) - 2) + ["GRAND TOTAL:", f"{grand_total:,.2f}"])
    
    # Table Styling
    t = Table(clean_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkgreen),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    
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

# Load Data
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# Load Members
if 'members_db' not in st.session_state:
    st.session_state.members_db = load_json_file(MEMBERS_FILE)

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    st.divider()
    
    # Backup Transactions
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Backup Transactions", csv, f"trans_{st.session_state.username}.csv", "text/csv")
    
    # Backup Members
    mem_json = json.dumps(st.session_state.members_db)
    st.download_button("💾 Backup Members Info", mem_json, "members.json", "application/json")
    
    st.markdown("---")
    
    # Restore
    up_trans = st.file_uploader("Restore Transactions", type=['csv'])
    if up_trans:
        st.session_state.df = pd.read_csv(up_trans)
        save_data(st.session_state.df)
        st.success("Transactions Restored!")
        
    up_mems = st.file_uploader("Restore Members Info", type=['json'])
    if up_mems:
        st.session_state.members_db = json.load(up_mems)
        save_json_file(MEMBERS_FILE, st.session_state.members_db)
        st.success("Members Restored!")

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
c2.metric(f"Income {curr_yr}", f"{CURRENCY}{yr_inc:,.2f}")
c3.metric("Total Donation", f"{CURRENCY}{tot_don:,.2f}")
c4.metric(f"Donation {curr_yr}", f"{CURRENCY}{yr_don:,.2f}")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Transaction", "2. Activities Log", "3. Analysis", "4. Member Report"])

# === TAB 1: TRANSACTION ===
with tab1:
    st.subheader("Transaction Management")
    
    # --- REGISTER NEW MEMBER SECTION ---
    with st.expander("➕ Register New Member", expanded=False):
        with st.form("new_member_form"):
            nm_name = st.text_input("Member Name (Full Name)")
            nm_group = st.radio("Group", ["Brother", "Sister"], horizontal=True)
            c1, c2, c3 = st.columns(3)
            nm_phone = c1.text_input("Phone Number")
            nm_email = c2.text_input("Email")
            nm_addr = c3.text_input("Address")
            
            if st.form_submit_button("Save New Member"):
                if nm_name:
                    st.session_state.members_db[nm_name] = {
                        "group": nm_group,
                        "phone": nm_phone,
                        "email": nm_email,
                        "address": nm_addr
                    }
                    save_json_file(MEMBERS_FILE, st.session_state.members_db)
                    st.success(f"Member '{nm_name}' registered successfully!")
                    st.rerun()
                else:
                    st.error("Name is required.")

    st.markdown("---")
    
    # --- TRANSACTION ENTRY ---
    st.write("#### New Entry")
    t_type = st.radio("Select Type:", ["Incoming", "Outgoing"], horizontal=True, key="t_select")
    
    # External Variables
    category_selection = ""
    sub_cat_selection = ""
    medical_selection = ""
    
    # Outgoing Pre-Selection
    if t_type == "Outgoing":
        st.info("ℹ️ Donation Details:")
        col_grp, col_cat = st.columns(2)
        out_group = col_grp.radio("Donation Group:", ["Brother", "Sister"], horizontal=True, key="out_grp")
        
        category_selection = col_cat.selectbox("Donation Category", INCOME_TYPES, key="out_cat")
        
        if category_selection == "Sadaka":
            sub_cat_selection = st.selectbox("Sadaka Type", ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"], key="out_sub")
            if sub_cat_selection == "Medical help":
                med_choice = st.selectbox("Medical Condition", MEDICAL_SUB_TYPES, key="out_med")
                if med_choice == "Other":
                    medical_selection = st.text_input("Specify Condition", key="out_med_txt")
                else:
                    medical_selection = med_choice
    
    with st.form("txn_form", clear_on_submit=True):
        c_date, c_amt = st.columns(2)
        date_val = c_date.date_input("Date", datetime.today())
        amount = c_amt.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=5.0)
        
        # Internal Vars
        member_name = ""
        group = "N/A"
        category = ""
        sub_category = ""
        medical = ""
        address, reason, responsible = "", "", ""
        
        if t_type == "Incoming":
            st.write("#### 📥 Income Details")
            c1, c2 = st.columns(2)
            
            # Select Group to filter names
            group_sel = c1.radio("Group Filter", ["Brother", "Sister"], horizontal=True)
            
            # Get members from DB matching group
            valid_members = [name for name, details in st.session_state.members_db.items() if details.get('group') == group_sel]
            valid_members.sort()
            
            member_name = c2.selectbox("Select Member", valid_members) if valid_members else c2.text_input("Member Name (Not registered)")
            
            category = st.selectbox("Category", INCOME_TYPES)
            group = group_sel
            
        else: # Outgoing
            st.write("#### 📤 Beneficiary & Responsible")
            col_a, col_b = st.columns(2)
            member_name = col_a.text_input("Beneficiary Name")
            address = col_b.text_input("Address / Location")
            
            col_c, col_d = st.columns(2)
            reason = col_c.text_input("Reason / Note")
            
            # Responsible Person (From Member DB)
            all_mems = sorted(list(st.session_state.members_db.keys()))
            responsible = col_d.selectbox("Responsible Person", ["Select..."] + all_mems)
            
            # Map external
            category = category_selection
            sub_category = sub_cat_selection
            medical = medical_selection
            group = out_group # From outside radio
        
        if st.form_submit_button("💾 Save Transaction", type="primary"):
            if amount > 0 and member_name:
                new_row = {
                    "ID": str(uuid.uuid4()), 
                    "Date": str(date_val), 
                    "Year": int(date_val.year), 
                    "Month": int(date_val.month),
                    "Type": t_type, 
                    "Group": group, 
                    "Name_Details": member_name, 
                    "Address": address, 
                    "Reason": reason, 
                    "Responsible": responsible,
                    "Category": category, 
                    "SubCategory": sub_category,
                    "Medical": medical, 
                    "Amount": amount
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("Saved Successfully!")
                st.rerun()
            else:
                st.error("Name and Amount required.")

    # Recent Transactions
    if not df.empty:
        st.caption("Recent Transactions")
        recent_df = df.tail(5).iloc[::-1].copy()
        
        def get_details(row):
            if row['Type'] == 'Incoming': return f"{row['Category']}"
            else:
                base = f"{row['Category']}"
                if row['SubCategory']: base += f" > {row['SubCategory']}"
                if row['Medical']: base += f" ({row['Medical']})"
                return base

        recent_df['Info'] = recent_df.apply(get_details, axis=1)
        st.dataframe(recent_df[["Date", "Type", "Info", "Name_Details", "Responsible", "Amount"]], hide_index=True, use_container_width=True)

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
    
    cols = ["Date", "Type", "Name_Details", "Category", "SubCategory", "Medical", "Address", "Reason", "Responsible", "Amount"]
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
    ac1, ac2 = st.columns(2)
    grp = ac1.selectbox("Group", ["All", "Brother", "Sister"], key="a")
    cat = ac2.selectbox("Category", ["All"] + INCOME_TYPES)
    
    if not df.empty:
        adf = df[df['Type'] == 'Incoming']
        if grp != "All": adf = adf[adf['Group'] == grp]
        if cat != "All": adf = adf[adf['Category'] == cat]
        
        if not adf.empty:
            stats = adf.groupby("Name_Details")['Amount'].sum().reset_index().sort_values("Amount", ascending=False)
            c1, c2 = st.columns([2,1])
            with c1:
                fig = px.bar(stats, x="Name_Details", y="Amount", text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.dataframe(stats, hide_index=True, use_container_width=True)
                st.success(f"Total: {CURRENCY}{stats['Amount'].sum():,.2f}")
        else: st.warning("No data found.")

# === TAB 4: MEMBER REPORT ===
with tab4:
    st.subheader("Member Report")
    
    c1, c2, c3 = st.columns(3)
    mat_grp = c1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mg")
    
    # Filter members based on registered DB + Existing Transactions
    reg_mems = [name for name, d in st.session_state.members_db.items() if (mat_grp == "All" or d.get('group') == mat_grp)]
    trans_mems = df[df['Type'] == 'Incoming']
    if mat_grp != "All": trans_mems = trans_mems[trans_mems['Group'] == mat_grp]
    
    # Merge and sort
    all_visible_mems = sorted(list(set(reg_mems + trans_mems['Name_Details'].unique().tolist())))
    
    if all_visible_mems:
        target = c2.selectbox("Select Member", all_visible_mems)
        tyear = c3.selectbox("Select Year", ["All"] + sorted(list(set(df['Year'].astype(str)))))
        
        # Display Member Details
        mem_info = st.session_state.members_db.get(target, {})
        with st.container():
            st.markdown(f"### 📋 {target}")
            mc1, mc2, mc3 = st.columns(3)
            mc1.markdown(f"**📞 Phone:** {mem_info.get('phone', 'N/A')}")
            mc2.markdown(f"**📧 Email:** {mem_info.get('email', 'N/A')}")
            mc3.markdown(f"**🏠 Address:** {mem_info.get('address', 'N/A')}")
            st.divider()

        # Custom Messages
        with st.expander("📝 Report Messages"):
            h = st.text_area("Header", "We appreciate your generous contributions.")
            f = st.text_area("Footer", "Please contact admin for discrepancies.")
        
        # Data Matrix
        mdf = df[(df['Name_Details'] == target) & (df['Type'] == 'Incoming')]
        if tyear != "All": mdf = mdf[mdf['Year'] == int(tyear)]
        
        if not mdf.empty:
            piv = mdf.pivot_table(index="Date", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
            piv['Daily Total'] = piv.sum(axis=1)
            g_tot = piv['Daily Total'].sum()
            st.dataframe(piv, use_container_width=True)
            st.success(f"Grand Total: {CURRENCY}{g_tot:,.2f}")
            
            if HAS_PDF:
                pdf = generate_pdf(target, mem_info, tyear, piv, h, f, g_tot)
                st.download_button("📄 Download Official PDF Report", pdf, f"{target}_Report.pdf", "application/pdf")
        else: st.info("No transaction records found for this period.")
    else: st.info("No members found.")
