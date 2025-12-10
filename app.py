import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import uuid
import io

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
CURRENCY = "€"
YEAR_LIST = [str(y) for y in range(2023, 2101)]
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]

INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]

# --- 2. DATA FUNCTIONS ---
def load_data():
    # Define all columns we expect
    expected_cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                     "Address", "Reason", "Responsible", "Category", "Medical", "Amount"]
    
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # Migration: Add missing columns if loading an old CSV
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
    """Generates a PDF in memory"""
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

    # Prepare Data
    df_reset = dataframe.reset_index()
    # Convert headers
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
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
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

# Initialize Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("💚 Charity Menu")
    
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Download Backup (CSV)", csv, "charity_backup.csv", "text/csv", type="primary")
    
    st.divider()
    
    uploaded_file = st.file_uploader("Restore Database (Upload CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            st.session_state.df = pd.read_csv(uploaded_file)
            save_data(st.session_state.df)
            st.success("Database Restored!")
            st.rerun()
        except:
            st.error("Invalid CSV file.")
            
    if st.button("⚠️ Clear All Data"):
        st.session_state.df = pd.DataFrame(columns=["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", "Address", "Reason", "Responsible", "Category", "Medical", "Amount"])
        save_data(st.session_state.df)
        st.rerun()

# --- 4. DASHBOARD ---
st.title("Charity Management System")

df = st.session_state.df
current_year = int(datetime.now().year)

# Calculations
tot_inc = 0.0
yr_inc = 0.0
tot_don = 0.0
yr_don = 0.0

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

# --- 5. TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Transaction", "2. Activities Log", "3. Analysis", "4. Member Report"])

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
        
        # Init variables
        member_name = ""
        group = "N/A"
        category = ""
        medical = ""
        address = ""
        reason = ""
        responsible = ""
        
        # --- LOGIC FOR INCOMING ---
        if t_type == "Incoming":
            st.divider()
            c_grp, c_mem, c_cat = st.columns([1,2,2])
            group = c_grp.radio("Group", ["Brother", "Sister"], horizontal=True)
            
            existing_mems = []
            if not df.empty:
                existing_mems = sorted(df[(df['Type'] == 'Incoming') & (df['Group'] == group)]['Name_Details'].unique().tolist())
            
            member_name_sel = c_mem.selectbox("Member Name", options=["Select..."] + existing_mems + ["Add New..."])
            
            if member_name_sel == "Add New..." or member_name_sel == "Select...":
                member_name = c_mem.text_input("Type Name Manualy")
            else:
                member_name = member_name_sel
                
            category = c_cat.selectbox("Category", INCOME_TYPES)
            
        # --- LOGIC FOR OUTGOING (DONATION) ---
        else:
            st.divider()
            st.markdown("##### 📤 Donation Details")
            
            row_a1, row_a2 = st.columns(2)
            member_name = row_a1.text_input("Beneficiary Person Name")
            address = row_a2.text_input("Address / Location")
            
            row_b1, row_b2 = st.columns(2)
            reason = row_b1.text_input("Reason / Note")
            
            # Responsible Person Selection
            all_members = sorted(df[df['Type'] == 'Incoming']['Name_Details'].unique().tolist()) if not df.empty else []
            resp_select = row_b2.selectbox("Responsible Person", options=["Select..."] + all_members + ["Other"])
            if resp_select == "Other" or resp_select == "Select...":
                responsible = row_b2.text_input("Type Responsible Person Name")
            else:
                responsible = resp_select
            
            row_c1, row_c2 = st.columns(2)
            category = row_c1.selectbox("Donation Category", OUTGOING_TYPES)
            
            if category == "Medical help":
                med_select = row_c2.selectbox("Medical Condition", MEDICAL_SUB_TYPES)
                if med_select == "Other":
                    medical = row_c2.text_input("Specify Condition")
                else:
                    medical = med_select
        
        st.divider()
        if st.form_submit_button("💾 Save Transaction", type="primary"):
            if amount > 0 and member_name:
                m_idx = MONTHS.index(month) + 1
                date_str = f"{year}-{m_idx:02d}-{int(day):02d}"
                
                new_row = {
                    "ID": str(uuid.uuid4()), 
                    "Date": date_str,
                    "Year": int(year), 
                    "Month": month,
                    "Type": t_type, 
                    "Group": group,
                    "Name_Details": member_name, # Stored as 'Name_Details'
                    "Address": address,
                    "Reason": reason,
                    "Responsible": responsible,
                    "Category": category, 
                    "Medical": medical, 
                    "Amount": amount
                }
                
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success(f"Successfully Saved: {t_type} - {amount} {CURRENCY}")
                st.rerun()
            else:
                st.error("Please enter a valid Name and Amount.")

# === TAB 2: ACTIVITIES LOG ===
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
    
    # Columns to show
    cols_to_show = ["Date", "Type", "Name_Details", "Category", "Medical", "Address", "Reason", "Responsible", "Amount"]
    
    edited_df = st.data_editor(
        view[cols_to_show],
        column_config={
            "Name_Details": "Name / Beneficiary",
            "Amount": st.column_config.NumberColumn(format="€%.2f")
        },
        use_container_width=True,
        num_rows="dynamic",
        key="editor"
    )
    
    if st.button("💾 Save Changes to Database"):
        if f_yr == "All" and f_tp == "All" and f_gr == "All":
            # For simplicity in this lightweight version, we replace the DF if filters are cleared
            # This is safer than partial updates without complex ID matching
            st.session_state.df = edited_df
            save_data(st.session_state.df)
            st.success("Changes Saved!")
            st.rerun()
        else:
            st.warning("Please set all filters to 'All' before saving edits to avoid data loss.")

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
    st.subheader("Member Contribution Report")
    
    mc1, mc2, mc3 = st.columns(3)
    mat_grp = mc1.selectbox("Filter Group", ["All", "Brother", "Sister"], key="mat_grp")
    
    mems_list = df[df['Type'] == 'Incoming']
    if mat_grp != "All": mems_list = mems_list[mems_list['Group'] == mat_grp]
    mems = sorted(mems_list['Name_Details'].unique())
    
    if mems:
        target = mc2.selectbox("Select Member", mems)
        tyear = mc3.selectbox("Select Year", ["All"] + YEAR_LIST, key="myr")
        
        with st.expander("📝 PDF Custom Messages", expanded=False):
            header_txt = st.text_area("Header Message", "We appreciate your generous contributions.")
            footer_txt = st.text_area("Footer Message", "Please contact admin for discrepancies.")
        
        mdf = df[(df['Name_Details'] == target) & (df['Type'] == 'Incoming')]
        if tyear != "All": mdf = mdf[mdf['Year'] == int(tyear)]
        
        if not mdf.empty:
            piv = mdf.pivot_table(index="Date", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
            piv['Daily Total'] = piv.sum(axis=1)
            grand_total = piv['Daily Total'].sum()
            
            st.dataframe(piv, use_container_width=True)
            st.success(f"**Grand Total: {CURRENCY}{grand_total:,.2f}**")
            
            # PDF Generation
            if HAS_PDF:
                pdf_file = generate_pdf(target, tyear, piv, header_txt, footer_txt, grand_total)
                if pdf_file:
                    st.download_button(
                        label="📄 Download PDF Report",
                        data=pdf_file,
                        file_name=f"{target}_Report_{tyear}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
            else:
                st.warning("PDF Library (reportlab) not found. Add 'reportlab' to requirements.txt")
                
        else:
            st.info("No records found.")
    else:
        st.info("No members recorded yet.")
