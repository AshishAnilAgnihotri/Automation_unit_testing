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
    if pd.isna(val) or str(val).strip() == "": return ""
    return re.sub(r'[\(\[].*?[\)\]]', '', str(val)).strip()

def parse_fin(val):
    s = clean_brackets(val).upper().replace('$', '').replace(',', '')
    if s == "" or s in ["MISSING", "NAN", "NONE"]: return 0.0
    m = 1.0
    if s.endswith('K'): m = 1e3; s = s[:-1]
    elif s.endswith('M'): m = 1e6; s = s[:-1]
    elif s.endswith('B'): m = 1e9; s = s[:-1]
    try:
        return float(s) * m
    except ValueError:
        return 0.0

def extract_roi_lead(val):
    if pd.isna(val) or str(val).strip() == "": return 0
    s = str(val).strip()
    match = re.search(r'^(\d+)', s)
    if match: return int(match.group(1))
    return 0

def parse_val_2(val):
    v_str = str(val).upper().strip()
    if pd.isna(val) or v_str in ["", "MISSING", "NAN", "NONE", "0", "0.0"]: return 0.0
    s = str(val).replace('$', '').replace(',', '').strip()
    try: return round(float(s), 2)
    except ValueError: return 0.0

def get_col_letter(n):
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
        df_a_raw = pd.read_excel(file_a, dtype=str) if file_a.name.endswith('xlsx') else pd.read_csv(file_a, dtype=str)
        df_b_raw = pd.read_excel(file_b, dtype=str) if file_b.name.endswith('xlsx') else pd.read_csv(file_b, dtype=str)
        
        df_a_raw.columns = [str(c).strip().upper() for c in df_a_raw.columns]
        df_b_raw.columns = [str(c).strip().upper() for c in df_b_raw.columns]

        if st.button("RUN FINANCIAL COMPARISON"):
            max_r = max(len(df_a_raw), len(df_b_raw))
            final_a = df_a_raw.reindex(range(max_r)).fillna("0").map(clean_brackets)
            final_b = df_b_raw.reindex(range(max_r)).fillna("0").map(clean_brackets)
            
            style_a = pd.DataFrame('', index=final_a.index, columns=final_a.columns)
            style_b = pd.DataFrame('', index=final_b.index, columns=final_b.columns)
            
            all_rows, mismatch_count = [], 0
            STRICT_THRESHOLD = 0.05 # 0.05%
            compare_pairs = [(0, 0), (1, 1), (2, 2), (3, 4), (4, 3), (5, 6), (6, 5)]

            for r in range(max_r):
                row_has_mismatch = False
                for i1, i2 in compare_pairs:
                    n1, n2 = parse_fin(final_a.iloc[r, i1]), parse_fin(final_b.iloc[r, i2])
                    diff_pct = abs(n1 - n2) / max(abs(n1), abs(n2)) if max(abs(n1), abs(n2)) != 0 else 0
                    if diff_pct > STRICT_THRESHOLD:
                        row_has_mismatch = True
                        style_a.iloc[r, i1] = 'background-color: #4b1111; color: #ff4b4b;'
                        style_b.iloc[r, i2] = 'background-color: #4b1111; color: #ff4b4b;'

                va4, vb3 = parse_fin(final_a.iloc[r, 4]), parse_fin(final_b.iloc[r, 3])
                va6, vb5 = parse_fin(final_a.iloc[r, 6]), parse_fin(final_b.iloc[r, 5])
                sales_diff_pct = (abs(va6 - vb5) / va6) if va6 != 0 else 0
                if sales_diff_pct > STRICT_THRESHOLD: row_has_mismatch = True

                row_data = {"MATCH_STATUS": "MISMATCH" if row_has_mismatch else "MATCH"}
                if row_has_mismatch: mismatch_count += 1
                
                for i1, i2 in compare_pairs:
                    row_data[f"F1_{final_a.columns[i1]}"] = final_a.iloc[r, i1]
                    row_data[f"F2_{final_b.columns[i2]}"] = final_b.iloc[r, i2]

                row_data["Sales % Diff"] = f"{round(sales_diff_pct * 100, 2)}%"
                all_rows.append(row_data)

            report_df = pd.DataFrame(all_rows)
            st.markdown('<div class="report-card"><h3>Financial Integrity Summary</h3></div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Rows Processed", max_r)
            m2.metric("Mismatches (>0.05%)", mismatch_count)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                report_df.to_excel(wr, index=False, sheet_name='Audit')
                wb, ws = wr.book, wr.sheets['Audit']
                fmt_red = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                ws.conditional_format(f'A2:{get_col_letter(len(report_df.columns)-1)}{len(report_df)+1}', {'type': 'formula', 'criteria': '=$A2="MISMATCH"', 'format': fmt_red})
            buf.seek(0)
            m3.download_button("📥 Download Financial Report", buf.getvalue(), "Financial_Audit.xlsx")

            # RE-ADDED SIDE BY SIDE VIEW
            st.markdown("### 🔍 Source File Comparison")
            v1, v2 = st.columns(2)
            v1.caption("File 1 (Streamlit)")
            v1.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
            v2.caption("File 2 (Mars)")
            v2.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)

            st.markdown("### 📋 Final Export Preview")
            st.dataframe(report_df.style.apply(lambda r: ['background-color: #4b1111' if r.MATCH_STATUS == "MISMATCH" else '' for _ in r], axis=1), use_container_width=True)

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

        df_o1_raw['PRODUCT_NAME'] = df_o1_raw.iloc[:, 6].astype(str).str.strip().str.upper()
        df_o1_raw['UID_KEY'] = df_o1_raw.iloc[:, 9].astype(str).str.strip().str.upper()
        df_o1_raw = df_o1_raw[(df_o1_raw['PRODUCT_NAME'] != "NAN") & (df_o1_raw['UID_KEY'] != "NAN")].copy()
        df_o1_raw['UID'] = df_o1_raw['PRODUCT_NAME'] + "_" + df_o1_raw['UID_KEY']
        
        f1_nums = [11, 12, 13, 14, 15]
        for i in f1_nums: df_o1_raw.iloc[:, i] = df_o1_raw.iloc[:, i].apply(parse_val_2)
        f1_col_names = [df_o1_raw.columns[i] for i in f1_nums]
        df_o1_clubbed = df_o1_raw.groupby('UID')[f1_col_names].sum().reset_index()

        df_o2_raw.iloc[:, 0] = df_o2_raw.iloc[:, 0].astype(str).str.strip().str.upper()
        df_o2_raw.iloc[:, 2] = df_o2_raw.iloc[:, 2].astype(str).str.strip().str.upper()
        df_o2_filtered = df_o2_raw[(df_o2_raw.iloc[:, 0] != "NAN") & (~df_o2_raw.iloc[:, 2].str.contains("TOTAL", na=False))].copy()
        df_o2_filtered['UID'] = df_o2_filtered['UID'] = df_o2_filtered.iloc[:, 0] + "_" + df_o2_filtered.iloc[:, 2]

        if st.button("RUN FULL AGGREGATED COMPARISON"):
            merged = pd.merge(df_o1_clubbed, df_o2_filtered, on='UID', how='outer', suffixes=('_F1', '_F2')).fillna("0")
            audit_rows_2, mismatch_count_2 = [], 0
            STRICT_THRESHOLD = 0.05 # 0.05%

            for _, row in merged.iterrows():
                uid_val = str(row['UID'])
                if any(x in uid_val for x in ["NAN", "NONE"]) or uid_val.endswith("_"): continue
                
                f1_actual_sales = parse_val_2(row.iloc[3])
                f2_hist_sales = parse_fin(row.get('Historical Impactable Sales', "0"))
                f1_imp_sales = parse_val_2(row.iloc[4])
                f2_opt_sales = parse_fin(row.get('Optimized Impactable Sales', "0"))
                f1_opt_spend = parse_val_2(row.iloc[2])
                f2_opt_spend = parse_fin(row.get('Optimized Product Spend', "0"))

                s1_diff = (abs(f1_actual_sales - f2_hist_sales) / f1_actual_sales) if f1_actual_sales != 0 else 0
                s2_diff = (abs(f1_imp_sales - f2_opt_sales) / f1_imp_sales) if f1_imp_sales != 0 else 0
                sp_diff = (abs(f1_opt_spend - f2_opt_spend) / f1_opt_spend) if f1_opt_spend != 0 else 0

                is_mismatch = any(d > STRICT_THRESHOLD for d in [s1_diff, s2_diff, sp_diff])

                res = {
                    "OVERALL_MATCH": "MISMATCH" if is_mismatch else "MATCH",
                    "UNIQUE_ID": uid_val,
                    "F1_OPTIMIZED_PRODUCT_SPEND": f1_opt_spend,
                    "F2_OPTIMIZED_PRODUCT_SPEND": row.get('Optimized Product Spend', "0"),
                    "F1_ACTUAL_SALES": f1_actual_sales,
                    "F2_HISTORICAL_SALES": row.get('Historical Impactable Sales', "0"),
                    "F1_IMPACTABLE_SALES": f1_imp_sales,
                    "F2_OPTIMIZED_SALES": row.get('Optimized Impactable Sales', "0"),
                    "Streamlit ROI": int(round(f1_imp_sales / f1_opt_spend)) if f1_opt_spend != 0 else 0,
                    "MARS ROI": extract_roi_lead(row.get(df_o2_raw.columns[7], "0")),
                    "Sales % Diff": f"{round(s2_diff * 100, 2)}%"
                }

                if is_mismatch: mismatch_count_2 += 1
                audit_rows_2.append(res)

            report_df2 = pd.DataFrame(audit_rows_2)
            st.markdown('<div class="report-card"><h3>Aggregated Analysis Summary</h3></div>', unsafe_allow_html=True)
            k1, k2, k3 = st.columns(3)
            k1.metric("Unique Records", len(report_df2))
            k2.metric("Mismatches (>0.05%)", mismatch_count_2)

            buf2 = io.BytesIO()
            with pd.ExcelWriter(buf2, engine='xlsxwriter') as wr2:
                report_df2.to_excel(wr2, index=False, sheet_name='Comparison')
                wb2, ws2 = wr2.book, wr2.sheets['Comparison']
                fmt_red2 = wb2.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                l_char2 = get_col_letter(len(report_df2.columns)-1)
                ws2.conditional_format(f'A2:{l_char2}{len(report_df2)+1}', {'type': 'formula', 'criteria': '=$A2="MISMATCH"', 'format': fmt_red2})
            buf2.seek(0)
            k3.download_button("📥 Download Aggregated Report", buf2.getvalue(), "Aggregated_Audit.xlsx")
            
            # SIDE BY SIDE VIEW FOR TAB 2
            st.markdown("### 🔍 Aggregated File Data")
            c1_view, c2_view = st.columns(2)
            c1_view.caption("Aggregated File 1 (Row Wise)")
            c1_view.dataframe(df_o1_clubbed, use_container_width=True)
            c2_view.caption("Filtered File 2 (Grouped Data)")
            c2_view.dataframe(df_o2_filtered, use_container_width=True)

            st.markdown("### 📋 Final Export Preview")
            st.dataframe(report_df2.style.apply(lambda r: ['background-color: #4b1111' if r.OVERALL_MATCH == "MISMATCH" else '' for _ in r], axis=1), use_container_width=True)