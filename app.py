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

CURRENCY = "€"
YEAR_LIST = [str(y) for y in range(2023, 2101)]
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]

INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]

# --- 2. AUTHENTICATION LOGIC ---

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Load users into Session State to keep them alive during the session
if 'user_db' not in st.session_state:
    # Default Admin
    st.session_state.user_db = {"admin": hash_password("admin")}

def check_login(username, password):
    users = st.session_state.user_db
    if username in users and users[username] == hash_password(password):
        return True
    return False

def register_user(username, password):
    if username in st.session_state.user_db:
        return False
    st.session_state.user_db[username] = hash_password(password)
    return True

# --- 3. SESSION STATE INIT ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# =========================================================
# LOGIN SCREEN
# =========================================================
if not st.session_state.authenticated:
    st.title("🔒 Charity System Login")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔑 Login")
        with st.form("login_form"):
            user_in = st.text_input("Username")
            pass_in = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary"):
                if check_login(user_in, pass_in):
                    st.session_state.authenticated = True
                    st.session_state.username = user_in
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")

    with col2:
        st.markdown("### 📝 Register")
        with st.form("reg_form"):
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            if st.form_submit_button("Create Account"):
                if len(new_user) < 3 or len(new_pass) < 3:
                    st.error("Username/Password too short")
                elif register_user(new_user, new_pass):
                    st.success("User Created! You can now Login.")
                else:
                    st.error("User already exists.")

    # --- USER DATABASE MANAGEMENT (Crucial for Persistence) ---
    st.divider()
    st.warning("⚠️ IMPORTANT: User accounts are lost if the app restarts. Download the backup below.")
    
    c_back, c_rest = st.columns(2)
    with c_back:
        # Export Users
        user_json = json.dumps(st.session_state.user_db)
        st.download_button("💾 Download User List (Backup)", user_json, "users.json", "application/json")
        
    with c_rest:
        # Import Users
        uploaded_users = st.file_uploader("Restore User List (users.json)", type=['json'])
        if uploaded_users:
            try:
                loaded_users = json.load(uploaded_users)
                st.session_state.user_db.update(loaded_users)
                st.success("User list restored!")
            except:
                st.error("Invalid JSON file")

    st.stop() # Stop here if not logged in

# =========================================================
# MAIN APP (USER IS LOGGED IN)
# =========================================================

# Generate unique filename for the user's data
CURRENT_DB_FILE = f"data_{st.session_state.username}.csv"

# --- DATA FUNCTIONS ---
def load_data():
    expected_cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                     "Address", "Reason", "Responsible", "Category", "Medical", "Amount"]
    
    # Try loading from disk if it exists in current session
    if os.path.exists(CURRENT_DB_FILE):
        try:
            df = pd.read_csv(CURRENT_DB_FILE)
            for col in expected_cols:
                if col not in df.columns: df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=expected_cols)
    return pd.DataFrame(columns=expected_cols)

def save_data(df):
    df.to_csv(CURRENT_DB_FILE, index=False)

def generate_pdf(member_name, year, dataframe, header_msg, footer_msg, grand_total):
    if not HAS_PDF: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph(f"Contribution Report: {member_name}", styles['Title']))
    elements.append(Paragraph(f"Year: {year}", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    if header_msg: elements.append(Paragraph(header_msg, styles['Normal'])); elements.append(Spacer(1, 12))
    
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
    
    t = Table(clean_data)
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkgreen), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    if footer_msg: elements.append(Paragraph(footer_msg, styles['Normal']))
    
    elements.append(Paragraph("_" * 30, styles['Normal']))
    elements.append(Paragraph("Authorized Signature", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Load Data into Session
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"👤 {st.session_state.username}")
    
    if st.button("Logout", type="primary"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        # We don't delete user_db here so other users persist in session
        st.rerun()
        
    st.divider()
    st.info(f"Data File: {CURRENT_DB_FILE}")
    
    # 1. Backup Data
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Backup Transactions (CSV)", csv, f"backup_{st.session_state.username}.csv", "text/csv")
    
    # 2. Restore Data
    uploaded = st.file_uploader("Restore Transactions", type=['csv'])
    if uploaded:
        try:
            st.session_state.df = pd.read_csv(uploaded)
            save_data(st.session_state.df)
            st.success("Transactions Restored!")
            st.rerun()
        except:
            st.error("Invalid CSV")
            
    # 3. Clear Data
    if st.button("⚠️ Clear My Data"):
        empty_df = pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "Medical", "Amount"])
        save_data(empty_df)
        st.session_state.df = empty_df
        st.rerun()

# --- DASHBOARD ---
st.title("Charity Management System")

df = st.session_state.df
curr_yr = int(datetime.now().year)
tot_inc = 0.0; yr_inc = 0.0; tot_don = 0.0; yr_don = 0.0

if not df.empty:
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    tot_inc = df[df['Type'] == 'Incoming']['Amount'].sum()
    yr_inc = df[(df['Type'] == 'Incoming') & (df['Year'] == curr_yr)]['Amount'].sum()
    tot_don = df[df['Type'] == 'Outgoing']['Amount'].sum()
    yr_don = df[(df['Type'] == 'Outgoing') & (df['Year'] == curr_yr)]['Amount'].sum()

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
    st.subheader("New Transaction")
    
    # TYPE SELECTION (Outside form for immediate update)
    t_type = st.radio("Select Type:", ["Incoming", "Outgoing"], horizontal=True, key="t_select")
    
    # VARS FOR OUTSIDE FORM LOGIC
    category_selection = ""
    medical_selection = ""
    
    # IF OUTGOING -> Show Donation Categories Immediately
    if t_type == "Outgoing":
        st.info("Please select donation details:")
        col_cat, col_med = st.columns(2)
        category_selection = col_cat.selectbox("Donation Category", OUTGOING_TYPES, key="cat_select")
        
        if category_selection == "Medical help":
            medical_selection = col_med.selectbox("Medical Condition", MEDICAL_SUB_TYPES, key="med_select")
    
    st.divider()
    
    with st.form("txn_form", clear_on_submit=True):
        # Common
        c_date, c_amt = st.columns(2)
        date_val = c_date.date_input("Date", datetime.today())
        amount = c_amt.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=5.0)
        
        # Init
        member_name, group, category, medical = "", "N/A", "", ""
        address, reason, responsible = "", "", ""
        
        if t_type == "Incoming":
            col1, col2, col3 = st.columns(3)
            group = col1.radio("Group", ["Brother", "Sister"], horizontal=True)
            
            # Name Logic
            existing = sorted(df[(df['Type'] == 'Incoming') & (df['Group'] == group)]['Name_Details'].unique().tolist()) if not df.empty else []
            mode = col2.radio("Name Input", ["Select Existing", "Type New"], horizontal=True, label_visibility="collapsed")
            
            if existing and mode == "Select Existing":
                member_name = col2.selectbox("Select Member", existing)
            else:
                member_name = col2.text_input("Enter Member Name")
                
            category = col3.selectbox("Category", INCOME_TYPES)
            
        else: # Outgoing (Inputs inside form)
            col1, col2 = st.columns(2)
            member_name = col1.text_input("Beneficiary Name")
            address = col2.text_input("Address / Location")
            
            col3, col4 = st.columns(2)
            reason = col3.text_input("Reason")
            
            # Responsible
            all_mems = sorted(df[df['Type'] == 'Incoming']['Name_Details'].unique().tolist()) if not df.empty else []
            r_mode = col4.radio("Responsible", ["Select Member", "Type Name"], horizontal=True, label_visibility="collapsed")
            if all_mems and r_mode == "Select Member":
                responsible = col4.selectbox("Select Responsible", all_mems)
            else:
                responsible = col4.text_input("Enter Responsible Name")
            
            # Map outside variables to inside form
            category = category_selection
            if category == "Medical help":
                if medical_selection == "Other":
                    medical = st.text_input("Specify Medical Condition")
                else:
                    medical = medical_selection
        
        # Submit
        if st.form_submit_button("💾 Save Transaction", type="primary"):
            if amount > 0 and member_name:
                new_row = {
                    "ID": str(uuid.uuid4()), "Date": str(date_val), 
                    "Year": int(date_val.year), "Month": int(date_val.month),
                    "Type": t_type, "Group": group, "Name_Details": member_name, 
                    "Address": address, "Reason": reason, "Responsible": responsible,
                    "Category": category, "Medical": medical, "Amount": amount
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("Saved!")
                st.rerun()
            else:
                st.error("Name and Amount required.")

# === TAB 2: LOG ===
with tab2:
    st.subheader("Activities Log")
    f1, f2, f3, f4 = st.columns(4)
    f_yr = f1.selectbox("Filter Year", ["All"] + sorted(list(set(df['Year'].astype(str)))) if not df.empty else ["All"])
    f_tp = f2.selectbox("Filter Type", ["All", "Incoming", "Outgoing"])
    f_gr = f3.selectbox("Filter Group", ["All", "Brother", "Sister"])
    
    view = st.session_state.df.copy()
    if f_yr != "All": view = view[view['Year'] == int(f_yr)]
    if f_tp != "All": view = view[view['Type'] == f_tp]
    if f_gr != "All": view = view[view['Group'] == f_gr]
    
    cols = ["Date", "Type", "Name_Details", "Category", "Medical", "Address", "Reason", "Responsible", "Amount"]
    edited = st.data_editor(view[cols], column_config={"Amount": st.column_config.NumberColumn(format="€%.2f")}, use_container_width=True, num_rows="dynamic", key="log_edit")
    
    if st.button("Save Edits"):
        st.session_state.df.update(edited)
        save_data(st.session_state.df)
        st.success("Updated!")
        st.rerun()

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
        else: st.warning("No data.")

# === TAB 4: REPORT ===
with tab4:
    st.subheader("Member Report")
    mc1, mc2, mc3 = st.columns(3)
    mat_grp = mc1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mg")
    mems_list = df[df['Type'] == 'Incoming']
    if mat_grp != "All": mems_list = mems_list[mems_list['Group'] == mat_grp]
    mems = sorted(mems_list['Name_Details'].unique())
    
    if mems:
        target = mc2.selectbox("Select Member", mems)
        tyear = mc3.selectbox("Select Year", ["All"] + sorted(list(set(df['Year'].astype(str)))))
        mdf = df[(df['Name_Details'] == target) & (df['Type'] == 'Incoming')]
        if tyear != "All": mdf = mdf[mdf['Year'] == int(tyear)]
        
        if not mdf.empty:
            piv = mdf.pivot_table(index="Date", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
            piv['Daily Total'] = piv.sum(axis=1)
            g_tot = piv['Daily Total'].sum()
            st.dataframe(piv, use_container_width=True)
            st.success(f"Grand Total: {CURRENCY}{g_tot:,.2f}")
            
            with st.expander("PDF Options"):
                h = st.text_area("Header", "Thanks for your contribution.")
                f = st.text_area("Footer", "Contact admin for queries.")
            
            if HAS_PDF:
                pdf = generate_pdf(target, tyear, piv, h, f, g_tot)
                st.download_button("Download PDF", pdf, f"{target}_Report.pdf", "application/pdf")
        else: st.info("No records.")
