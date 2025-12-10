import streamlit as st
import pandas as pd
import os
import uuid
import io
import hashlib
import json
from datetime import datetime
import plotly.express as px

# --- REPORTLAB IMPORTS ---
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

# FILES
USER_FILE = "users.json"
# We define the current DB file later based on login

# LISTS
CURRENCY = "€"
YEAR_LIST = [str(y) for y in range(2023, 2101)]
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]

# --- 2. AUTHENTICATION & FUNCTIONS ---

def get_user_db_file(username):
    # Sanitize username for filename
    clean_name = "".join(x for x in username if x.isalnum())
    return f"data_{clean_name}.csv"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_users():
    # Default Admin (Always exists)
    default_users = {"admin": hash_password("admin")}
    
    if not os.path.exists(USER_FILE):
        return default_users
    try:
        with open(USER_FILE, 'r') as f:
            loaded_users = json.load(f)
            # Ensure admin always exists even in loaded file
            if "admin" not in loaded_users:
                loaded_users["admin"] = hash_password("admin")
            return loaded_users
    except:
        return default_users

def save_user_db(users_dict):
    with open(USER_FILE, 'w') as f:
        json.dump(users_dict, f)

def check_login(username, password):
    users = load_users()
    if username in users and users[username] == hash_password(password):
        return True
    return False

# --- 3. SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# =========================================================
# LOGIN SCREEN (BLOCKING)
# =========================================================
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Charity System Login")
        
        tab_login, tab_reg = st.tabs(["Login", "Register New User"])
        
        with tab_login:
            with st.form("login_form"):
                user_in = st.text_input("Username")
                pass_in = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Login")
                
                if submit_login:
                    if check_login(user_in, pass_in):
                        st.session_state.authenticated = True
                        st.session_state.username = user_in
                        st.success("Login Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password")
                        
        with tab_reg:
            with st.form("reg_form"):
                st.caption("Create a separate database for a new user.")
                new_user = st.text_input("New Username")
                new_pass = st.text_input("New Password", type="password")
                submit_reg = st.form_submit_button("Create Account")
                
                if submit_reg:
                    users = load_users()
                    if new_user in users:
                        st.error("Username already exists.")
                    elif len(new_user) < 3 or len(new_pass) < 3:
                        st.error("Username/Password too short.")
                    else:
                        users[new_user] = hash_password(new_pass)
                        save_user_db(users)
                        st.success("User created! Go to Login tab.")
    
    # Stop execution here if not logged in
    st.stop()

# =========================================================
# MAIN APP (EXECUTED ONLY IF LOGGED IN)
# =========================================================

# Determine the database file for the logged-in user
CURRENT_DB_FILE = get_user_db_file(st.session_state.username)

# Data Load/Save Functions
def load_data():
    expected_cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                     "Address", "Reason", "Responsible", "Category", "Medical", "Amount"]
    
    if os.path.exists(CURRENT_DB_FILE):
        try:
            df = pd.read_csv(CURRENT_DB_FILE)
            # Ensure columns exist
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
    
    # Data Prep
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

# Load Data into Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 User: {st.session_state.username}")
    
    if st.button("Logout", type="primary"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.df = pd.DataFrame() # Clear data
        st.rerun()
        
    st.divider()
    st.markdown("### 🛠️ Data Tools")
    
    # Backup
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Backup Database (CSV)", csv, f"backup_{st.session_state.username}.csv", "text/csv")
    
    # Restore
    uploaded = st.file_uploader("Restore Database", type=['csv'])
    if uploaded:
        try:
            st.session_state.df = pd.read_csv(uploaded)
            save_data(st.session_state.df)
            st.success("Restored!")
            st.rerun()
        except:
            st.error("Invalid File")
            
    if st.button("⚠️ Clear All Data"):
        empty_df = pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "Medical", "Amount"])
        save_data(empty_df)
        st.session_state.df = empty_df
        st.rerun()

# --- DASHBOARD ---
st.title("Charity Management System")

# Calculate Stats
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
    
    # Type selection OUTSIDE the form to trigger updates
    t_type = st.radio("Select Type:", ["Incoming", "Outgoing"], horizontal=True)
    
    # Additional selections outside form for reactivity
    category_selection = ""
    medical_selection = ""
    
    if t_type == "Outgoing":
        st.info("Please fill Donation details below.")
        col_cat, col_med = st.columns(2)
        category_selection = col_cat.selectbox("Donation Category", OUTGOING_TYPES)
        if category_selection == "Medical help":
            medical_selection = col_med.selectbox("Medical Condition", MEDICAL_SUB_TYPES)
    
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
            
        else: # Outgoing
            col1, col2 = st.columns(2)
            member_name = col1.text_input("Beneficiary Name")
            address = col2.text_input("Address")
            
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

# === TAB 2: ACTIVITIES ===
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
    
    cols = ["Date", "Type", "Name_Details", "Category", "Medical", "Address", "Reason", "Responsible", "Amount"]
    edited = st.data_editor(view[cols], column_config={"Amount": st.column_config.NumberColumn(format="€%.2f")}, use_container_width=True, num_rows="dynamic", key="log_edit")
    
    if st.button("Save Edits"):
        if f_yr == "All" and f_tp == "All" and f_gr == "All":
            st.session_state.df.update(edited)
            save_data(st.session_state.df)
            st.success("Updated!")
            st.rerun()
        else: st.warning("Reset filters to 'All' to save.")

# === TAB 3: ANALYSIS ===
with tab3:
    st.subheader("Analysis")
    c1, c2 = st.columns(2)
    grp = c1.selectbox("Group", ["All", "Brother", "Sister"], key="an_grp")
    cat = c2.selectbox("Category", ["All"] + INCOME_TYPES, key="an_cat")
    
    if not df.empty:
        adf = df[df['Type'] == 'Incoming']
        if grp != "All": adf = adf[adf['Group'] == grp]
        if cat != "All": adf = adf[adf['Category'] == cat]
        
        if not adf.empty:
            stats = adf.groupby("Name_Details")['Amount'].sum().reset_index().sort_values("Amount", ascending=False)
            col1, col2 = st.columns([2,1])
            with col1:
                fig = px.bar(stats, x="Name_Details", y="Amount", text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(stats, hide_index=True, use_container_width=True)
                st.success(f"Total: {CURRENCY}{stats['Amount'].sum():,.2f}")
        else: st.warning("No data.")

# === TAB 4: MEMBER REPORT ===
with tab4:
    st.subheader("Member Report")
    c1, c2, c3 = st.columns(3)
    mat_grp = c1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="rep_grp")
    
    mems_list = df[df['Type'] == 'Incoming']
    if mat_grp != "All": mems_list = mems_list[mems_list['Group'] == mat_grp]
    mems = sorted(mems_list['Name_Details'].unique())
    
    if mems:
        target = c2.selectbox("Select Member", mems)
        tyear = c3.selectbox("Select Year", ["All"] + sorted(list(set(df['Year'].astype(str)))))
        
        mdf = df[(df['Name_Details'] == target) & (df['Type'] == 'Incoming')]
        if tyear != "All": mdf = mdf[mdf['Year'] == int(tyear)]
        
        if not mdf.empty:
            piv = mdf.pivot_table(index="Date", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
            piv['Daily Total'] = piv.sum(axis=1)
            gtot = piv['Daily Total'].sum()
            st.dataframe(piv, use_container_width=True)
            st.success(f"Grand Total: {CURRENCY}{gtot:,.2f}")
            
            with st.expander("PDF Custom Text"):
                h = st.text_area("Header", "We appreciate your contribution.")
                f = st.text_area("Footer", "Contact admin for details.")
            
            if HAS_PDF:
                pdf = generate_pdf(target, tyear, piv, h, f, gtot)
                st.download_button("Download PDF", pdf, f"{target}_Report.pdf", "application/pdf")
    else: st.info("No members found.")
