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
CURRENCY = "€"

# CATEGORY LISTS
INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]

# Outgoing Logic Lists
SADAKA_SUB_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_CONDITIONS = ["Heart", "Cancer", "Kidney", "Eye", "Brain", "Bone", "Other"]

# --- 2. AUTHENTICATION & FILE FUNCTIONS ---
def get_user_db_file(username):
    clean_name = "".join(x for x in username if x.isalnum())
    return f"data_{clean_name}.csv"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_users():
    default_users = {"admin": hash_password("admin")}
    if not os.path.exists(USER_FILE): return default_users
    try:
        with open(USER_FILE, 'r') as f:
            users = json.load(f)
            if "admin" not in users: users["admin"] = hash_password("admin")
            return users
    except: return default_users

def save_user_db(users_dict):
    with open(USER_FILE, 'w') as f: json.dump(users_dict, f)

def check_login(username, password):
    users = load_users()
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
        if os.path.exists(USER_FILE):
            with open(USER_FILE, "r") as f:
                st.download_button("💾 Backup Logins", f, "users_backup.json", "application/json")
        up_users = st.file_uploader("Restore Logins", type=['json'])
        if up_users:
            save_user_db(json.load(up_users))
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
                users = load_users()
                if nu in users: st.error("Exists")
                else:
                    users[nu] = hash_password(np)
                    save_user_db(users)
                    st.success("Created! Please Login.")
    st.stop()

# =========================================================
# MAIN APP
# =========================================================
CURRENT_DB_FILE = get_user_db_file(st.session_state.username)

def load_data():
    # Updated Schema to include SubCategory
    expected_cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                     "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical", "Amount"]
    
    if os.path.exists(CURRENT_DB_FILE):
        try:
            df = pd.read_csv(CURRENT_DB_FILE)
            # FORCE MIGRATION: Add missing columns if they don't exist
            missing = [c for c in expected_cols if c not in df.columns]
            if missing:
                for c in missing: df[c] = ""
                df.to_csv(CURRENT_DB_FILE, index=False)
            
            # Clean NaNs
            text_cols = ["Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical"]
            for c in text_cols:
                df[c] = df[c].fillna("")
                
            return df
        except: return pd.DataFrame(columns=expected_cols)
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
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    st.divider()
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Backup My Data", csv, f"backup_{st.session_state.username}.csv", "text/csv")
    uploaded = st.file_uploader("Restore Data", type=['csv'])
    if uploaded:
        st.session_state.df = pd.read_csv(uploaded)
        save_data(st.session_state.df)
        st.success("Restored!")
        st.rerun()
    if st.button("⚠️ Clear All Data"):
        empty = pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical", "Amount"])
        save_data(empty)
        st.session_state.df = empty
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
c2.metric(f"Income {curr_yr}", f"{CURRENCY}{yr_inc:,.2f}")
c3.metric("Total Donation", f"{CURRENCY}{tot_don:,.2f}")
c4.metric(f"Donation {curr_yr}", f"{CURRENCY}{yr_don:,.2f}")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Transaction", "2. Activities Log", "3. Analysis", "4. Member Report"])

# === TAB 1: TRANSACTION ===
with tab1:
    st.subheader("New Transaction")
    
    # TYPE SELECTION OUTSIDE FORM
    t_type = st.radio("Select Type:", ["Incoming", "Outgoing"], horizontal=True, key="t_select")
    
    # DYNAMIC LOGIC VARIABLES (Calculated OUTSIDE the form)
    sel_group = "N/A"
    sel_category = ""
    sel_sub_category = ""
    sel_medical = ""
    
    # --- DYNAMIC SELECTION LOGIC ---
    if t_type == "Outgoing":
        st.info("ℹ️ Donation Details:")
        
        # 1. Group Selection
        sel_group = st.radio("Donation Group:", ["Brother", "Sister"], horizontal=True, key="out_grp")
        
        # 2. Main Category Selection (Matched to Income Types)
        sel_category = st.selectbox("Donation Category", INCOME_TYPES, key="out_cat")
        
        # 3. Sub-Category Logic (Only if Sadaka)
        if sel_category == "Sadaka":
            sel_sub_category = st.selectbox("Sadaka Type", SADAKA_SUB_TYPES, key="out_sub")
            
            # 4. Medical Logic (Only if Medical help)
            if sel_sub_category == "Medical help":
                med_choice = st.selectbox("Medical Condition", MEDICAL_CONDITIONS, key="out_med")
                if med_choice == "Other":
                    sel_medical = st.text_input("Specify Condition", key="out_med_txt")
                else:
                    sel_medical = med_choice
    
    st.markdown("---")
    
    with st.form("txn_form", clear_on_submit=True):
        # Date & Amount
        c_date, c_amt = st.columns(2)
        date_val = c_date.date_input("Date", datetime.today())
        amount = c_amt.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=5.0)
        
        # Init internal vars
        member_name = ""
        address, reason, responsible = "", "", ""
        
        if t_type == "Incoming":
            st.write("#### 📥 Income Details")
            c1, c2, c3 = st.columns(3)
            
            # Group (Local scope for Incoming)
            inc_group = c1.radio("Group", ["Brother", "Sister"], horizontal=True)
            
            # Name Logic
            existing = sorted(df[(df['Type'] == 'Incoming') & (df['Group'] == inc_group)]['Name_Details'].unique().tolist()) if not df.empty else []
            mode = c2.radio("Input Mode", ["Select Existing", "Type New"], horizontal=True, label_visibility="collapsed")
            if existing and mode == "Select Existing":
                member_name = c2.selectbox("Member Name", existing)
            else:
                member_name = c2.text_input("Enter Member Name")
                
            inc_category = c3.selectbox("Category", INCOME_TYPES)
            
            # Assign to main variables
            sel_group = inc_group
            sel_category = inc_category
            
        else: # Outgoing Form Fields
            st.write("#### 📤 Beneficiary & Responsible")
            col_a, col_b = st.columns(2)
            member_name = col_a.text_input("Beneficiary Name")
            address = col_b.text_input("Address / Location")
            
            col_c, col_d = st.columns(2)
            reason = col_c.text_input("Reason / Note")
            
            # Responsible Person
            all_mems = sorted(df[df['Type'] == 'Incoming']['Name_Details'].unique().tolist()) if not df.empty else []
            resp_mode = col_d.radio("Resp. Person", ["Select Member", "Type Name"], horizontal=True, label_visibility="collapsed")
            if all_mems and resp_mode == "Select Member":
                responsible = col_d.selectbox("Responsible", all_mems)
            else:
                responsible = col_d.text_input("Responsible Name")
        
        # SUBMIT
        if st.form_submit_button("💾 Save Transaction", type="primary"):
            if amount > 0 and member_name:
                new_row = {
                    "ID": str(uuid.uuid4()), "Date": str(date_val), 
                    "Year": int(date_val.year), "Month": int(date_val.month),
                    "Type": t_type, 
                    "Group": sel_group, 
                    "Name_Details": member_name, 
                    "Address": address, "Reason": reason, "Responsible": responsible,
                    "Category": sel_category, 
                    "SubCategory": sel_sub_category,
                    "Medical": sel_medical, 
                    "Amount": amount
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("Saved Successfully!")
                st.rerun()
            else:
                st.error("Name and Amount required.")

    # Recent Transactions Table
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
    
    cols = ["Date", "Type", "Name_Details", "Category", "SubCategory", "Medical", "Address", "Responsible", "Amount"]
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

# === TAB 4: REPORT ===
with tab4:
    st.subheader("Member Report")
    c1, c2, c3 = st.columns(3)
    mat_grp = c1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mg")
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
            
            with st.expander("PDF Options"):
                h = st.text_area("Header", "Thanks for your contribution.")
                f = st.text_area("Footer", "Contact admin for queries.")
            
            if HAS_PDF:
                pdf = generate_pdf(target, tyear, piv, h, f, gtot)
                st.download_button("Download PDF", pdf, f"{target}_Report.pdf", "application/pdf")
        else: st.info("No records.")
    else: st.info("No members found.")
