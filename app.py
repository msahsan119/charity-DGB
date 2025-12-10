import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import uuid
import io
import hashlib
import json

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

# Constants
DATA_FILE = "charity_data.csv"
USER_FILE = "users.json"
CURRENCY = "€"
YEAR_LIST = [str(y) for y in range(2023, 2101)]
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]

INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]

# --- 2. AUTHENTICATION FUNCTIONS ---
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    try:
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_user(username, password):
    users = load_users()
    users[username] = hash_password(password)
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)

def check_login(username, password):
    users = load_users()
    if username in users and users[username] == hash_password(password):
        return True
    return False

# --- 3. SESSION STATE INIT ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# --- 4. LOGIN SYSTEM UI ---
if not st.session_state.authenticated:
    st.title("🔒 Charity System Access")
    
    auth_mode = st.radio("Select Option:", ["Login", "Register New User"], horizontal=True)
    
    with st.form("auth_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Submit")
        
        if submit:
            if auth_mode == "Login":
                if check_login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            
            elif auth_mode == "Register New User":
                users = load_users()
                if username in users:
                    st.error("Username already exists.")
                elif len(username) < 3 or len(password) < 3:
                    st.error("Username and Password must be at least 3 characters.")
                else:
                    save_user(username, password)
                    st.success("Account created! Please switch to 'Login' tab to sign in.")

    st.stop() # Stop code here if not logged in

# =========================================================
# MAIN APPLICATION (Only runs if Logged In)
# =========================================================

# --- DATA FUNCTIONS ---
def load_data():
    expected_cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                     "Address", "Reason", "Responsible", "Category", "Medical", "Amount"]
    
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=expected_cols)
    return pd.DataFrame(columns=expected_cols)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def generate_pdf(member_name, year, dataframe, header_msg, footer_msg, grand_total):
    if not HAS_PDF: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph(f"Contribution Report: {member_name}", styles['Title']))
    elements.append(Paragraph(f"Year: {year}", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    if header_msg:
        elements.append(Paragraph(header_msg, styles['Normal']))
        elements.append(Spacer(1, 12))

    df_reset = dataframe.reset_index()
    headers = [col for col in df_reset.columns]
    data = [headers] + df_reset.values.tolist()
    
    clean_data = []
    for row in data:
        clean_row = []
        for item in row:
            if isinstance(item, float) or isinstance(item, int):
                clean_row.append(f"{item:,.2f}")
            else:
                clean_row.append(str(item))
        clean_data.append(clean_row)
        
    total_row = [""] * (len(clean_data[0]) - 2) + ["GRAND TOTAL:", f"{grand_total:,.2f}"]
    clean_data.append(total_row)

    t = Table(clean_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    if footer_msg:
        elements.append(Paragraph(footer_msg, styles['Normal']))
        elements.append(Spacer(1, 30))

    elements.append(Paragraph("_" * 30, styles['Normal']))
    elements.append(Paragraph("Authorized Signature", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# Load Data
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.divider()
    st.info("System Menu")
    
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Download Backup", csv, "charity_backup.csv", "text/csv")
    
    uploaded_file = st.file_uploader("Restore Database", type=['csv'])
    if uploaded_file is not None:
        try:
            st.session_state.df = pd.read_csv(uploaded_file)
            save_data(st.session_state.df)
            st.success("Restored!")
            st.rerun()
        except:
            st.error("Invalid CSV")
            
    if st.button("⚠️ Clear All Data"):
        empty_df = pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "Medical", "Amount"])
        save_data(empty_df)
        st.session_state.df = empty_df
        st.rerun()

# --- DASHBOARD ---
st.title("Charity Management System")

df = st.session_state.df
current_year = int(datetime.now().year)
tot_inc = 0.0; yr_inc = 0.0; tot_don = 0.0; yr_don = 0.0

if not df.empty:
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    tot_inc = df[df['Type'] == 'Incoming']['Amount'].sum()
    yr_inc = df[(df['Type'] == 'Incoming') & (df['Year'] == current_year)]['Amount'].sum()
    tot_don = df[df['Type'] == 'Outgoing']['Amount'].sum()
    yr_don = df[(df['Type'] == 'Outgoing') & (df['Year'] == current_year)]['Amount'].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Income", f"{CURRENCY}{tot_inc:,.2f}")
c2.metric(f"Income {current_year}", f"{CURRENCY}{yr_inc:,.2f}")
c3.metric("Total Donation", f"{CURRENCY}{tot_don:,.2f}")
c4.metric(f"Donation {current_year}", f"{CURRENCY}{yr_don:,.2f}")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Transaction", "2. Activities Log", "3. Analysis", "4. Member Report"])

# === TAB 1: TRANSACTION ===
with tab1:
    st.subheader("New Transaction")
    
    with st.form("entry_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        t_type = col1.radio("Type", ["Incoming", "Outgoing"], horizontal=True)
        year = col2.selectbox("Year", YEAR_LIST)
        month = col3.selectbox("Month", MONTHS, index=datetime.now().month-1)
        day = col4.number_input("Day", 1, 31, datetime.now().day)
        
        amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=5.0)
        
        # Variables
        member_name, group, category, medical = "", "N/A", "", ""
        address, reason, responsible = "", "", ""
        
        # LOGIC
        if t_type == "Incoming":
            st.divider()
            c_grp, c_mem, c_cat = st.columns([1,2,2])
            group = c_grp.radio("Group", ["Brother", "Sister"], horizontal=True)
            
            existing_mems = []
            if not df.empty:
                existing_mems = sorted(df[(df['Type'] == 'Incoming') & (df['Group'] == group)]['Name_Details'].unique().tolist())
            
            member_name_sel = c_mem.selectbox("Member Name", options=["Select..."] + existing_mems + ["Add New..."])
            if member_name_sel == "Add New..." or member_name_sel == "Select...":
                member_name = c_mem.text_input("Type Name Manually")
            else:
                member_name = member_name_sel
                
            category = c_cat.selectbox("Category", INCOME_TYPES)
            
        else:
            # Outgoing Logic
            st.divider()
            st.markdown("##### 📤 Donation Details")
            ra1, ra2 = st.columns(2)
            member_name = ra1.text_input("Beneficiary Name")
            address = ra2.text_input("Address / Location")
            
            rb1, rb2 = st.columns(2)
            reason = rb1.text_input("Reason")
            
            all_mems = sorted(df[df['Type'] == 'Incoming']['Name_Details'].unique().tolist()) if not df.empty else []
            resp_sel = rb2.selectbox("Responsible Person", options=["Select..."] + all_mems + ["Other"])
            responsible = rb2.text_input("Type Name") if resp_sel == "Other" or resp_sel == "Select..." else resp_sel
            
            rc1, rc2 = st.columns(2)
            category = rc1.selectbox("Donation Category", OUTGOING_TYPES)
            
            # FIXED MEDICAL LOGIC: Only show if category matches
            if category == "Medical help":
                med_sel = rc2.selectbox("Medical Condition", MEDICAL_SUB_TYPES)
                medical = rc2.text_input("Specify Condition") if med_sel == "Other" else med_sel
            else:
                medical = "" # Ensure it's empty for non-medical donations
        
        if st.form_submit_button("💾 Save Transaction", type="primary"):
            if amount > 0 and member_name:
                m_idx = MONTHS.index(month) + 1
                date_str = f"{year}-{m_idx:02d}-{int(day):02d}"
                
                new_row = {
                    "ID": str(uuid.uuid4()), "Date": date_str, "Year": int(year), "Month": month,
                    "Type": t_type, "Group": group, 
                    "Name_Details": member_name, "Address": address, "Reason": reason, 
                    "Responsible": responsible, "Category": category, "Medical": medical, "Amount": amount
                }
                
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("Saved Successfully!")
                st.rerun()
            else:
                st.error("Please enter Name and Amount.")

    if not df.empty:
        st.caption("Recent Transactions")
        st.dataframe(df.tail(5).iloc[::-1][["Date", "Type", "Category", "Name_Details", "Amount"]], hide_index=True)

# === TAB 2: LOG ===
with tab2:
    st.subheader("Activities Log")
    f1, f2, f3, f4 = st.columns(4)
    f_yr = f1.selectbox("Filter Year", ["All"] + YEAR_LIST)
    f_tp = f2.selectbox("Filter Type", ["All", "Incoming", "Outgoing"])
    f_gr = f3.selectbox("Filter Group", ["All", "Brother", "Sister"])
    
    view = st.session_state.df.copy()
    if f_yr != "All": view = view[view['Year'] == int(f_yr)]
    if f_tp != "All": view = view[view['Type'] == f_tp]
    if f_gr != "All": view = view[view['Group'] == f_gr]
    
    cols_to_show = ["Date", "Type", "Name_Details", "Category", "Medical", "Address", "Reason", "Responsible", "Amount"]
    edited_df = st.data_editor(view[cols_to_show], column_config={"Amount": st.column_config.NumberColumn(format="€%.2f")}, use_container_width=True, num_rows="dynamic", key="editor")
    
    if st.button("💾 Save Changes"):
        if f_yr == "All" and f_tp == "All" and f_gr == "All":
            st.session_state.df.update(edited_df)
            save_data(st.session_state.df)
            st.success("Updated!")
            st.rerun()
        else:
            st.warning("Set filters to 'All' to save.")

# === TAB 3: ANALYSIS ===
with tab3:
    st.subheader("Analysis")
    ac1, ac2 = st.columns(2)
    grp = ac1.selectbox("Group", ["All", "Brother", "Sister"], key="a_grp")
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
        else:
            st.warning("No data found.")

# === TAB 4: MEMBER REPORT ===
with tab4:
    st.subheader("Member Report")
    mc1, mc2, mc3 = st.columns(3)
    mat_grp = mc1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mat_grp")
    
    mems_list = df[df['Type'] == 'Incoming']
    if mat_grp != "All": mems_list = mems_list[mems_list['Group'] == mat_grp]
    mems = sorted(mems_list['Name_Details'].unique())
    
    if mems:
        target = mc2.selectbox("Select Member", mems)
        tyear = mc3.selectbox("Select Year", ["All"] + YEAR_LIST, key="myr")
        
        with st.expander("📝 PDF Messages"):
            h_txt = st.text_area("Header", "We appreciate your contribution.")
            f_txt = st.text_area("Footer", "Contact admin for queries.")
        
        mdf = df[(df['Name_Details'] == target) & (df['Type'] == 'Incoming')]
        if tyear != "All": mdf = mdf[mdf['Year'] == int(tyear)]
        
        if not mdf.empty:
            piv = mdf.pivot_table(index="Date", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
            piv['Daily Total'] = piv.sum(axis=1)
            g_tot = piv['Daily Total'].sum()
            st.dataframe(piv, use_container_width=True)
            st.success(f"Total: {CURRENCY}{g_tot:,.2f}")
            if HAS_PDF:
                pdf = generate_pdf(target, tyear, piv, h_txt, f_txt, g_tot)
                st.download_button("📄 Download PDF", pdf, f"{target}_Report.pdf", "application/pdf")
        else:
            st.info("No records.")
