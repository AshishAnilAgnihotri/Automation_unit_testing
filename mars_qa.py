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
    if s == "" or s == "MISSING": return 0.0
    m = 1.0
    if s.endswith('K'): m = 1e3; s = s[:-1]
    elif s.endswith('M'): m = 1e6; s = s[:-1]
    elif s.endswith('B'): m = 1e9; s = s[:-1]
    try:
        return float(s) * m
    except ValueError:
        return 0.0

def extract_roi_lead(val):
    """Extracts the integer part before any : or . (e.g., 4.3 -> 4, 5:11 -> 5)."""
    if pd.isna(val) or str(val).strip() == "": return 0
    s = str(val).strip()
    match = re.search(r'^(\d+)', s)
    if match:
        return int(match.group(1))
    s_clean = re.sub(r'[^\d:.]', '', s)
    parts = re.split(r'[:.]', s_clean)
    try:
        return int(parts[0]) if parts[0] else 0
    except:
        return 0

def parse_val_2(val):
    v_str = str(val).upper().strip()
    if pd.isna(val) or v_str == "" or v_str in ["MISSING", "NAN", "NONE", "0", "0.0"]: return 0.0
    s = str(val).replace('$', '').replace(',', '').strip()
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0

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
            if len(df_a_raw.columns) < 7 or len(df_b_raw.columns) < 8:
                st.error("Audit failed: Source data columns missing.")
            else:
                max_r = max(len(df_a_raw), len(df_b_raw))
                final_a = df_a_raw.reindex(range(max_r)).fillna("0").map(clean_brackets)
                final_b = df_b_raw.reindex(range(max_r)).fillna("0").map(clean_brackets)

                style_a = pd.DataFrame('', index=final_a.index, columns=final_a.columns)
                style_b = pd.DataFrame('', index=final_b.index, columns=final_b.columns)
                
                all_rows, mismatch_count = [], 0
                compare_pairs = [(0, 0), (1, 1), (2, 2), (3, 4), (4, 3), (5, 6), (6, 5)]

                for r in range(max_r):
                    row_data = {}
                    row_has_mismatch = False
                    
                    for i1, i2 in compare_pairs:
                        s1, s2 = final_a.iloc[r, i1], final_b.iloc[r, i2]
                        n1, n2 = parse_fin(s1), parse_fin(s2)
                        diff_pct = abs(n1 - n2) / max(abs(n1), abs(n2)) if max(abs(n1), abs(n2)) != 0 else 0
                        
                        if diff_pct > 0.005:
                            row_has_mismatch = True
                            style_a.iloc[r, i1] = 'background-color: #4b1111; color: #ff4b4b;'
                            style_b.iloc[r, i2] = 'background-color: #4b1111; color: #ff4b4b;'

                    row_data["MATCH_STATUS"] = "MISMATCH" if row_has_mismatch else "MATCH"
                    if row_has_mismatch: mismatch_count += 1

                    for i1, i2 in compare_pairs:
                        row_data[f"F1_{final_a.columns[i1]}"] = final_a.iloc[r, i1]
                        row_data[f"F2_{final_b.columns[i2]}"] = final_b.iloc[r, i2]

                    va4, vb3 = parse_fin(final_a.iloc[r, 4]), parse_fin(final_b.iloc[r, 3])
                    va6, vb5 = parse_fin(final_a.iloc[r, 6]), parse_fin(final_b.iloc[r, 5])
                    
                    row_data["Streamlit ROI"] = int(round(va6 / va4)) if va4 != 0 else 0
                    row_data["MARS ROI"] = extract_roi_lead(final_b.iloc[r, 7])
                    row_data["Spent Diff"] = round(abs(va4 - vb3), 2)
                    row_data["Spent % Diff"] = f"{round((abs(va4-vb3)/va4*100), 2) if va4 != 0 else 0}%"
                    row_data["Sales Diff"] = round(abs(va6 - vb5), 2)
                    row_data["Sales % Diff"] = f"{round((abs(va6-vb5)/va6*100), 2) if va6 != 0 else 0}%"

                    all_rows.append(row_data)

                report_df = pd.DataFrame(all_rows)
                st.markdown('<div class="report-card"><h3>Financial Integrity Summary</h3></div>', unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Rows Processed", max_r)
                m2.metric("Mismatches", mismatch_count, delta_color="inverse")

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                    report_df.to_excel(wr, index=False, sheet_name='Audit')
                    wb, ws = wr.book, wr.sheets['Audit']
                    fmt_green = wb.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
                    fmt_red = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                    l_char = get_col_letter(len(report_df.columns)-1)
                    ws.conditional_format(f'A2:{l_char}{len(report_df)+1}', {'type': 'formula', 'criteria': '=$A2="MATCH"', 'format': fmt_green})
                    ws.conditional_format(f'A2:{l_char}{len(report_df)+1}', {'type': 'formula', 'criteria': '=$A2="MISMATCH"', 'format': fmt_red})
                
                buf.seek(0)
                m3.download_button("📥 Download Master Report", buf.getvalue(), "Financial_Audit.xlsx")

                v1, v2 = st.columns(2)
                v1.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
                v2.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)

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

        # 1. PROCESS FILE 1
        df_o1_raw['PRODUCT_NAME'] = df_o1_raw.iloc[:, 6].astype(str).str.strip().str.upper()
        df_o1_raw['UID_KEY'] = df_o1_raw.iloc[:, 9].astype(str).str.strip().str.upper()
        df_o1_raw = df_o1_raw[(df_o1_raw['PRODUCT_NAME'] != "") & (df_o1_raw['PRODUCT_NAME'] != "NAN") & (df_o1_raw['UID_KEY'] != "") & (df_o1_raw['UID_KEY'] != "NAN")].copy()
        df_o1_raw['UID'] = df_o1_raw['PRODUCT_NAME'] + "_" + df_o1_raw['UID_KEY']
        
        f1_nums = [11, 12, 13, 14, 15]
        for i in f1_nums: df_o1_raw.iloc[:, i] = df_o1_raw.iloc[:, i].apply(parse_val_2)
        f1_col_agg = [df_o1_raw.columns[i] for i in f1_nums if df_o1_raw.columns[i] not in ['PRODUCT_NAME', 'UID']]
        df_o1_clubbed = df_o1_raw.groupby(['PRODUCT_NAME', 'UID'])[f1_col_agg].sum().reset_index()

        # 2. PROCESS FILE 2
        df_o2_raw.iloc[:, 0] = df_o2_raw.iloc[:, 0].astype(str).str.strip().str.upper()
        df_o2_raw.iloc[:, 2] = df_o2_raw.iloc[:, 2].astype(str).str.strip().str.upper()
        
        # --- REFINED FILTERING LOGIC ---
        # 1. Exclude Empty/Null Cost Types
        # 2. Exclude rows containing the word "TOTAL" in the Cost Type (Column index 2)
        # 3. Exclude NAN product identifiers
        df_o2_filtered = df_o2_raw[
            (df_o2_raw.iloc[:, 0] != "") & (df_o2_raw.iloc[:, 0] != "NAN") & 
            (df_o2_raw.iloc[:, 2] != "") & (df_o2_raw.iloc[:, 2] != "NAN") &
            (~df_o2_raw.iloc[:, 2].str.contains("TOTAL", na=False))
        ].copy()
        
        df_o2_filtered['UID'] = df_o2_filtered.iloc[:, 0] + "_" + df_o2_filtered.iloc[:, 2]
        orig_roi_col_name = df_o2_raw.columns[7] if len(df_o2_raw.columns) > 7 else "ROI"

        if st.button("RUN FULL AGGREGATED COMPARISON"):
            merged = pd.merge(df_o1_clubbed, df_o2_filtered, on='UID', how='outer', suffixes=('_F1', '_F2')).fillna(0)
            actual_roi_col = next((c for c in merged.columns if c == orig_roi_col_name or c == f"{orig_roi_col_name}_F2"), None)
            
            audit_rows_2, mismatch_count_2 = [], 0

            for _, row in merged.iterrows():
                uid_val = str(row['UID'])
                if any(x in uid_val for x in ["NAN", "NONE"]) or uid_val.endswith("_"):
                    continue

                res = {"OVERALL_MATCH": "MATCH", "UNIQUE_ID": uid_val}
                
                def compare_vals(v1, v2):
                    n1, n2 = parse_val_2(v1), parse_val_2(v2)
                    diff = abs(n1 - n2)
                    mx = max(abs(n1), abs(n2))
                    tol = max(0.05 * mx, 0.01) if mx != 0 else 0.01
                    return (f"{n1:,.2f} | {n2:,.2f}", diff <= tol, n1, n2)

                s1, m1, _, _ = compare_vals(row.iloc[2], row.get('Historical Product Spend', 0))
                s2, m2, v1_spend_opt, v2_o_spend = compare_vals(row.iloc[3], row.get('Optimized Product Spend', 0))
                s3, m3, _, _ = compare_vals(row.iloc[4], row.get('Historical Impactable Sales', 0))
                s4, m4, v1_sales_opt, v2_o_sales = compare_vals(row.iloc[5], row.get('Optimized Impactable Sales', 0))
                
                spend_diff_raw = (v2_o_spend - v1_spend_opt)
                streamlit_roi = int(round(v1_sales_opt / v1_spend_opt)) if v1_spend_opt != 0 else 0
                raw_roi = row.get(actual_roi_col, "0") if actual_roi_col else "0"
                mars_roi_extracted = extract_roi_lead(raw_roi)

                res.update({
                    "Hist Spend (F1|F2)": s1, 
                    "Opt Spend (F1|F2)": s2,
                    "Hist Sales (F1|F2)": s3, 
                    "Opt Sales (F1|F2)": s4,
                    "file 1": v1_spend_opt,
                    "file 2": v2_o_spend,
                    "Optimized product Spend": v2_o_spend,
                    "Optimized Impactable Sales": v2_o_sales,
                    "Percentage Product spend Difference": round(spend_diff_raw, 2),
                    "streamlit ROI": streamlit_roi,
                    "MARS ROI": mars_roi_extracted
                })

                if not all([m1, m2, m3, m4]):
                    res["OVERALL_MATCH"] = "MISMATCH"
                    mismatch_count_2 += 1
                audit_rows_2.append(res)

            report_df2 = pd.DataFrame(audit_rows_2)
            st.markdown('<div class="report-card"><h3>Aggregated Analysis Summary</h3></div>', unsafe_allow_html=True)
            k1, k2, k3 = st.columns(3)
            k1.metric("Rows Processed", len(report_df2))
            k2.metric("Mismatches", mismatch_count_2, delta_color="inverse")

            buf2 = io.BytesIO()
            with pd.ExcelWriter(buf2, engine='xlsxwriter') as wr2:
                report_df2.to_excel(wr2, index=False, sheet_name='Comparison')
                wb2, ws2 = wr2.book, wr2.sheets['Comparison']
                green2, red2 = wb2.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}), wb2.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                l_char2 = get_col_letter(len(report_df2.columns)-1)
                ws2.conditional_format(f'A2:{l_char2}{len(report_df2)+1}', {'type': 'formula', 'criteria': '=$A2="MATCH"', 'format': green2})
                ws2.conditional_format(f'A2:{l_char2}{len(report_df2)+1}', {'type': 'formula', 'criteria': '=$A2="MISMATCH"', 'format': red2})

            buf2.seek(0)
            k3.download_button("📥 Download Master Report", buf2.getvalue(), "General_Data_Audit.xlsx")

            st.dataframe(report_df2.style.apply(lambda r: ['background-color: #4b1111' if r.OVERALL_MATCH == "MISMATCH" else '' for _ in r], axis=1), use_container_width=True)