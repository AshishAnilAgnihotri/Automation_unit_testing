import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime
from pathlib import Path

# --- PREMIUM UI/UX CONFIGURATION ---
st.set_page_config(page_title="Audit Command Center", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .main { background: #0d1117; color: #c9d1d9; }
    .stButton>button {
        background: linear-gradient(90deg, #1f6feb 0%, #58a6ff 100%);
        color: white; border-radius: 50px; height: 3.5em; font-weight: bold;
        border: none; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        width: 100%;
    }
    .stButton>button:hover { 
        transform: translateY(-3px); 
        box-shadow: 0 8px 25px rgba(88, 166, 255, 0.4);
    }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800 !important; }
    .stMetric { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .report-card {
        background: #161b22; padding: 30px; border-radius: 20px; border: 1px solid #30363d;
        text-align: center; margin-bottom: 25px; border-top: 5px solid #58a6ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CLEANING & COMPARISON LOGIC ---

def clean_brackets(val):
    """Removes anything inside () or []. Example: 87.2M(23.43%) -> 87.2M"""
    if pd.isna(val) or str(val).strip() == "":
        return ""
    # Regex: find '(' or '[' and everything until the closing ')' or ']'
    clean_val = re.sub(r'[\(\[].*?[\)\]]', '', str(val))
    return clean_val.strip()

def parse_fin(val):
    """Converts cleaned financial string to float for comparison."""
    # Ensure it's cleaned first
    s = clean_brackets(val).upper().replace('$', '').replace(',', '')
    if s == "" or s == "MISSING": return 0.0
    
    m = 1.0
    if s.endswith('K'): m = 1e3; s = s[:-1]
    elif s.endswith('M'): m = 1e6; s = s[:-1]
    elif s.endswith('B'): m = 1e9; s = s[:-1]
    
    try:
        return float(s) * m
    except ValueError:
        return s

def get_state(v1, v2):
    """Returns 0: Match, 1: Yellow (Tolerance), 2: Red (Critical)"""
    # Compare cleaned strings directly first
    s1, s2 = clean_brackets(v1), clean_brackets(v2)
    if s1 == s2: return 0
    
    # Compare numeric values
    n1, n2 = parse_fin(v1), parse_fin(v2)
    if isinstance(n1, (float, int)) and isinstance(n2, (float, int)):
        if n1 == n2: return 0
        diff = abs(n1 - n2) / max(abs(n1), abs(n2)) if max(abs(n1), abs(n2)) != 0 else 0
        return 1 if diff <= 0.005 else 2 
    return 2

# --- DASHBOARD ---
st.title("🛡️ Data Comparison Command Center")
st.caption("Auto-scrubbing variances in brackets (e.g., (0.10%)) for cleaner audits.")

u1, u2 = st.columns(2)
file_a = u1.file_uploader("📂 Ledger A (Source)", type=['xlsx', 'csv'])
file_b = u2.file_uploader("📂 Ledger B (Target)", type=['xlsx', 'csv'])

if file_a and file_b:
    df_a = pd.read_excel(file_a, dtype=str) if file_a.name.endswith('xlsx') else pd.read_csv(file_a, dtype=str)
    df_b = pd.read_excel(file_b, dtype=str) if file_b.name.endswith('xlsx') else pd.read_csv(file_b, dtype=str)

    df_a.columns = [str(c).strip().upper() for c in df_a.columns]
    df_b.columns = [str(c).strip().upper() for c in df_b.columns]
    common_headers = [c for c in df_a.columns if c in df_b.columns]

    if st.button("EXECUTE DUAL-TABLE RECONCILIATION"):
        # 1. Align Dataframes
        max_r = max(len(df_a), len(df_b))
        final_a = df_a.reindex(range(max_r)).fillna("MISSING")
        final_b = df_b[common_headers].reindex(range(max_r)).fillna("MISSING")

        # 2. GLOBAL SCRUBBING - Clean all data for the final View and Export
        for col in common_headers:
            final_a[col] = final_a[col].apply(clean_brackets)
            final_b[col] = final_b[col].apply(clean_brackets)

        # 3. Process Comparisons & Styling
        style_a = pd.DataFrame('', index=final_a.index, columns=final_a.columns)
        style_b = pd.DataFrame('', index=final_b.index, columns=final_b.columns)
        variance_rows = []
        red_c, yellow_c = 0, 0

        for r in range(max_r):
            row_has_variance = False
            for col in common_headers:
                lvl = get_state(final_a.at[r, col], final_b.at[r, col])
                if lvl > 0:
                    row_has_variance = True
                    color = 'rgba(251, 255, 0, 0.1)' if lvl == 1 else 'rgba(255, 75, 75, 0.1)'
                    text_color = '#fbff00' if lvl == 1 else '#ff4b4b'
                    style_a.at[r, col] = f'background-color: {color}; color: {text_color};'
                    style_b.at[r, col] = f'background-color: {color}; color: {text_color};'
                    if lvl == 1: yellow_c += 1
                    else: red_c += 1

            if row_has_variance:
                # Combined Row for Single-Sheet Excel Export
                combined_row = {f"A_{c}": final_a.at[r, c] for c in common_headers}
                combined_row.update({f"B_{c}": final_b.at[r, c] for c in common_headers})
                variance_rows.append(combined_row)

        # --- OUTPUT: METRICS & EXPORT ---
        total_cells = max_r * len(common_headers)
        integrity = round(((total_cells - red_c) / total_cells) * 100, 2)
        
        st.markdown(f'<div class="report-card"><h1>Integrity Score: {integrity}%</h1></div>', unsafe_allow_html=True)
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Rows", max_r)
        k2.metric("Critical Variances", red_c)
        k3.metric("Tolerance/Shorthand", yellow_c)

        if variance_rows:
            export_df = pd.DataFrame(variance_rows)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Variances')
            
            st.download_button(
                label="📥 Download Variance-Only Report (Excel)",
                data=buffer.getvalue(),
                file_name=f"Audit_Variance_Report_{datetime.now().strftime('%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ Perfectly Reconciled: No variances detected.")

        # --- OUTPUT: VISUAL TABLES ---
        st.markdown("---")
        st.markdown("### 🔍 Side-by-Side Review Workspace")
        view_left, view_right = st.columns(2)
        
        with view_left:
            st.write("**LEDGER A (SOURCE)**")
            st.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
        
        with view_right:
            st.write("**LEDGER B (AUTO-ALIGNED)**")
            st.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)