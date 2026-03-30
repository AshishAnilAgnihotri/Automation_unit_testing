import streamlit as st
import pandas as pd
import re
import io

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Audit Command Center", layout="wide", page_icon="🛡️")

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
    """Shorthand Financial Parser for Tab 1 (K, M, B support)."""
    s = clean_brackets(val).upper().replace('$', '').replace(',', '')
    if s == "" or s == "MISSING": return 0.0
    m = 1.0
    if s.endswith('K'): m = 1e3; s = s[:-1]
    elif s.endswith('M'): m = 1e6; s = s[:-1]
    elif s.endswith('B'): m = 1e9; s = s[:-1]
    try: return float(s) * m
    except ValueError: return 0.0

def parse_val_2(val):
    """Clean and convert to float for Tab 2, rounding to 2 decimals."""
    if pd.isna(val) or str(val).strip() == "" or str(val).upper() == "MISSING": return 0.0
    s = str(val).replace('$', '').replace(',', '').strip()
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0

# --- APP LAYOUT ---
st.title("🛡️ Audit Command Center")
tab1, tab2 = st.tabs(["💰 Financial Reconciliation", "📊 General Data Comparison"])

# ---------------------------------------------------------
# TAB 1: FINANCIAL RECONCILIATION
# ---------------------------------------------------------
with tab1:
    st.subheader("Financial Audit Mode")
    u1, u2 = st.columns(2)
    file_a = u1.file_uploader("📂 Ledger A", type=['xlsx', 'csv'], key="t1_fa")
    file_b = u2.file_uploader("📂 Ledger B", type=['xlsx', 'csv'], key="t1_fb")

    if file_a and file_b:
        df_a = pd.read_excel(file_a, dtype=str) if file_a.name.endswith('xlsx') else pd.read_csv(file_a, dtype=str)
        df_b = pd.read_excel(file_b, dtype=str) if file_b.name.endswith('xlsx') else pd.read_csv(file_b, dtype=str)
        
        df_a.columns = [str(c).strip().upper() for c in df_a.columns]
        df_b.columns = [str(c).strip().upper() for c in df_b.columns]
        common = [c for c in df_a.columns if c in df_b.columns]

        if st.button("RUN FINANCIAL AUDIT"):
            max_r = max(len(df_a), len(df_b))
            final_a = df_a.reindex(range(max_r)).fillna("MISSING")
            final_b = df_b[common].reindex(range(max_r)).fillna("MISSING")

            for col in common:
                final_a[col] = final_a[col].apply(clean_brackets)
                final_b[col] = final_b[col].apply(clean_brackets)

            style_a = pd.DataFrame('', index=final_a.index, columns=final_a.columns)
            style_b = pd.DataFrame('', index=final_b.index, columns=final_b.columns)
            all_rows = []
            mismatch_count = 0
            
            for r in range(max_r):
                row_diff = False
                for col in common:
                    s1, s2 = final_a.at[r, col], final_b.at[r, col]
                    n1, n2 = parse_fin(s1), parse_fin(s2)
                    lvl = 0
                    if s1 != s2:
                        if n1 == n2: lvl = 0 
                        else:
                            d = abs(n1 - n2) / max(abs(n1), abs(n2)) if max(abs(n1), abs(n2)) != 0 else 0
                            lvl = 1 if d <= 0.005 else 2

                    if lvl > 0:
                        row_diff = True
                        color = 'rgba(255, 75, 75, 0.15)' if lvl == 2 else 'rgba(251, 255, 0, 0.1)'
                        style_a.at[r, col] = f'background-color: {color}; color: {"#ff4b4b" if lvl == 2 else "#fbff00"};'
                        style_b.at[r, col] = f'background-color: {color}; color: {"#ff4b4b" if lvl == 2 else "#fbff00"};'

                if row_diff: mismatch_count += 1
                row_data = {f"A_{c}": final_a.at[r, c] for c in common}
                row_data.update({f"B_{c}": final_b.at[r, c] for c in common})
                row_data["MATCH_STATUS"] = "MISMATCH" if row_diff else "MATCH"
                
                num_col = next((c for c in common if any(k in c for k in ['AMOUNT', 'SPEND', 'COST', 'VALUE'])), common[-1])
                val_a, val_b = parse_fin(final_a.at[r, num_col]), parse_fin(final_b.at[r, num_col])
                abs_diff = abs(val_a - val_b)
                row_data["ABS_DIFF_AMOUNT"] = round(abs_diff, 2)
                row_data["PERCENTAGE_DIFF"] = f"{round((abs_diff / val_a * 100), 2) if val_a != 0 else 0}%"
                all_rows.append(row_data)

            st.markdown('<div class="report-card"><h3>Financial Integrity Summary</h3></div>', unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            s1.metric("Total Rows", max_r)
            s2.metric("Mismatches", mismatch_count, delta_color="inverse")
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: pd.DataFrame(all_rows).to_excel(wr, index=False)
            s3.download_button("📥 Download Master Report", buf.getvalue(), "Financial_Audit.xlsx")

            v1, v2 = st.columns(2)
            v1.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
            v2.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)

# ---------------------------------------------------------
# TAB 2: GENERAL DATA COMPARISON (Aggregated, Filtered & Product Select)
# ---------------------------------------------------------
with tab2:
    st.subheader("General Data Comparison Mode")
    c1, c2 = st.columns(2)
    other_a = c1.file_uploader("📂 Source (File 1)", type=['xlsx', 'csv'], key="t2_fa")
    other_b = c2.file_uploader("📂 Target (File 2)", type=['xlsx', 'csv'], key="t2_fb")
    
    if other_a and other_b:
        df_o1_raw = pd.read_excel(other_a).fillna(0) if other_a.name.endswith('xlsx') else pd.read_csv(other_a).fillna(0)
        df_o2_raw = pd.read_excel(other_b).fillna(0) if other_b.name.endswith('xlsx') else pd.read_csv(other_b).fillna(0)

        # 1. CLUBBING SOURCE (Sheet 1)
        df_o1_raw['PRODUCT_NAME'] = df_o1_raw.iloc[:, 6].astype(str).str.strip().str.upper()
        df_o1_raw['UID'] = df_o1_raw['PRODUCT_NAME'] + "_" + df_o1_raw.iloc[:, 9].astype(str).str.strip().str.upper()
        
        f1_num_indices = [11, 12, 13, 14, 15]
        f1_num_cols = [df_o1_raw.columns[i] for i in f1_num_indices]
        for col in f1_num_cols: df_o1_raw[col] = df_o1_raw[col].apply(parse_val_2)
        df_o1_clubbed = df_o1_raw.groupby(['PRODUCT_NAME', 'UID'])[f1_num_cols].sum().reset_index()

        # 2. FILTERING TARGET (Sheet 2) - Skips rows where Col C is empty
        df_o2_filtered = df_o2_raw[df_o2_raw.iloc[:, 2].astype(str).str.strip().replace("0", "") != ""].copy()
        df_o2_filtered['UID'] = df_o2_filtered.iloc[:, 0].astype(str).str.strip().str.upper() + "_" + df_o2_filtered.iloc[:, 2].astype(str).str.strip().str.upper()

        # Dynamic Product Filter
        unique_prods = sorted(df_o1_clubbed['PRODUCT_NAME'].unique())
        selected_prod = st.selectbox("🎯 Filter Results by Product:", ["ALL"] + unique_prods)

        if st.button("RUN AGGREGATED COMPARISON"):
            merged = pd.merge(df_o1_clubbed, df_o2_filtered, on='UID', how='outer', suffixes=('_F1', '_F2')).fillna(0)
            if selected_prod != "ALL": merged = merged[merged['PRODUCT_NAME'] == selected_prod]

            audit_rows_2 = []
            mismatch_count_2 = 0
            for _, row in merged.iterrows():
                res = {"UNIQUE_ID": row['UID'], "OVERALL_MATCH": True}
                def check_tol(v1, v2):
                    n1, n2 = parse_val_2(v1), parse_val_2(v2)
                    diff, mx = abs(n1 - n2), max(abs(n1), abs(n2))
                    threshold = 0.005 * mx if mx != 0 else 0
                    if diff <= max(threshold, 0.01): return f"✅ {n1:,.2f}"
                    return f"❌ {n1:,.2f} | {n2:,.2f}"

                res["L_vs_E (Old Spend)"] = check_tol(row.iloc[2], row.get('Historical Product Spend', 0))
                res["N_vs_G (Imp Sales)"] = check_tol(row.iloc[4], row.get('Historical Impactable Sales', 0))
                res["M_vs_D (Opt Spend)"] = check_tol(row.iloc[3], row.get('Optimized Product Spend', 0))
                res["O_vs_F (Opt Imp Sales)"] = check_tol(row.iloc[5], row.get('Optimized Impactable Sales', 0))
                res["P_vs_H (ROI)"] = check_tol(row.iloc[6], row.get('Optimized ROI', 0))

                if "❌" in str(res.values()):
                    res["OVERALL_MATCH"] = False
                    mismatch_count_2 += 1
                audit_rows_2.append(res)

            report_df = pd.DataFrame(audit_rows_2)
            st.markdown('<div class="report-card"><h3>Comparison Analysis Summary</h3></div>', unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric(f"Records ({selected_prod})", len(report_df))
            m2.metric("Mismatches", mismatch_count_2, delta_color="inverse")

            st.dataframe(report_df.style.apply(lambda r: ['background-color: #4b1111' if not r.OVERALL_MATCH else '' for _ in r], axis=1), use_container_width=True)
            st.download_button("📥 Download Filtered Report", report_df.to_csv(index=False), "Filtered_Audit.csv")