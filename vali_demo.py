import streamlit as st
import pandas as pd
from io import BytesIO

# 1. Page Configuration
st.set_page_config(page_title="Clinical Data Gap Finder", layout="wide")

def main():
    # Specific File Names
    FILE_A_NAME = "PROD-Study Build-ClinicalTargetDEL"
    FILE_B_NAME = "PROD-PRD-ClinicalTargetDEL"

    st.title("📂 Clinical Target Comparison (A ➔ B)")
    st.markdown(f"Comparing **{FILE_A_NAME}** against **{FILE_B_NAME}** with full data sanitization.")

    # 2. Sidebar for File Uploads
    st.sidebar.header("Upload Settings")
    file_a = st.sidebar.file_uploader(f"Upload {FILE_A_NAME}", type=["csv"])
    file_b = st.sidebar.file_uploader(f"Upload {FILE_B_NAME}", type=["csv"])

    if file_a and file_b:
        # Load Data
        df_a_raw = pd.read_csv(file_a, header=0)
        df_b_raw = pd.read_csv(file_b, header=0)

        key_cols = ['Domain*', 'Variable Name*']

        # 3. Validation
        if all(col in df_a_raw.columns for col in key_cols) and all(col in df_b_raw.columns for col in key_cols):
            
            # 4. DATA SANITIZATION PIPELINE (Strip -> Upper)
            # This ensures "  dm  " matches "DM"
            for col in key_cols:
                # File A
                df_a_raw[col] = df_a_raw[col].astype(str).str.strip().str.upper()
                # File B
                df_b_raw[col] = df_b_raw[col].astype(str).str.strip().str.upper()

            # 5. Deduplication (Unique Baseline for File A)
            df_a_unique = df_a_raw.drop_duplicates(subset=key_cols).copy()
            
            # 6. One-Way Comparison Logic (Left Join A -> B)
            # We only look for A's keys in B
            comparison = pd.merge(
                df_a_unique, 
                df_b_raw[key_cols].drop_duplicates(), 
                on=key_cols, 
                how='left', 
                indicator=True
            )

            # 7. Filter for Missing Records
            # 'left_only' means it exists in A but was not found in B
            missing_df = comparison[comparison['_merge'] == 'left_only'].copy()
            
            # Final deduplication to ensure the count is exactly the unique gap (e.g., 198)
            export_df = missing_df.drop_duplicates(subset=key_cols).drop(columns=['_merge'])
            
            # Add Tracking Metadata
            export_df['Found In File'] = FILE_A_NAME
            export_df['Missing From File'] = FILE_B_NAME

            # 8. UI Summary Metrics
            st.divider()
            col1, col2, col3 = st.columns(3)
            
            col1.metric(f"Unique Keys ({FILE_A_NAME})", len(df_a_unique))
            col2.metric(f"Unique Keys ({FILE_B_NAME})", len(df_b_raw[key_cols].drop_duplicates()))
            # This shows the strictly cleaned A -> B gap
            col3.metric("A ➔ B Gap Count", len(export_df), delta_color="inverse")

            # 9. Results Table and Download
            if not export_df.empty:
                st.subheader(f"📋 Missing Unique Records ({len(export_df)})")
                st.dataframe(export_df, use_container_width=True)

                # Export to CSV
                csv_data = export_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download Report ({len(export_df)} Records)",
                    data=csv_data,
                    file_name=f"Missing_from_{FILE_B_NAME}.csv",
                    mime="text/csv"
                )
            else:
                st.balloons()
                st.success(f"✅ Comparison complete! All unique records in {FILE_A_NAME} were found in {FILE_B_NAME}.")
        
        else:
            st.error(f"Required columns {key_cols} not found. Please check CSV headers.")
    else:
        st.info("Please upload both CSV files to start the sanitized comparison.")

if __name__ == "__main__":
    main()