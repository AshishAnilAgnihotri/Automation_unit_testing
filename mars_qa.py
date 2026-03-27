import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime
from pathlib import Path

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

# --- CLEANING & MATH LOGIC ---

def clean_brackets(val):
    """Removes noise like (0.10%) or [USD]."""
    if pd.isna(val) or str(val).strip() == "": return ""
    return re.sub(r'[\(\[].*?[\)\]]', '', str(val)).strip()

def parse_fin(val):
    """Converts cleaned string to float."""
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

def get_state(v1, v2):
    s1, s2 = clean_brackets(v1), clean_brackets(v2)
    if s1 == s2: return 0
    n1, n2 = parse_fin(v1), parse_fin(v2)
    if n1 == n2: return 0
    diff = abs(n1 - n2) / max(abs(n1), abs(n2)) if max(abs(n1), abs(n2)) != 0 else 0
    return 1 if diff <= 0.005 else 2

# --- DASHBOARD ---
st.title("🛡️ Data Comparison Command Center")

u1, u2 = st.columns(2)
file_a = u1.file_uploader("📂 Ledger A (Source)", type=['xlsx', 'csv'])
file_b = u2.file_uploader("📂 Ledger B (Target)", type=['xlsx', 'csv'])

if file_a and file_b:
    df_a = pd.read_excel(file_a, dtype=str) if file_a.name.endswith('xlsx') else pd.read_csv(file_a, dtype=str)
    df_b = pd.read_excel(file_b, dtype=str) if file_b.name.endswith('xlsx') else pd.read_csv(file_b, dtype=str)

    df_a.columns = [str(c).strip().upper() for c in df_a.columns]
    df_b.columns = [str(c).strip().upper() for c in df_b.columns]
    common_headers = [c for c in df_a.columns if c in df_b.columns]

    if st.button("EXECUTE FULL MASTER RECONCILIATION"):
        max_r = max(len(df_a), len(df_b))
        final_a = df_a.reindex(range(max_r)).fillna("MISSING")
        final_b = df_b[common_headers].reindex(range(max_r)).fillna("MISSING")

        # Visual Cleaning
        for col in common_headers:
            final_a[col] = final_a[col].apply(clean_brackets)
            final_b[col] = final_b[col].apply(clean_brackets)

        style_a = pd.DataFrame('', index=final_a.index, columns=final_a.columns)
        style_b = pd.DataFrame('', index=final_b.index, columns=final_b.columns)
        
        all_rows_for_export = []
        red_c, yellow_c = 0, 0

        for r in range(max_r):
            row_has_variance = False
            amount_col = "AMOUNT" if "AMOUNT" in common_headers else None
            
            for col in common_headers:
                lvl = get_state(final_a.at[r, col], final_b.at[r, col])
                if lvl > 0:
                    row_has_variance = True
                    color = 'rgba(255, 75, 75, 0.15)' if lvl == 2 else 'rgba(251, 255, 0, 0.1)'
                    style_a.at[r, col] = f'background-color: {color}; color: {"#ff4b4b" if lvl == 2 else "#fbff00"};'
                    style_b.at[r, col] = f'background-color: {color}; color: {"#ff4b4b" if lvl == 2 else "#fbff00"};'
                    if lvl == 2: red_c += 1
                    else: yellow_c += 1

            # Build row dictionary with strict column ordering for Excel (L & M alignment)
            row_data = {}
            for c in common_headers: row_data[f"A_{c}"] = final_a.at[r, c]
            for c in common_headers: row_data[f"B_{c}"] = final_b.at[r, c]
            
            row_data["MATCH_STATUS"] = "MISMATCH" if row_has_variance else "MATCH"
            
            # Variance Calculations (Always Positive Diff)
            if amount_col:
                val_a = parse_fin(final_a.at[r, amount_col])
                val_b = parse_fin(final_b.at[r, amount_col])
                
                # ABSOLUTE DIFFERENCE (MAX - MIN)
                abs_diff = abs(val_b - val_a)
                pct_diff = (abs_diff / val_a * 100) if val_a != 0 else (100.0 if abs_diff > 0 else 0)
                
                row_data["ABS_DIFF_VAL"] = round(abs_diff, 2)  # Column L
                row_data["PERCENT_DIFF"] = f"{round(pct_diff, 2)}%" # Column M
            else:
                row_data["ABS_DIFF_VAL"] = 0
                row_data["PERCENT_DIFF"] = "0%"

            all_rows_for_export.append(row_data)

        # --- EXPORT ---
        export_df = pd.DataFrame(all_rows_for_export)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Full_Reconciliation')
            workbook = writer.book
            worksheet = writer.sheets['Full_Reconciliation']
            # Header formatting
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#1f6feb', 'font_color': 'white', 'border': 1})
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
            worksheet.freeze_panes(1, 0)
            
        st.download_button("📥 Download Master Report", buffer.getvalue(), f"Full_Audit_{datetime.now().strftime('%H%M')}.xlsx")

        # --- UI DISPLAY ---
        total_cells = max_r * len(common_headers)
        integrity = round(((total_cells - red_c) / total_cells) * 100, 2)
        st.markdown(f'<div class="report-card"><h1>Integrity Score: {integrity}%</h1></div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Rows", max_r); c2.metric("Critical Cells", red_c); c3.metric("Warning Cells", yellow_c)
        
        v1, v2 = st.columns(2)
        v1.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
        v2.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)