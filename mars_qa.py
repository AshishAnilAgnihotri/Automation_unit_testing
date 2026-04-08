import streamlit as st
import pandas as pd
import re
import io
import math

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Data Comparison Tool", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .main { background: #0d1117; color: #c9d1d9; }
    .stButton>button {
        background: linear-gradient(90deg, #1f6feb 0%, #58a6ff 100%);
        color: white; border-radius: 50px; height: 3.5em; font-weight: bold;
        border: none; transition: all 0.4s; width: 100%;
    }
    .stMetric { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .report-card {
        background: #161b22; padding: 30px; border-radius: 20px; border: 1px solid #30363d;
        text-align: center; margin-bottom: 25px; border-top: 5px solid #58a6ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SHARED UTILITIES ---
def clean_brackets(val):
    """Removes content inside brackets and parentheses."""
    if pd.isna(val) or str(val).strip() == "": return ""
    return re.sub(r'[\(\[].*?[\)\]]', '', str(val)).strip()

def parse_fin(val):
    """Shorthand Financial Parser for Tab 1 (K, M, B support)."""
    s = clean_brackets(val).upper().replace('$', '').replace(',', '')
    if s == "" or s == "MISSING": return 0.0
    m = 1.0
    if s.endswith('K'): m = 1e3; s = s[:-1]
    elif s.endswith('M'): m = 1e6; s = s[:-1]
    elif s.endswith('B'): m = 1e9; s = s[:-1]
    try:
        return float(s) * m
    except ValueError:
        return 0.0

def extract_ratio_lead(val):
    """Extracts numeric value before colon and rounds to whole number."""
    s = str(val).strip()
    if s == "" or s.lower() == "nan": return 0
    head = s.split(':', 1)[0]
    clean_head = re.sub(r'[^0-9.]', '', head)
    try:
        return int(round(float(clean_head))) if clean_head else 0
    except ValueError:
        return 0

def parse_val_2(val):
    """Clean and convert to float for Tab 2, rounding to 2 decimals."""
    if pd.isna(val) or str(val).strip() == "" or str(val).upper() == "MISSING": return 0.0
    s = str(val).replace('$', '').replace(',', '').strip()
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0

def get_col_letter(n):
    """Helper to convert column index to Excel letter (e.g. 0 -> A, 27 -> AB)."""
    string = ""
    while n >= 0:
        n, r = divmod(n, 26)
        string = chr(65 + r) + string
        n -= 1
    return string

# --- APP LAYOUT ---
st.title("🛡️ Data Comparison Center")
tab1, tab2 = st.tabs(["💰 Financial Reconciliation", "📊 General Data Comparison"])

# ---------------------------------------------------------
# TAB 1: FINANCIAL RECONCILIATION
# ---------------------------------------------------------
with tab1:
    st.subheader("Financial Integrity Audit")
    u1, u2 = st.columns(2)
    file_a = u1.file_uploader("📂 Streamlit Optimization Data(File 1)", type=['xlsx', 'csv'], key="t1_fa")
    file_b = u2.file_uploader("📂 Mars Optimization Data(File 2)", type=['xlsx', 'csv'], key="t1_fb")

    if file_a and file_b:
        df_a = pd.read_excel(file_a, dtype=str) if file_a.name.endswith('xlsx') else pd.read_csv(file_a, dtype=str)
        df_b = pd.read_excel(file_b, dtype=str) if file_b.name.endswith('xlsx') else pd.read_csv(file_b, dtype=str)
        
        df_a.columns = [str(c).strip().upper() for c in df_a.columns]
        df_b.columns = [str(c).strip().upper() for c in df_b.columns]

        if st.button("RUN FINANCIAL COMPARISON"):
            if len(df_a.columns) < 7 or len(df_b.columns) < 8:
                st.error("Audit failed: Ledger A needs at least 7 columns and Ledger B needs 8 columns.")
            else:
                max_r = max(len(df_a), len(df_b))
                final_a = df_a.reindex(range(max_r)).fillna("MISSING").map(clean_brackets)
                final_b = df_b.reindex(range(max_r)).fillna("MISSING").map(clean_brackets)

                style_a = pd.DataFrame('', index=final_a.index, columns=final_a.columns)
                style_b = pd.DataFrame('', index=final_b.index, columns=final_b.columns)
                all_rows, mismatch_count = [], 0
                
                compare_pairs = [(0, 0), (1, 1), (2, 2), (3, 4), (4, 3), (5, 6), (6, 5)]
                f1_cols, f2_cols = list(final_a.columns), list(final_b.columns)

                for r in range(max_r):
                    row_diff, row_status = False, "MATCH"
                    row_data = {}

                    # Check mismatches and style UI
                    for i1, i2 in compare_pairs:
                        if i1 >= len(f1_cols) or i2 >= len(f2_cols): continue
                        c1, c2 = f1_cols[i1], f2_cols[i2]
                        s1, s2 = final_a.at[r, c1], final_b.at[r, c2]
                        n1, n2 = parse_fin(s1), parse_fin(s2)
                        
                        lvl = 0
                        if s1 != s2 and n1 != n2:
                            d = abs(n1 - n2) / max(abs(n1), abs(n2)) if max(abs(n1), abs(n2)) != 0 else 0
                            lvl = 1 if d <= 0.005 else 2

                        if lvl > 0:
                            row_diff = True
                            if lvl == 2: row_status = "MISMATCH"
                            elif lvl == 1 and row_status != "MISMATCH": row_status = "ROUNDED"
                            
                            color = 'rgba(255, 75, 75, 0.15)' if lvl == 2 else 'rgba(251, 255, 0, 0.1)'
                            style_a.at[r, c1] = f'background-color: {color}; color: {"#ff4b4b" if lvl == 2 else "#fbff00"};'
                            style_b.at[r, c2] = f'background-color: {color}; color: {"#ff4b4b" if lvl == 2 else "#fbff00"};'

                    row_data["MATCH_STATUS"] = row_status
                    for i1, i2 in compare_pairs:
                        if i1 < len(f1_cols) and i2 < len(f2_cols):
                            row_data[f"F1_{f1_cols[i1]}"] = final_a.at[r, f1_cols[i1]]
                            row_data[f"F2_{f2_cols[i2]}"] = final_b.at[r, f2_cols[i2]]

                    # Financial Math & Metrics
                    va4, vb3 = parse_fin(final_a.iloc[r, 4]), parse_fin(final_b.iloc[r, 3])
                    va6, vb5 = parse_fin(final_a.iloc[r, 6]), parse_fin(final_b.iloc[r, 5])
                    
                    row_data["Streamlit ROI"] = int(round(va6 / va4)) if va4 != 0 else 0
                    row_data["MARS ROI"] = extract_ratio_lead(final_b.iloc[r, 7])
                    row_data["Spent Diff"] = round(abs(va4 - vb3), 2)
                    row_data["Spent % Diff"] = f"{round((abs(va4-vb3)/va4*100), 2) if va4 != 0 else 0}%"
                    row_data["Sales Diff"] = round(abs(va6 - vb5), 2)
                    row_data["Sales % Diff"] = f"{round((abs(va6-vb5)/va6*100), 2) if va6 != 0 else 0}%"

                    if row_diff: mismatch_count += 1
                    all_rows.append(row_data)

                report_df = pd.DataFrame(all_rows)
                st.markdown('<div class="report-card"><h3>Comparison Result Summary</h3></div>', unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Processed Rows", max_r); m2.metric("Mismatches", mismatch_count, delta_color="inverse")

                # Master Excel Export with Full Row Highlighting
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                    report_df.to_excel(wr, index=False, sheet_name='Audit')
                    wb, ws = wr.book, wr.sheets['Audit']
                    fmt_green = wb.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
                    fmt_red = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                    fmt_yellow = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
                    
                    l_char = get_col_letter(len(report_df.columns)-1)
                    ws.conditional_format(f'A2:{l_char}{len(report_df)+1}', {'type': 'formula', 'criteria': '=$A2="MATCH"', 'format': fmt_green})
                    ws.conditional_format(f'A2:{l_char}{len(report_df)+1}', {'type': 'formula', 'criteria': '=$A2="MISMATCH"', 'format': fmt_red})
                    ws.conditional_format(f'A2:{l_char}{len(report_df)+1}', {'type': 'formula', 'criteria': '=$A2="ROUNDED"', 'format': fmt_yellow})
                
                buf.seek(0)
                m3.download_button("📥 Download Master Report", buf.getvalue(), "Financial_Audit.xlsx")

                st.markdown("### 📄 Source Data Comparison (Separate Display)")
                d1, d2 = st.columns(2)
                d1.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
                d2.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)

# ---------------------------------------------------------
# TAB 2: GENERAL DATA COMPARISON
# ---------------------------------------------------------
with tab2:
    st.subheader("Aggregated Data Reconciliation")
    c1, c2 = st.columns(2)
    other_a = c1.file_uploader("📂 Row wise data (File 1)", type=['xlsx', 'csv'], key="t2_fa")
    other_b = c2.file_uploader("📂 Grouped Data (File 2)", type=['xlsx', 'csv'], key="t2_fb")
    
    if other_a and other_b:
        df_o1_raw = pd.read_excel(other_a, dtype=str) if other_a.name.endswith('xlsx') else pd.read_csv(other_a, dtype=str)
        df_o2_raw = pd.read_excel(other_b, dtype=str) if other_b.name.endswith('xlsx') else pd.read_csv(other_b, dtype=str)

        # File 1: Group and Aggregation
        df_o1_raw['PRODUCT_NAME'] = df_o1_raw.iloc[:, 6].astype(str).str.strip().str.upper()
        df_o1_raw['UID_KEY'] = df_o1_raw.iloc[:, 9].astype(str).str.strip().str.upper()
        df_o1_raw['UID'] = df_o1_raw['PRODUCT_NAME'] + "_" + df_o1_raw['UID_KEY']
        
        f1_num_idxs = [11, 12, 13, 14, 15]
        for i in f1_num_idxs: 
            df_o1_raw.iloc[:, i] = df_o1_raw.iloc[:, i].apply(parse_val_2)
        
        f1_col_names = [df_o1_raw.columns[i] for i in f1_num_idxs]
        df_o1_clubbed = df_o1_raw.groupby(['PRODUCT_NAME', 'UID'])[f1_col_names].sum().reset_index()

        # File 2: Process and UID sync (Fixed str.upper logic)
        df_o2_filtered = df_o2_raw[df_o2_raw.iloc[:, 2].astype(str).str.strip() != ""].copy()
        df_o2_filtered['UID'] = df_o2_filtered.iloc[:, 0].astype(str).str.strip().str.upper() + "_" + df_o2_filtered.iloc[:, 2].astype(str).str.strip().str.upper()

        if st.button("RUN FULL AGGREGATED COMPARISON"):
            merged = pd.merge(df_o1_clubbed, df_o2_filtered, on='UID', how='outer', suffixes=('_F1', '_F2'))
            audit_rows_2, mismatch_count_2 = [], 0

            for _, row in merged.iterrows():
                res = {"OVERALL_MATCH": "MATCH", "UNIQUE_ID": row['UID']}
                
                def compare_vals(v1, v2):
                    n1, n2 = parse_val_2(v1), parse_val_2(v2)
                    diff = abs(n1 - n2)
                    mx = max(abs(n1), abs(n2))
                    tol = max(0.005 * mx, 0.01) if mx != 0 else 0.01
                    return (f"{n1:,.2f} | {n2:,.2f}", True) if diff <= tol else (f"{n1:,.2f} | {n2:,.2f}", False)

                # Execute Comparisons
                s1, m1 = compare_vals(row.iloc[2], row.get('Historical Product Spend', 0))
                s2, m2 = compare_vals(row.iloc[3], row.get('Optimized Product Spend', 0))
                s3, m3 = compare_vals(row.iloc[4], row.get('Historical Impactable Sales', 0))
                s4, m4 = compare_vals(row.iloc[5], row.get('Optimized Impactable Sales', 0))
                
                target_roi = extract_ratio_lead(row.iloc[12]) if len(row) > 12 else 0

                res.update({
                    "Hist Spend (F1|F2)": s1, "Opt Spend (F1|F2)": s2,
                    "Hist Sales (F1|F2)": s3, "Opt Sales (F1|F2)": s4,
                    "Target ROI": target_roi
                })

                if not all([m1, m2, m3, m4]):
                    res["OVERALL_MATCH"] = "MISMATCH"
                    mismatch_count_2 += 1
                audit_rows_2.append(res)

            report_df2 = pd.DataFrame(audit_rows_2)
            st.markdown('<div class="report-card"><h3>Aggregated Result Summary</h3></div>', unsafe_allow_html=True)
            k1, k2, k3 = st.columns(3)
            k1.metric("Processed Records", len(report_df2)); k2.metric("Mismatches", mismatch_count_2, delta_color="inverse")

            # Tab 2 Export with Full Row Highlighting
            buf2 = io.BytesIO()
            with pd.ExcelWriter(buf2, engine='xlsxwriter') as wr2:
                report_df2.to_excel(wr2, index=False, sheet_name='Comparison')
                wb2, ws2 = wr2.book, wr2.sheets['Comparison']
                green2, red2 = wb2.add_format({'bg_color': '#C6EFCE'}), wb2.add_format({'bg_color': '#FFC7CE'})
                l_char2 = get_col_letter(len(report_df2.columns)-1)
                ws2.conditional_format(f'A2:{l_char2}{len(report_df2)+1}', {'type': 'formula', 'criteria': '=$A2="MISMATCH"', 'format': red2})

            buf2.seek(0)
            k3.download_button("📥 Download Aggregated Report", buf2.getvalue(), "Aggregated_Comparison.xlsx")
            st.dataframe(report_df2.style.apply(lambda r: ['background-color: #4b1111' if r.OVERALL_MATCH == "MISMATCH" else '' for _ in r], axis=1), use_container_width=True)