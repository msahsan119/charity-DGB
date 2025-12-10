import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import uuid

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Charity Management System", layout="wide", page_icon="💚")

# Constants
DATA_FILE = "charity_data.csv"
CURRENCY = "€"
YEAR_LIST = [str(y) for y in range(2023, 2101)]
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Financial help", "Medical help", "Karje Hasana", "Mosque", "Dead Body Funeral"]
MEDICAL_SUB_TYPES = ["Cancer", "Heart", "Lung", "Brain", "Bone", "Other"]

# --- 2. DATA FUNCTIONS ---
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    # Default Structure
    return pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Category", "Medical", "Amount"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# Initialize Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. SIDEBAR (MENU) ---
with st.sidebar:
    st.header("💚 Charity Menu")
    
    # Download Button
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Download Backup (CSV)", csv, "charity_backup.csv", "text/csv", type="primary")
    
    st.divider()
    
    # Restore Button
    uploaded_file = st.file_uploader("Restore Database (Upload CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            st.session_state.df = pd.read_csv(uploaded_file)
            save_data(st.session_state.df)
            st.success("Database Restored!")
            st.rerun()
        except:
            st.error("Invalid CSV file.")

# --- 4. DASHBOARD ---
st.title("Charity Management System (Online)")

df = st.session_state.df
current_year = int(datetime.now().year)

if not df.empty:
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    tot_inc = df[df['Type'] == 'Incoming']['Amount'].sum()
    yr_inc = df[(df['Type'] == 'Incoming') & (df['Year'] == current_year)]['Amount'].sum()
    tot_don = df[df['Type'] == 'Outgoing']['Amount'].sum()
    yr_don = df[(df['Type'] == 'Outgoing') & (df['Year'] == current_year)]['Amount'].sum()
else:
    tot_inc = yr_inc = tot_don = yr_don = 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Income", f"{CURRENCY}{tot_inc:,.2f}")
c2.metric(f"Income {current_year}", f"{CURRENCY}{yr_inc:,.2f}")
c3.metric("Total Donation", f"{CURRENCY}{tot_don:,.2f}")
c4.metric(f"Donation {current_year}", f"{CURRENCY}{yr_don:,.2f}")

st.divider()

# --- 5. TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Transaction", "2. Activities Log (Edit)", "3. Analysis", "4. Member Contributions"])

# === TAB 1: TRANSACTION ENTRY ===
with tab1:
    st.subheader("New Transaction")
    with st.form("entry_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        t_type = col1.radio("Type", ["Incoming", "Outgoing"], horizontal=True)
        year = col2.selectbox("Year", YEAR_LIST)
        month = col3.selectbox("Month", MONTHS, index=datetime.now().month-1)
        day = col4.number_input("Day", 1, 31, datetime.now().day)
        amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=5.0)
        
        member_name, group, category, medical = "Organization", "N/A", "", ""
        
        if t_type == "Incoming":
            c_grp, c_mem, c_cat = st.columns([1,2,2])
            group = c_grp.radio("Group", ["Brother", "Sister"], horizontal=True)
            
            # Smart Filter for Names based on Group
            existing_mems = []
            if not df.empty:
                existing_mems = sorted(df[(df['Type'] == 'Incoming') & (df['Group'] == group)]['Name_Details'].unique().tolist())
            
            member_name = c_mem.selectbox("Member Name (Select or Type)", options=existing_mems + ["Add New..."])
            if member_name == "Add New...":
                member_name = c_mem.text_input("Enter New Member Name")
                
            category = c_cat.selectbox("Category", INCOME_TYPES)
        else:
            c_cat, c_med = st.columns(2)
            category = c_cat.selectbox("Type", OUTGOING_TYPES)
            if category == "Medical help":
                medical = c_med.selectbox("Condition", MEDICAL_SUB_TYPES)
        
        if st.form_submit_button("Save Transaction"):
            if amount > 0 and member_name:
                m_idx = MONTHS.index(month) + 1
                date_str = f"{year}-{m_idx:02d}-{int(day):02d}"
                new_row = {
                    "ID": str(uuid.uuid4()), "Date": date_str,
                    "Year": int(year), "Month": month, "Type": t_type, "Group": group,
                    "Name_Details": member_name, "Category": category, "Medical": medical, "Amount": amount
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("Saved!")
                st.rerun()
            else:
                st.error("Please enter Name and Amount")

    # Last 5 Transactions
    if not df.empty:
        st.caption("Recent Transactions")
        st.dataframe(df.tail(5).iloc[::-1][["Date", "Type", "Category", "Name_Details", "Amount"]], hide_index=True)

# === TAB 2: ACTIVITIES LOG (EDITABLE) ===
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
    
    # Editable Data Editor
    edited_df = st.data_editor(
        view,
        column_config={
            "ID": None, # Hide ID
            "Amount": st.column_config.NumberColumn(format="€%.2f")
        },
        use_container_width=True,
        num_rows="dynamic",
        key="editor"
    )
    
    # Save Changes Button
    if st.button("💾 Save Changes to Database"):
        # We need to update the main dataframe with edits
        # Logic: We replace rows in main DF where IDs match edited_df
        # And delete rows that are missing (if deleted in editor)
        
        # Simple method: Replace entire dataset (only safe if filtering logic handles it well)
        # Better method for simple app: Just accept the edited_df as new truth IF no filters applied
        if f_yr == "All" and f_tp == "All" and f_gr == "All":
            st.session_state.df = edited_df
            save_data(st.session_state.df)
            st.success("Changes Saved!")
            st.rerun()
        else:
            st.warning("Editing is only enabled when 'All' filters are selected to prevent data loss. Please set filters to 'All' to edit.")

    st.info(f"**Total in view: {CURRENCY}{view['Amount'].sum():,.2f}**")

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
                fig = px.bar(stats, x="Name_Details", y="Amount", text_auto=True, title="Contribution Analysis")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.dataframe(stats, hide_index=True, use_container_width=True)
                st.success(f"**Total: {CURRENCY}{stats['Amount'].sum():,.2f}**")
        else:
            st.warning("No data found.")

# === TAB 4: MEMBER MATRIX ===
with tab4:
    st.subheader("Member Matrix")
    
    mc1, mc2 = st.columns(2)
    # Filter Group for dropdown
    mat_grp = mc1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mat_grp")
    
    mems_list = df[df['Type'] == 'Incoming']
    if mat_grp != "All": mems_list = mems_list[mems_list['Group'] == mat_grp]
    mems = sorted(mems_list['Name_Details'].unique())
    
    if mems:
        target = mc2.selectbox("Select Member", mems)
        tyear = st.selectbox("Select Year", ["All"] + YEAR_LIST, key="myr")
        
        mdf = df[(df['Name_Details'] == target) & (df['Type'] == 'Incoming')]
        if tyear != "All": mdf = mdf[mdf['Year'] == int(tyear)]
        
        if not mdf.empty:
            piv = mdf.pivot_table(index="Date", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
            piv['Daily Total'] = piv.sum(axis=1)
            
            st.dataframe(piv, use_container_width=True)
            st.success(f"**Grand Total: {CURRENCY}{piv['Daily Total'].sum():,.2f}**")
            
            # Download PDF equivalent (CSV)
            csv_mat = piv.to_csv().encode('utf-8')
            st.download_button("💾 Download Report (CSV)", csv_mat, f"{target}_report.csv", "text/csv")
        else:
            st.info("No records found.")
