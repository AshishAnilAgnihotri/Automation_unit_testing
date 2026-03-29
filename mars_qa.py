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
    """Standard financial parser for Tab 1."""
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

# --- APP LAYOUT WITH TABS ---
st.title("🛡️ Audit Command Center")
tab1, tab2 = st.tabs(["💰 Financial Reconciliation", "📊 General Data Comparison"])

# ---------------------------------------------------------
# TAB 1: FINANCIAL RECONCILIATION (Original Logic)
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
            red_c, yellow_c = 0, 0

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
                        if lvl == 2: red_c += 1
                        else: yellow_c += 1

                row_data = {f"A_{c}": final_a.at[r, c] for c in common}
                row_data.update({f"B_{c}": final_b.at[r, c] for c in common})
                row_data["MATCH_STATUS"] = "MISMATCH" if row_diff else "MATCH"
                all_rows.append(row_data)

            export_df = pd.DataFrame(all_rows)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                export_df.to_excel(wr, index=False, sheet_name='Audit')
            st.download_button("📥 Download Master Report", buf.getvalue(), "Financial_Audit.xlsx")

            v1, v2 = st.columns(2)
            v1.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
            v2.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)

# ---------------------------------------------------------
# TAB 2: GENERAL DATA COMPARISON (New Pure Mapping Logic)
# ---------------------------------------------------------
with tab2:
    st.subheader("General Data Comparison Mode")
    st.info("Direct Comparison: L↔E, N↔G, M↔D, O↔F, P↔H. Tolerance: 0.5% | Decimals: 2. Data filtered for units only.")
    
    c1, c2 = st.columns(2)
    other_a = c1.file_uploader("📂 Source (File 1)", type=['xlsx', 'csv'], key="t2_fa")
    other_b = c2.file_uploader("📂 Target (File 2)", type=['xlsx', 'csv'], key="t2_fb")
    
    if other_a and other_b:
        df_o1 = pd.read_excel(other_a, dtype=str).fillna("") if other_a.name.endswith('xlsx') else pd.read_csv(other_a, dtype=str).fillna("")
        df_o2 = pd.read_excel(other_b, dtype=str).fillna("") if other_b.name.endswith('xlsx') else pd.read_csv(other_b, dtype=str).fillna("")

        # STRATEGY: Target the Unit Data (Row 3+)
        # We only keep rows where 'Cost Type' (Index 2 in File 2) is populated. 
        # This skips the blank 'Total' rows for each product.
        df_o2_units = df_o2[df_o2.iloc[:, 2].str.strip() != ""].copy()

        # Create UIDs: [Product Name]_[Channel/Cost Type]
        # File 1: Col 6 + Col 9 | File 2: Col 0 + Col 2
        df_o1['UID'] = df_o1.iloc[:, 6].str.strip().str.upper() + "_" + df_o1.iloc[:, 9].str.strip().str.upper()
        df_o2_units['UID'] = df_o2_units.iloc[:, 0].str.strip().str.upper() + "_" + df_o2_units.iloc[:, 2].str.strip().str.upper()

        if st.button("RUN GENERAL COMPARISON"):
            merged = pd.merge(df_o1, df_o2_units, on='UID', how='outer', suffixes=('_F1', '_F2')).fillna("MISSING")

            audit_rows = []
            for _, row in merged.iterrows():
                res = {"UNIQUE_ID": row['UID'], "OVERALL_MATCH": True}
                
                def check_with_tolerance(v1, v2):
                    n1, n2 = parse_val_2(v1), parse_val_2(v2)
                    diff = abs(n1 - n2)
                    # 0.5% Tolerance check
                    max_val = max(abs(n1), abs(n2))
                    threshold = 0.005 * max_val if max_val != 0 else 0
                    
                    # 0.01 cent buffer for rounding safety
                    if diff <= max(threshold, 0.01):
                        return f"✅ {n1:.2f}"
                    return f"❌ {n1:.2f} | {n2:.2f}"

                # Mappings (L-E, N-G, M-D, O-F, P-H)
                res["L_vs_E (Old Spend)"] = check_with_tolerance(row.get('Old spend', 'N/A'), row.get('Historical Product Spend', 'N/A'))
                res["N_vs_G (Imp Sales)"] = check_with_tolerance(row.get('Impactable sales', 'N/A'), row.get('Historical Impactable Sales', 'N/A'))
                res["M_vs_D (Opt Spend)"] = check_pair = check_with_tolerance(row.get('Optimized spend', 'N/A'), row.get('Optimized Product Spend', 'N/A'))
                res["O_vs_F (Opt Imp Sales)"] = check_with_tolerance(row.get('Optimize impactable sales', 'N/A'), row.get('Optimized Impactable Sales', 'N/A'))
                res["P_vs_H (ROI)"] = check_with_tolerance(row.get('Optimized ROI_F1', 'N/A'), row.get('Optimized ROI_F2', 'N/A'))

                # Set global mismatch flag for row coloring
                if any("❌" in str(v) for v in res.values()):
                    res["OVERALL_MATCH"] = False
                
                audit_rows.append(res)

            report_df = pd.DataFrame(audit_rows)

            # Highlighting Logic: Entire Row turns Red if OVERALL_MATCH is False
            def style_general(row):
                if not row['OVERALL_MATCH']:
                    return ['background-color: #4b1111; color: #ffcccc'] * len(row)
                return [''] * len(row)

            st.markdown(f"### 📋 Audit Results ({len(report_df)} Records)")
            st.dataframe(report_df.style.apply(style_general, axis=1), use_container_width=True)

            csv_data = report_df.to_csv(index=False)
            st.download_button("📥 Download General Audit CSV", csv_data, "General_Audit_Report.csv")