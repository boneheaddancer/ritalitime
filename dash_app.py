"""
RitaliTime - ADHD Medication & Painkiller Timeline Simulator
Dash Application (replacing Streamlit)

This application provides:
- ADHD medication and stimulant timeline simulation
- Painkiller effect timeline simulation  
- Interactive data visualization with Plotly
- True client-side data persistence
- Real-time calculations and updates
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from dash_extensions import WebSocket
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import json
import base64
from datetime import time, datetime
import os

# Import existing modules
from medication_simulator import MedicationSimulator
import data_schema

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="RitaliTime - Medication Timeline Simulator"
)

# App configuration
app.config.suppress_callback_exceptions = True

# Initialize global simulator instance
simulator = MedicationSimulator()

# Load medications data
def load_medications_data():
    """Load medications data from JSON files"""
    try:
        with open('medications.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading medications: {e}")
        return {}

medications_data = load_medications_data()

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("💊 RitaliTime - Medication Timeline Simulator", 
                    className="text-center mb-4"),
            html.P("Simulate and visualize medication and stimulant effects throughout the day",
                   className="text-center text-muted")
        ])
    ]),
    
    # Navigation tabs
    dbc.Tabs([
        dbc.Tab(label="ADHD Medications", tab_id="adhd-tab"),
        dbc.Tab(label="Painkillers", tab_id="painkillers-tab"),
    ], id="main-tabs", active_tab="adhd-tab"),
    
    # Content area
    html.Div(id="tab-content"),
    
    # Hidden div for storing data
    dcc.Store(id="medication-store"),
    dcc.Store(id="stimulant-store"),
    dcc.Store(id="painkiller-store"),
    dcc.Store(id="app-settings-store"),
    
], fluid=True, className="mt-4")

# Callback to render tab content
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "adhd-tab":
        return render_adhd_tab()
    elif active_tab == "painkillers-tab":
        return render_painkillers_tab()
    return "Select a tab"

def render_adhd_tab():
    """Render the ADHD medications tab"""
    return dbc.Row([
        dbc.Col([
            html.H3("ADHD Medications & Stimulants"),
            html.P("This tab will contain the ADHD medication simulation interface"),
            # TODO: Add medication input forms and timeline visualization
        ], width=12)
    ])

def render_painkillers_tab():
    """Render the painkillers tab"""
    return dbc.Row([
        dbc.Col([
            html.H3("Painkiller Timeline"),
            html.P("This tab will contain the painkiller simulation interface"),
            # TODO: Add painkiller input forms and timeline visualization
        ], width=12)
    ])

# Main application entry point
if __name__ == "__main__":
    print("Starting RitaliTime Dash application...")
    print(f"Medications loaded: {len(medications_data)} categories")
    
    # Run the app
    app.run_server(
        debug=True,
        host="127.0.0.1",
        port=8080
    )
