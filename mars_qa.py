import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

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
    s = clean_brackets(val).upper().replace('$', '').replace(',', '')
    if s == "" or s == "MISSING": return 0.0
    m = 1.0
    if s.endswith('K'): m = 1e3; s = s[:-1]
    elif s.endswith('M'): m = 1e6; s = s[:-1]
    elif s.endswith('B'): m = 1e9; s = s[:-1]
    try: return float(s) * m
    except ValueError: return 0.0

def parse_val_2(val):
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
                
                # CRITICAL: Prepare Master Export Row with specific Variance Columns
                row_data = {f"A_{c}": final_a.at[r, c] for c in common}
                row_data.update({f"B_{c}": final_b.at[r, c] for c in common})
                row_data["MATCH_STATUS"] = "MISMATCH" if row_diff else "MATCH"
                
                # Dynamic numeric column detection for variance calculation
                num_col = next((c for c in common if any(k in c for k in ['AMOUNT', 'SPEND', 'COST', 'VALUE'])), common[-1])
                val_a = parse_fin(final_a.at[r, num_col])
                val_b = parse_fin(final_b.at[r, num_col])
                
                # Column: ABS_DIFF_AMOUNT (Always Positive)
                abs_val = abs(val_a - val_b)
                row_data["ABS_DIFF_AMOUNT"] = round(abs_val, 2)
                
                # Column: PERCENTAGE_DIFF
                if val_a != 0:
                    pct_val = (abs_val / val_a) * 100
                else:
                    pct_val = 100.0 if abs_val > 0 else 0.0
                row_data["PERCENTAGE_DIFF"] = f"{round(pct_val, 2)}%"
                
                all_rows.append(row_data)

            # Master Export Generation
            export_df = pd.DataFrame(all_rows)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                export_df.to_excel(wr, index=False, sheet_name='Financial_Audit')
            
            # --- SUMMARY ANALYSIS DASHBOARD ---
            st.markdown('<div class="report-card"><h3>Financial Integrity Summary</h3></div>', unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            s1.metric("Total Rows", max_r)
            s2.metric("Mismatches Found", mismatch_count, delta_color="inverse")
            s3.download_button("📥 Download Master Report", buf.getvalue(), "Financial_Audit_Report.xlsx")

            v1, v2 = st.columns(2)
            v1.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
            v2.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)

# ---------------------------------------------------------
# TAB 2: GENERAL DATA COMPARISON
# ---------------------------------------------------------
with tab2:
    st.subheader("General Data Comparison Mode")
    c1, c2 = st.columns(2)
    other_a = c1.file_uploader("📂 Source (File 1)", type=['xlsx', 'csv'], key="t2_fa")
    other_b = c2.file_uploader("📂 Target (File 2)", type=['xlsx', 'csv'], key="t2_fb")
    
    if other_a and other_b:
        df_o1 = pd.read_excel(other_a, dtype=str).fillna("") if other_a.name.endswith('xlsx') else pd.read_csv(other_a, dtype=str).fillna("")
        df_o2 = pd.read_excel(other_b, dtype=str).fillna("") if other_b.name.endswith('xlsx') else pd.read_csv(other_b, dtype=str).fillna("")

        # Filter for Row 3+ units
        df_o2_units = df_o2[df_o2.iloc[:, 2].str.strip() != ""].copy()
        df_o1['UID'] = df_o1.iloc[:, 6].str.strip().str.upper() + "_" + df_o1.iloc[:, 9].str.strip().str.upper()
        df_o2_units['UID'] = df_o2_units.iloc[:, 0].str.strip().str.upper() + "_" + df_o2_units.iloc[:, 2].str.strip().str.upper()

        if st.button("RUN GENERAL COMPARISON"):
            merged = pd.merge(df_o1, df_o2_units, on='UID', how='outer', suffixes=('_F1', '_F2')).fillna("MISSING")
            audit_rows_2 = []
            red_rows_count = 0
            total_var = 0.0

            for _, row in merged.iterrows():
                res = {"UNIQUE_ID": row['UID'], "OVERALL_MATCH": True}
                
                def check_with_tol(v1, v2):
                    n1, n2 = parse_val_2(v1), parse_val_2(v2)
                    diff = abs(n1 - n2)
                    mx = max(abs(n1), abs(n2))
                    threshold = 0.005 * mx if mx != 0 else 0
                    if diff <= max(threshold, 0.01):
                        return f"✅ {n1:.2f}", diff
                    return f"❌ {n1:.2f} | {n2:.2f}", diff

                r1, d1 = check_with_tol(row.get('Old spend', 'N/A'), row.get('Historical Product Spend', 'N/A'))
                r2, d2 = check_with_tol(row.get('Impactable sales', 'N/A'), row.get('Historical Impactable Sales', 'N/A'))
                r3, d3 = check_with_tol(row.get('Optimized spend', 'N/A'), row.get('Optimized Product Spend', 'N/A'))
                r4, d4 = check_with_tol(row.get('Optimize impactable sales', 'N/A'), row.get('Optimized Impactable Sales', 'N/A'))
                r5, d5 = check_with_tol(row.get('Optimized ROI_F1', 'N/A'), row.get('Optimized ROI_F2', 'N/A'))

                res.update({"L_vs_E": r1, "N_vs_G": r2, "M_vs_D": r3, "O_vs_F": r4, "P_vs_H": r5})
                if any("❌" in str(v) for v in res.values()):
                    res["OVERALL_MATCH"] = False
                    red_rows_count += 1
                
                total_var += (d1 + d2 + d3 + d4)
                audit_rows_2.append(res)

            # SUMMARY ANALYSIS TAB 2
            st.markdown('<div class="report-card"><h3>Mapped Comparison Summary</h3></div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Mapped Records", len(merged))
            m2.metric("Mismatched (Red)", red_rows_count, delta_color="inverse")
            m3.metric("Aggregated Variance", f"${total_var:,.2f}")

            report_df = pd.DataFrame(audit_rows_2)
            def style_general(row):
                if not row['OVERALL_MATCH']:
                    return ['background-color: #4b1111; color: #ffcccc'] * len(row)
                return [''] * len(row)

            st.dataframe(report_df.style.apply(style_general, axis=1), use_container_width=True)
            st.download_button("📥 Download General Audit Report", report_df.to_csv(index=False), "General_Audit_Report.csv")