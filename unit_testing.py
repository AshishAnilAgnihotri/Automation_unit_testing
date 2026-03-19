import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Clinical Data Auditor", layout="wide")

st.title("🛡️ Clinical Data Mandatory Field Auditor")
st.markdown("This tool validates 15 mandatory columns and maintains a detailed error log with row context.")

# The 15 Mandatory Columns
MANDATORY_COLUMNS = [
    "SITEID", "SUBJID", "VISITID", "VISITNAME", "VISITINDEX", 
    "FORMNAME", "SRECORD", "FORMREPEATKEY", "ITEMGROUPREPEATKEY", 
    "SITEMNEM", "SUBJGUID", "FORMID", "DATAPAGEID", "SRMODTM", "DOMAIN"
]

uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)

# UI for the Start Button
if "started" not in st.session_state:
    st.session_state.started = False

if st.button(" Start Validation", type="primary"):
    st.session_state.started = True

if uploaded_files and st.session_state.started:
    log_entries = []

    for uploaded_file in uploaded_files:
        # Read the CSV
        df = pd.read_csv(uploaded_file)
        file_name = uploaded_file.name
        
        # 1. Identify existing and missing columns
        existing_target_cols = [c for c in MANDATORY_COLUMNS if c in df.columns]
        missing_from_header = [c for c in MANDATORY_COLUMNS if c not in df.columns]

        # 2. Log missing headers
        for col in missing_from_header:
            log_entries.append({
                "File_Name": file_name,
                "CSV_Row": "N/A (Header)",
                "Error_Column": col,
                "Status": "MISSING COLUMN",
                "Details": "Column header not found in file"
            })

        # 3. Check for Nulls/Empty strings in the rows
        if existing_target_cols:
            # We iterate through the mandatory columns to find specific empty cells
            for col in existing_target_cols:
                # Find indices where value is null, "nan", or empty whitespace
                is_null = df[col].isnull() | (df[col].astype(str).str.strip().isin(['', 'nan', 'NaN', 'None']))
                error_rows = df[is_null]

                for idx, row in error_rows.iterrows():
                    # Create a dictionary for the log entry
                    entry = {
                        "File_Name": file_name,
                        "CSV_Row": idx + 2, # +2 for Excel/CSV line number
                        "Error_Column": col,
                        "Status": "EMPTY CELL",
                    }
                    # Add the actual data from the mandatory columns for context
                    for m_col in MANDATORY_COLUMNS:
                        entry[m_col] = row.get(m_col, "N/A")
                    
                    log_entries.append(entry)

    # --- LOG DISPLAY & DOWNLOAD ---
    if log_entries:
        log_df = pd.DataFrame(log_entries)
        
        # Reorder columns so File/Row/Error come first
        base_cols = ["File_Name", "CSV_Row", "Error_Column", "Status"]
        other_cols = [c for c in log_df.columns if c not in base_cols]
        log_df = log_df[base_cols + other_cols]

        st.error(f" Validation complete. {len(log_df)} issues identified.")
        
        st.subheader("Master Error Log (with Mandatory Field Data)")
        st.dataframe(log_df, use_container_width=True, hide_index=True)

        # Generate Downloadable CSV
        output = io.StringIO()
        log_df.to_csv(output, index=False)
        st.download_button(
            label=" Download Full Error Log",
            data=output.getvalue(),
            file_name=f"Clinical_Validation_Log_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        # st.balloons()
        st.success("  All mandatory fields in all files are populated.")

elif not uploaded_files and st.session_state.started:
    st.warning("Please upload files first.")