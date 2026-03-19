import streamlit as st
import pandas as pd

# Set page config for a professional look
st.set_page_config(page_title="Data Integrity Guard", layout="wide")

st.title("🔍 Data Validation & Attention Tool")
st.info("This tool monitors 15 critical columns for missing data.")

# The specific columns that require attention if null
REQUIRED_COLUMNS = [
    "SITEID", "SUBJID", "VISITID", "VISITNAME", "VISITINDEX", 
    "FORMNAME", "SRECORD", "FORMREPEATKEY", "ITEMGROUPREPEATKEY", 
    "SITEMNEM", "SUBJGUID", "FORMID", "DATAPAGEID", "SRMODTM", "DOMAIN"
]

uploaded_file = st.file_uploader("Upload Clinical XLS/XLSX File", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # 1. Identify missing columns first
    existing_req_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    missing_from_schema = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing_from_schema:
        st.error(f"🚨 **CRITICAL ATTENTION REQUIRED:** The following columns are completely missing from the file: {', '.join(missing_from_schema)}")

    # 2. Analyze Nulls in existing columns
    null_counts = df[existing_req_cols].isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0]

    if not cols_with_nulls.empty:
        st.subheader("⚠️ Columns Needing Attention")
        
        # Create metric columns for a quick dashboard view
        cols = st.columns(len(cols_with_nulls))
        for idx, (col_name, count) in enumerate(cols_with_nulls.items()):
            cols[idx % len(cols)].metric(label=col_name, value=f"{count} Missing", delta="-Action Required", delta_color="inverse")

        # 3. Show the flagged data rows
        st.markdown("---")
        st.subheader("Row-Level Issues")
        st.write("The red cells below indicate missing values that must be filled:")
        
        # Filter to rows that have at least one null in the required columns
        error_df = df[df[existing_req_cols].isnull().any(axis=1)]
        
        # Display styled dataframe
        st.dataframe(
            error_df.style.highlight_null(color="#FF4B4B"), # Streamlit Red
            use_container_width=True
        )
        
        # Download button for the flagged report
        csv = error_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Attention List (CSV)", csv, "attention_required.csv", "text/csv")
        
    else:
        st.success("✅ Validation Passed: No missing data found in the monitored columns.")
        st.balloons()