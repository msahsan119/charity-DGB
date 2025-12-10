import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Charity-DGB", layout="wide", page_icon="💚")

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
    # Return empty structure if no file found
    return pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Category", "Medical", "Amount"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# Initialize Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. SIDEBAR (BACKUP SYSTEM) ---
with st.sidebar:
    st.header("💚 Charity-DGB Menu")
    st.info("System Menu")
    
    # 1. Download Button
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Download Database (Backup)",
        data=csv,
        file_name="charity_dgb_backup.csv",
        mime="text/csv",
        type="primary"
    )
    
    st.divider()
    
    # 2. Upload Button (Restore)
    uploaded_file = st.file_uploader("Restore Database (Upload CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            st.session_state.df = pd.read_csv(uploaded_file)
            save_data(st.session_state.df)
            st.success("Database Restored Successfully!")
            st.rerun()
        except:
            st.error("Invalid CSV file.")

# --- 4. DASHBOARD ---
st.title("Charity-DGB System")

# Calculate Stats
df = st.session_state.df
current_year = int(datetime.now().year)

if not df.empty:
    # Ensure amount is numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    tot_inc = df[df['Type'] == 'Incoming']['Amount'].sum()
    yr_inc = df[(df['Type'] == 'Incoming') & (df['Year'] == current_year)]['Amount'].sum()
    tot_don = df[df['Type'] == 'Outgoing']['Amount'].sum()
    yr_don = df[(df['Type'] == 'Outgoing') & (df['Year'] == current_year)]['Amount'].sum()
else:
    tot_inc, yr_inc, tot_don, yr_don = 0.0, 0.0, 0.0, 0.0

# Display Stats
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Income", f"{CURRENCY}{tot_inc:,.2f}")
c2.metric(f"Income {current_year}", f"{CURRENCY}{yr_inc:,.2f}")
c3.metric("Total Donation", f"{CURRENCY}{tot_don:,.2f}")
c4.metric(f"Donation {current_year}", f"{CURRENCY}{yr_don:,.2f}")

st.divider()

# --- 5. MAIN TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Transaction", "2. Activities Log", "3. Analysis", "4. Member Matrix"])

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
        
        # Details
        member_name, group, category, medical = "Organization", "N/A", "", ""
        
        if t_type == "Incoming":
            c_grp, c_mem, c_cat = st.columns([1,2,2])
            group = c_grp.radio("Group", ["Brother", "Sister"], horizontal=True)
            
            # Autocomplete logic
            existing = sorted(df[df['Type'] == 'Incoming']['Name_Details'].unique().tolist()) if not df.empty else []
            member_name = c_mem.text_input("Member Name")
            if existing: st.caption(f"Existing members: {', '.join(existing[:3])}...")
            
            category = c_cat.selectbox("Category", INCOME_TYPES)
        else:
            c_cat, c_med = st.columns(2)
            category = c_cat.selectbox("Type", OUTGOING_TYPES)
            if category == "Medical help":
                medical = c_med.selectbox("Condition", MEDICAL_SUB_TYPES)
        
        if st.form_submit_button("Save Transaction"):
            if amount > 0:
                # Create Date string for sorting
                m_idx = MONTHS.index(month) + 1
                date_str = f"{year}-{m_idx:02d}-{int(day):02d}"
                
                new_row = {
                    "ID": str(datetime.now().timestamp()),
                    "Date": date_str,
                    "Year": int(year), "Month": month,
                    "Type": t_type, "Group": group,
                    "Name_Details": member_name,
                    "Category": category, "Medical": medical,
                    "Amount": amount
                }
                
                # Add to DataFrame and Save
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("Transaction Saved!")
                st.rerun()
            else:
                st.error("Please enter a valid amount.")

# === TAB 2: ACTIVITIES LOG ===
with tab2:
    st.subheader("Activities Log")
    
    # Filters
    f1, f2, f3, f4 = st.columns(4)
    f_yr = f1.selectbox("Filter Year", ["All"] + YEAR_LIST)
    f_tp = f2.selectbox("Filter Type", ["All", "Incoming", "Outgoing"])
    f_gr = f3.selectbox("Filter Group", ["All", "Brother", "Sister"])
    
    # Filter Data
    view = st.session_state.df.copy()
    if f_yr != "All": view = view[view['Year'] == int(f_yr)]
    if f_tp != "All": view = view[view['Type'] == f_tp]
    if f_gr != "All": view = view[view['Group'] == f_gr]
    
    # Display Table
    st.dataframe(
        view[["Date", "Type", "Group", "Name_Details", "Category", "Medical", "Amount"]], 
        use_container_width=True,
        hide_index=True
    )
    st.info(f"**Total in View: {CURRENCY}{view['Amount'].sum():,.2f}**")

# === TAB 3: ANALYSIS ===
with tab3:
    st.subheader("Analysis")
    
    if not st.session_state.df.empty:
        ac1, ac2 = st.columns(2)
        grp = ac1.selectbox("Group", ["All", "Brother", "Sister"], key="a_grp")
        cat = ac2.selectbox("Category", ["All"] + INCOME_TYPES, key="a_cat")
        
        adf = st.session_state.df[st.session_state.df['Type'] == 'Incoming']
        
        if grp != "All": adf = adf[adf['Group'] == grp]
        if cat != "All": adf = adf[adf['Category'] == cat]
        
        if not adf.empty:
            # Group by Member Name
            stats = adf.groupby("Name_Details")['Amount'].sum().reset_index().sort_values("Amount", ascending=False)
            
            c1, c2 = st.columns([2,1])
            with c1:
                fig = px.bar(stats, x="Name_Details", y="Amount", text_auto=True, title="Contribution Analysis")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.dataframe(stats, hide_index=True, use_container_width=True)
                st.success(f"**Total: {CURRENCY}{stats['Amount'].sum():,.2f}**")
        else:
            st.warning("No data found for these filters.")
    else:
        st.info("Add data first.")

# === TAB 4: MEMBER MATRIX ===
with tab4:
    st.subheader("Member Matrix")
    
    mc1, mc2 = st.columns(2)
    
    # Get List of Members
    mems = sorted(st.session_state.df[st.session_state.df['Type'] == 'Incoming']['Name_Details'].unique().tolist())
    
    if mems:
        target = mc1.selectbox("Select Member", mems)
        tyear = mc2.selectbox("Select Year", ["All"] + YEAR_LIST, key="myr")
        
        mdf = st.session_state.df[(st.session_state.df['Name_Details'] == target) & (st.session_state.df['Type'] == 'Incoming')]
        
        if tyear != "All":
            mdf = mdf[mdf['Year'] == int(tyear)]
            
        if not mdf.empty:
            # Create Pivot Table
            piv = mdf.pivot_table(index="Date", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
            
            # Add Total Column
            piv['Daily Total'] = piv.sum(axis=1)
            
            st.dataframe(piv, use_container_width=True)
            st.success(f"**Grand Total for {target}: {CURRENCY}{piv['Daily Total'].sum():,.2f}**")
        else:
            st.info("No records found for this selection.")
    else:
        st.info("No members recorded yet.")
