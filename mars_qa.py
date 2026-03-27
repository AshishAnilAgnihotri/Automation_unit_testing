import streamlit as st
import pandas as pd
import time
import os
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
    }
    .stButton>button:hover { 
        transform: translateY(-3px) scale(1.02); 
        box-shadow: 0 8px 25px rgba(88, 166, 255, 0.5);
        background: linear-gradient(90deg, #58a6ff 0%, #1f6feb 100%);
    }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800 !important; }
    .stMetric { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .report-card {
        background: #161b22; padding: 30px; border-radius: 20px; border: 1px solid #30363d;
        text-align: center; margin-bottom: 25px; border-top: 5px solid #58a6ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- AUDIT LOGGING PATH ---
LOG_PATH = Path(r"C:\Users\ashish.agnihotri.saa\Desktop\Automation_unit_testing")
LOG_PATH.mkdir(parents=True, exist_ok=True)


def save_audit_record(f_a, f_b, rows, red, yellow, score):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = LOG_PATH / f"Audit_Summary_{timestamp}.txt"
    summary = (
        f"EXECUTIVE AUDIT RECORD\n{'=' * 30}\n"
        f"SOURCE: {f_a}\nTARGET: {f_b}\n\n"
        f"ROWS: {rows}\nCRITICAL (RED): {red}\nSHORTHAND (YELLOW): {yellow}\n"
        f"SCORE: {score}%\n{'=' * 30}"
    )
    with open(log_file, "w") as f: f.write(summary)
    return log_file


# --- FINANCIAL LOGIC ---
def parse_fin(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).replace('$', '').replace(',', '').strip().upper()
    m = 1.0
    if s.endswith('K'):
        m = 1e3; s = s[:-1]
    elif s.endswith('M'):
        m = 1e6; s = s[:-1]
    elif s.endswith('B'):
        m = 1e9; s = s[:-1]
    try:
        return float(s) * m
    except:
        return s


def get_state(v1, v2):
    s1, s2 = str(v1).strip(), str(v2).strip()
    if s1 == s2: return 0
    n1, n2 = parse_fin(v1), parse_fin(v2)
    if isinstance(n1, float) and isinstance(n2, float):
        if n1 == n2: return 0
        diff = abs(n1 - n2) / max(abs(n1), abs(n2)) if max(abs(n1), abs(n2)) != 0 else 0
        return 1 if diff <= 0.005 else 2
    return 2


# --- DASHBOARD ---
st.title(" Data Comparision")
st.caption(f"Archiving to: {LOG_PATH}")

u1, u2 = st.columns(2)
with u1: file_a = st.file_uploader("📂 Ledger A (Source)", type=['xlsx', 'csv'])
with u2: file_b = st.file_uploader("📂 Ledger B (Target)", type=['xlsx', 'csv'])

if file_a and file_b:
    df_a = pd.read_excel(file_a, dtype=str) if file_a.name.endswith('xlsx') else pd.read_csv(file_a, dtype=str)
    df_b = pd.read_excel(file_b, dtype=str) if file_b.name.endswith('xlsx') else pd.read_csv(file_b, dtype=str)

    df_a.columns = [str(c).strip().upper() for c in df_a.columns]
    df_b.columns = [str(c).strip().upper() for c in df_b.columns]

    # FEATURE: HEADER MATCH VALIDATION & POSITIONAL ALIGNMENT
    common_headers = [c for c in df_a.columns if c in df_b.columns]

    if not common_headers:
        st.error(
            f"❌ **HEADERS DO NOT MATCH**: Ledger A has {list(df_a.columns)} while Ledger B has {list(df_b.columns)}. Execution halted.")
        st.stop()

    # Reorder Ledger B to match Ledger A sequence positionally
    df_b_aligned = df_b[common_headers]

    if st.button("EXECUTE DUAL-TABLE RECONCILIATION"):
        max_r = max(len(df_a), len(df_b_aligned))
        final_a = df_a.reindex(range(max_r)).fillna("0")
        final_b = df_b_aligned.reindex(range(max_r)).fillna("0")

        style_a = pd.DataFrame('', index=final_a.index, columns=final_a.columns)
        style_b = pd.DataFrame('', index=final_b.index, columns=final_b.columns)
        red_c, yellow_c = 0, 0

        for r in range(max_r):
            for col in common_headers:
                lvl = get_state(final_a.at[r, col], final_b.at[r, col])
                if lvl == 1:
                    yellow_c += 1
                    style_a.at[r, col] = 'background-color: rgba(251, 255, 0, 0.1); color: #fbff00;'
                    style_b.at[r, col] = 'background-color: rgba(251, 255, 0, 0.1); color: #fbff00;'
                elif lvl == 2:
                    red_c += 1
                    style_a.at[r, col] = 'background-color: rgba(255, 75, 75, 0.1); color: #ff4b4b;'
                    style_b.at[r, col] = 'background-color: rgba(255, 75, 75, 0.1); color: #ff4b4b;'

        integrity = round(((max_r * len(common_headers) - red_c) / (max_r * len(common_headers))) * 100, 1)
        saved_log = save_audit_record(file_a.name, file_b.name, max_r, red_c, yellow_c, integrity)

        st.markdown(f'<div class="report-card"><h1>Integrity Score: {integrity}%</h1></div>', unsafe_allow_html=True)

        k1, k2, k3 = st.columns(3)
        k1.metric("Rows Scanned", max_r)
        k2.metric("Critical Variances", red_c)
        k3.metric("Verified Shorthand", yellow_c)

        st.markdown("### 🔍 Dual-Table Comparison Workspace")
        view_a, view_b = st.columns(2)
        with view_a:
            st.write("**LEDGER A (SOURCE)**")
            st.dataframe(final_a.style.apply(lambda x: style_a, axis=None), use_container_width=True)
        with view_b:
            st.write("**LEDGER B (AUTO-ALIGNED TARGET)**")
            st.dataframe(final_b.style.apply(lambda x: style_b, axis=None), use_container_width=True)

        st.success(f"Audit Complete. Summary saved to {saved_log}")