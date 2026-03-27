import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
from datetime import datetime

# Initialize app with a professional Bootstrap theme (FLATLY or LUX)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

MANDATORY_COLUMNS = [
    "SITEID", "SUBJID", "VISITID", "VISITNAME", "VISITINDEX", 
    "FORMNAME", "SRECORD", "FORMREPEATKEY", "ITEMGROUPREPEATKEY", 
    "SITEMNEM", "SUBJGUID", "FORMID", "DATAPAGEID", "SRMODTM", "DOMAIN"
]

# --- UI COMPONENTS ---

sidebar = html.Div(
    [
        html.H2("QC Portal", className="display-6"),
        html.Hr(),
        html.P("Clinical Data Validation Suite", className="lead"),
        dbc.Nav(
            [
                dbc.NavLink("Dashboard", href="/", active="exact"),
                dbc.NavLink("Documentation", href="#", active="exact", disabled=True),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style={"position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "18rem", "padding": "2rem 1rem", "backgroundColor": "#f8f9fa"},
)

content = html.Div([
    dbc.Row([
        dbc.Col(html.H1("🛡️ Mandatory Field Auditor", className="text-primary mb-4"), width=12)
    ]),

    # Metric Cards
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Files Processed", className="card-title"),
            html.H2(id="total-files", children="0", className="text-info")
        ])), width=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Total Issues", className="card-title"),
            html.H2(id="total-issues", children="0", className="text-danger")
        ])), width=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Clean Files", className="card-title"),
            html.H2(id="clean-files", children="0", className="text-success")
        ])), width=4),
    ], className="mb-4"),

    # Upload Section
    dbc.Card([
        dbc.CardBody([
            dcc.Upload(
                id='upload-data',
                children=html.Div(['Drag and Drop or ', html.A('Select CSV Files', className="text-primary")]),
                style={'width': '100%', 'height': '80px', 'lineHeight': '80px', 'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '10px', 'textAlign': 'center'},
                multiple=True
            ),
            html.Div(id='file-list', className="mt-2 text-muted small"),
            dbc.Button('🚀 Run Validation', id='start-btn', color="primary", className="mt-3 w-100", n_clicks=0),
        ])
    ], className="mb-4 shadow-sm"),

    # Results Table
    dbc.Card([
        dbc.CardHeader("Validation Detailed Log"),
        dbc.CardBody([
            dash_table.DataTable(
                id='error-log-table',
                sort_action="native",
                filter_action="native", # Adds search bars to every column
                page_action="native",
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'padding': '12px', 'fontFamily': 'Segoe UI, Tahoma, sans-serif'},
                style_header={'backgroundColor': '#f2f2f2', 'fontWeight': 'bold', 'border': '1px solid #dee2e6'},
                style_data_conditional=[{
                    'if': {'filter_query': '{Status} eq "MISSING COLUMN"'},
                    'backgroundColor': '#fff3f3', 'color': '#dc3545'
                }]
            ),
            html.Div(
                dbc.Button("📥 Export CSV Report", id="btn-download", color="success", className="mt-3"),
                id='download-container', style={'display': 'none'}
            ),
            dcc.Download(id="download-log-csv"),
        ])
    ], className="shadow-sm")
], style={"marginLeft": "20rem", "marginRight": "2rem", "padding": "2rem"})

app.layout = html.Div([sidebar, content])

# --- LOGIC ---

def process_file(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    
    entries = []
    found_cols = [c for c in MANDATORY_COLUMNS if c in df.columns]
    missing_cols = [c for c in MANDATORY_COLUMNS if c not in df.columns]

    for col in missing_cols:
        entries.append({"File": filename, "Row": "Header", "Column": col, "Status": "MISSING COLUMN"})

    for col in found_cols:
        null_mask = df[col].isnull() | (df[col].astype(str).str.strip().isin(['', 'nan', 'NaN', 'None']))
        for idx in df[null_mask].index:
            entry = {"File": filename, "Row": idx + 2, "Column": col, "Status": "EMPTY CELL"}
            for m in MANDATORY_COLUMNS: entry[m] = df.iloc[idx].get(m, "N/A")
            entries.append(entry)
    
    return entries, (1 if not entries and not missing_cols else 0)

@callback(
    [Output('error-log-table', 'data'),
     Output('error-log-table', 'columns'),
     Output('total-files', 'children'),
     Output('total-issues', 'children'),
     Output('clean-files', 'children'),
     Output('download-container', 'style')],
    Input('start-btn', 'n_clicks'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def run_qc(n, contents, names):
    if not contents: return [], [], "0", "0", "0", {'display': 'none'}
    
    master_log = []
    clean_count = 0
    for c, n in zip(contents, names):
        logs, is_clean = process_file(c, n)
        master_log.extend(logs)
        clean_count += is_clean

    df = pd.DataFrame(master_log)
    if df.empty:
        return [], [], str(len(names)), "0", str(clean_count), {'display': 'none'}

    # Organize columns
    cols = [{"name": i, "id": i} for i in df.columns]
    return df.to_dict('records'), cols, str(len(names)), str(len(df)), str(clean_count), {'display': 'block'}

@callback(
    Output("download-log-csv", "data"),
    Input("btn-download", "n_clicks"),
    State('error-log-table', 'data'),
    prevent_initial_call=True
)
def export(n, data):
    return dcc.send_data_frame(pd.DataFrame(data).to_csv, f"QC_Report_{datetime.now().strftime('%H%M')}.csv", index=False)

if __name__ == '__main__':
    app.run(debug=True)