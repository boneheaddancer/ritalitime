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
from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH, no_update
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

# Helper functions for time formatting
def format_time_hours_minutes(hours):
    """Format decimal hours as HH:MM"""
    if hours < 0:
        return "00:00"
    total_minutes = int(hours * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"

def format_duration_hours_minutes(hours):
    """Format decimal hours as duration string"""
    if hours < 0:
        return "0h 0m"
    total_minutes = int(hours * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"

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
            dbc.Row([
                # Left column - Input forms
                dbc.Col([
                    render_medication_forms(),
                    html.Hr(),
                    render_stimulant_forms(),
                ], width=6),
                
                # Right column - Current doses and timeline
                dbc.Col([
                    render_current_doses(),
                    html.Hr(),
                    render_timeline_visualization(),
                ], width=6)
            ])
        ], width=12)
    ])

def render_medication_forms():
    """Render medication input forms"""
    available_medications = []
    if medications_data.get('stimulants', {}).get('prescription_stimulants'):
        available_medications = list(medications_data['stimulants']['prescription_stimulants'].keys())
    
    if not available_medications:
        return dbc.Alert("No medications available. Please check that medications.json is properly loaded.", 
                         color="danger")
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4("💊 Add New Medication", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Dose Time"),
                    dcc.Input(
                        id="med-time-input",
                        type="time",
                        value="08:00",
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Medication Type"),
                    dcc.Dropdown(
                        id="med-name-dropdown",
                        options=[{"label": med, "value": med} for med in available_medications],
                        value=available_medications[0] if available_medications else None,
                        className="form-select"
                    )
                ], width=6)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Dosage (mg)"),
                    dcc.Input(
                        id="med-dosage-input",
                        type="number",
                        min=1.0,
                        max=100.0,
                        step=1.0,
                        value=20.0,
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("&nbsp;"),  # Spacer
                    dbc.Button("Add Medication", id="add-med-btn", color="primary", className="w-100")
                ], width=6)
            ], className="mb-3"),
            
            # Advanced parameters expandable section
            dbc.Collapse([
                html.H6("Advanced Parameters (Override Defaults)", className="mt-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Onset Time (hours)"),
                        dcc.Slider(
                            id="med-onset-slider",
                            min=0.5,
                            max=3.0,
                            step=0.1,
                            value=1.0,
                            marks={0.5: "0.5h", 1.0: "1h", 2.0: "2h", 3.0: "3h"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Peak Time (hours)"),
                        dcc.Slider(
                            id="med-peak-slider",
                            min=1.0,
                            max=6.0,
                            step=0.1,
                            value=2.0,
                            marks={1.0: "1h", 2.0: "2h", 4.0: "4h", 6.0: "6h"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Duration (hours)"),
                        dcc.Slider(
                            id="med-duration-slider",
                            min=4.0,
                            max=16.0,
                            step=0.5,
                            value=8.0,
                            marks={4.0: "4h", 8.0: "8h", 12.0: "12h", 16.0: "16h"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Peak Effect"),
                        dcc.Slider(
                            id="med-effect-slider",
                            min=0.1,
                            max=2.0,
                            step=0.1,
                            value=1.0,
                            marks={0.1: "0.1", 1.0: "1.0", 2.0: "2.0"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6)
                ])
            ], id="med-advanced-collapse"),
            
            dbc.Button(
                "Advanced Parameters",
                id="med-advanced-toggle",
                color="outline-secondary",
                size="sm",
                className="mt-2"
            )
        ])
    ], className="mb-4")

def render_stimulant_forms():
    """Render stimulant input forms"""
    available_stimulants = []
    if medications_data.get('stimulants', {}).get('common_stimulants'):
        available_stimulants = list(medications_data['stimulants']['common_stimulants'].keys())
    
    if not available_stimulants:
        return dbc.Alert("No stimulants available. Please check that medications.json is properly loaded.", 
                         color="danger")
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4("☕ Add New Stimulant", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Consumption Time"),
                    dcc.Input(
                        id="stim-time-input",
                        type="time",
                        value="09:00",
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Stimulant"),
                    dcc.Dropdown(
                        id="stim-name-dropdown",
                        options=[{"label": stim, "value": stim} for stim in available_stimulants],
                        value=available_stimulants[0] if available_stimulants else None,
                        className="form-select"
                    )
                ], width=6)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Quantity"),
                    dcc.Input(
                        id="stim-quantity-input",
                        type="number",
                        min=0.5,
                        max=5.0,
                        step=0.5,
                        value=1.0,
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("&nbsp;"),  # Spacer
                    dbc.Button("Add Stimulant", id="add-stim-btn", color="success", className="w-100")
                ], width=6)
            ], className="mb-3"),
            
            # Component selection for complex stimulants
            html.Div(id="stim-component-section", className="mb-3"),
            
            # Advanced parameters expandable section
            dbc.Collapse([
                html.H6("Advanced Parameters (Override Defaults)", className="mt-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Onset Time (hours)"),
                        dcc.Slider(
                            id="stim-onset-slider",
                            min=0.1,
                            max=2.0,
                            step=0.1,
                            value=0.17,
                            marks={0.1: "0.1h", 0.5: "0.5h", 1.0: "1h", 2.0: "2h"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Peak Time (hours)"),
                        dcc.Slider(
                            id="stim-peak-slider",
                            min=0.5,
                            max=3.0,
                            step=0.1,
                            value=1.0,
                            marks={0.5: "0.5h", 1.0: "1h", 2.0: "2h", 3.0: "3h"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Duration (hours)"),
                        dcc.Slider(
                            id="stim-duration-slider",
                            min=2.0,
                            max=12.0,
                            step=0.5,
                            value=6.0,
                            marks={2.0: "2h", 4.0: "4h", 6.0: "6h", 12.0: "12h"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Peak Effect"),
                        dcc.Slider(
                            id="stim-effect-slider",
                            min=0.1,
                            max=2.0,
                            step=0.1,
                            value=0.75,
                            marks={0.1: "0.1", 1.0: "1.0", 2.0: "2.0"},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6)
                ])
            ], id="stim-advanced-collapse"),
            
            dbc.Button(
                "Advanced Parameters",
                id="stim-advanced-toggle",
                color="outline-secondary",
                size="sm",
                className="mt-2"
            )
        ])
    ], className="mb-4")

def render_current_doses():
    """Render current doses display"""
    return dbc.Card([
        dbc.CardHeader([
            html.H4("📋 Current Doses", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div(id="current-doses-display"),
            html.Hr(),
            dbc.Button("Clear All Doses", id="clear-all-doses-btn", color="danger", size="sm")
        ])
    ])

def render_timeline_visualization():
    """Render timeline visualization"""
    return dbc.Card([
        dbc.CardHeader([
            html.H4("📊 Daily Effect Timeline", className="mb-0")
        ]),
        dbc.CardBody([
            dcc.Graph(id="timeline-graph", style={"height": "400px"}),
            dbc.Checklist(
                id="show-individual-curves",
                options=[{"label": "Show Individual Component Curves", "value": "show"}],
                value=[],
                inline=True
            )
        ])
    ])

def render_painkillers_tab():
    """Render the painkillers tab"""
    return dbc.Row([
        dbc.Col([
            dbc.Row([
                # Left column - Input forms
                dbc.Col([
                    render_painkiller_forms(),
                ], width=6),
                
                # Right column - Current doses and timeline
                dbc.Col([
                    render_painkiller_doses(),
                    html.Hr(),
                    render_painkiller_timeline(),
                ], width=6)
            ])
        ], width=12)
    ])

def render_painkiller_forms():
    """Render painkiller input forms"""
    available_painkillers = []
    if medications_data.get('painkillers'):
        available_painkillers = list(medications_data['painkillers'].keys())
    
    if not available_painkillers:
        return dbc.Alert("No painkillers available. Please check that medications.json is properly loaded.", 
                         color="danger")
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4("💊 Add New Painkiller", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Dose Time"),
                    dcc.Input(
                        id="pk-time-input",
                        type="time",
                        value="08:00",
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Painkiller Type"),
                    dcc.Dropdown(
                        id="pk-name-dropdown",
                        options=[{"label": pk, "value": pk} for pk in available_painkillers],
                        value=available_painkillers[0] if available_painkillers else None,
                        className="form-select"
                    )
                ], width=6)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Pills"),
                    dcc.Input(
                        id="pk-pills-input",
                        type="number",
                        min=1,
                        max=4,
                        step=1,
                        value=1,
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("&nbsp;"),  # Spacer
                    dbc.Button("Add Painkiller", id="add-pk-btn", color="warning", className="w-100")
                ], width=6)
            ], className="mb-3"),
            
            # Auto-calculated dosage display
            html.Div(id="pk-dosage-display", className="mb-3"),
            
            # Painkiller info display
            html.Div(id="pk-info-display", className="mb-3")
        ])
    ], className="mb-4")

def render_painkiller_doses():
    """Render current painkiller doses"""
    return dbc.Card([
        dbc.CardHeader([
            html.H4("📋 Current Painkiller Doses", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div(id="current-pk-doses-display"),
            html.Hr(),
            dbc.Button("Clear All Painkillers", id="clear-all-pk-btn", color="danger", size="sm")
        ])
    ])

def render_painkiller_timeline():
    """Render painkiller timeline visualization"""
    return dbc.Card([
        dbc.CardHeader([
            html.H4("📊 Painkiller Timeline", className="mb-0")
        ]),
        dbc.CardBody([
            dcc.Graph(id="pk-timeline-graph", style={"height": "400px"}),
            html.Div(id="pk-relief-windows", className="mt-3")
        ])
    ])

# Callbacks for medication forms
@app.callback(
    Output("med-advanced-collapse", "is_open"),
    Input("med-advanced-toggle", "n_clicks"),
    State("med-advanced-collapse", "is_open")
)
def toggle_med_advanced(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output("stim-advanced-collapse", "is_open"),
    Input("stim-advanced-toggle", "n_clicks"),
    State("stim-advanced-collapse", "is_open")
)
def toggle_stim_advanced(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# Callback for stimulant component selection
@app.callback(
    Output("stim-component-section", "children"),
    Input("stim-name-dropdown", "value")
)
def update_stim_component(stim_name):
    if stim_name and stim_name in ['redbull', 'monster']:
        return dbc.Row([
            dbc.Col([
                dbc.Label("Component"),
                dcc.Dropdown(
                    id="stim-component-dropdown",
                    options=[
                        {"label": "Caffeine", "value": "caffeine"},
                        {"label": "Taurine", "value": "taurine"}
                    ],
                    value="caffeine",
                    className="form-select"
                )
            ], width=12)
        ])
    return ""

# Callback for adding medication
@app.callback(
    [Output("current-doses-display", "children"),
     Output("med-time-input", "value"),
     Output("med-name-dropdown", "value"),
     Output("med-dosage-input", "value"),
     Output("med-onset-slider", "value"),
     Output("med-peak-slider", "value"),
     Output("med-duration-slider", "value"),
     Output("med-effect-slider", "value")],
    [Input("add-med-btn", "n_clicks")],
    [State("med-time-input", "value"),
     State("med-name-dropdown", "value"),
     State("med-dosage-input", "value"),
     State("med-onset-slider", "value"),
     State("med-peak-slider", "value"),
     State("med-duration-slider", "value"),
     State("med-effect-slider", "value")]
)
def add_medication(n_clicks, dose_time, med_name, dosage, onset_time, peak_time, duration, peak_effect):
    if not n_clicks:
        # Initial load - return current doses display
        return render_doses_list(), "08:00", None, 20.0, 1.0, 2.0, 8.0, 1.0
    
    if not all([dose_time, med_name, dosage]):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    try:
        # Convert time string to minutes
        hour, minute = map(int, dose_time.split(':'))
        time_minutes = hour * 60 + minute
        
        # Add medication to simulator
        custom_params = {
            'onset_time_min': int(onset_time * 60),
            'peak_time_min': int(peak_time * 60),
            'duration_min': int(duration * 60),
            'peak_effect': peak_effect
        }
        
        simulator.add_medication(
            dose_time, float(dosage), medication_name=med_name, custom_params=custom_params
        )
        
        # Reset form values
        return render_doses_list(), "08:00", None, 20.0, 1.0, 2.0, 8.0, 1.0
        
    except Exception as e:
        print(f"Error adding medication: {e}")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Callback for adding stimulant
@app.callback(
    [Output("current-doses-display", "children"),
     Output("stim-time-input", "value"),
     Output("stim-name-dropdown", "value"),
     Output("stim-quantity-input", "value"),
     Output("stim-onset-slider", "value"),
     Output("stim-peak-slider", "value"),
     Output("stim-duration-slider", "value"),
     Output("stim-effect-slider", "value")],
    [Input("add-stim-btn", "n_clicks")],
    [State("stim-time-input", "value"),
     State("stim-name-dropdown", "value"),
     State("stim-quantity-input", "value"),
     State("stim-onset-slider", "value"),
     State("stim-peak-slider", "value"),
     State("stim-duration-slider", "value"),
     State("stim-effect-slider", "value"),
     State("stim-component-dropdown", "value")]
)
def add_stimulant(n_clicks, dose_time, stim_name, quantity, onset_time, peak_time, duration, peak_effect, component_name):
    if not n_clicks:
        # Initial load - return current doses display
        return render_doses_list(), "09:00", None, 1.0, 0.17, 1.0, 6.0, 0.75
    
    if not all([dose_time, stim_name, quantity]):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    try:
        # Convert time string to minutes
        hour, minute = map(int, dose_time.split(':'))
        time_minutes = hour * 60 + minute
        
        # Add stimulant to simulator
        custom_params = {
            'onset_time_min': int(onset_time * 60),
            'peak_time_min': int(peak_time * 60),
            'duration_min': int(duration * 60),
            'peak_effect': peak_effect
        }
        
        simulator.add_stimulant(
            dose_time, stim_name, component_name, float(quantity), custom_params
        )
        
        # Reset form values
        return render_doses_list(), "09:00", None, 1.0, 0.17, 1.0, 6.0, 0.75
        
    except Exception as e:
        print(f"Error adding stimulant: {e}")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Callback for adding painkiller
@app.callback(
    [Output("current-pk-doses-display", "children"),
     Output("pk-time-input", "value"),
     Output("pk-name-dropdown", "value"),
     Output("pk-pills-input", "value")],
    [Input("add-pk-btn", "n_clicks")],
    [State("pk-time-input", "value"),
     State("pk-name-dropdown", "value"),
     State("pk-pills-input", "value")]
)
def add_painkiller(n_clicks, dose_time, pk_name, pills):
    if not n_clicks:
        # Initial load - return current doses display
        return render_painkiller_doses_list(), "08:00", None, 1
    
    if not all([dose_time, pk_name, pills]):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    try:
        # Convert time string to hours
        hour, minute = map(int, dose_time.split(':'))
        time_hours = hour + minute / 60.0
        
        # Create painkiller dose entry
        dose_entry = {
            'id': len(simulator.painkillers) if hasattr(simulator, 'painkillers') else 0,
            'time_hours': time_hours,
            'name': pk_name,
            'pills': int(pills),
            'time': dose_time
        }
        
        # Add to simulator (we'll need to implement this)
        if not hasattr(simulator, 'painkillers'):
            simulator.painkillers = []
        simulator.painkillers.append(dose_entry)
        
        # Reset form values
        return render_painkiller_doses_list(), "08:00", None, 1
        
    except Exception as e:
        print(f"Error adding painkiller: {e}")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Callback for clearing all doses
@app.callback(
    Output("current-doses-display", "children"),
    Input("clear-all-doses-btn", "n_clicks")
)
def clear_all_doses(n_clicks):
    if n_clicks:
        simulator.clear_all_doses()
        return render_doses_list()
    return render_doses_list()

# Callback for clearing all painkillers
@app.callback(
    Output("current-pk-doses-display", "children"),
    Input("clear-all-pk-btn", "n_clicks")
)
def clear_all_painkillers(n_clicks):
    if n_clicks:
        if hasattr(simulator, 'painkillers'):
            simulator.painkillers.clear()
        return render_painkiller_doses_list()
    return render_painkiller_doses_list()

# Callback for timeline graph
@app.callback(
    Output("timeline-graph", "figure"),
    [Input("show-individual-curves", "value"),
     Input("add-med-btn", "n_clicks"),
     Input("add-stim-btn", "n_clicks"),
     Input("clear-all-doses-btn", "n_clicks")]
)
def update_timeline_graph(show_individual, med_clicks, stim_clicks, clear_clicks):
    try:
        # Generate timeline data
        time_points, combined_effect = simulator.generate_daily_timeline()
        
        if len(time_points) == 0 or len(combined_effect) == 0:
            # Return empty graph
            fig = go.Figure()
            fig.add_annotation(
                text="No doses added yet. Add some medications or stimulants above!",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                xaxis_title="Time (hours)",
                yaxis_title="Effect Level",
                title="Daily Effect Timeline"
            )
            return fig
        
        # Create figure
        fig = go.Figure()
        
        # Add individual curves if requested
        if show_individual and "show" in show_individual:
            individual_curves = simulator.get_individual_curves()
            
            # Color palette for different doses
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
            
            for i, (label, curve) in enumerate(individual_curves):
                color = colors[i % len(colors)]
                
                fig.add_trace(go.Scatter(
                    x=time_points,
                    y=curve,
                    mode='lines',
                    name=f"Component: {label}",
                    line=dict(color=color, width=2),
                    fill='tonexty',
                    fillcolor=color,
                    opacity=0.3,
                    showlegend=True,
                    hovertemplate=f"<b>{label}</b><br>Time: %{{x:.1f}}h<br>Effect: %{{y:.3f}}<extra></extra>"
                ))
        
        # Add combined effect curve
        fig.add_trace(go.Scatter(
            x=time_points,
            y=combined_effect,
            mode='lines',
            name='Combined Effect',
            line=dict(color='blue', width=3),
            fill='tonexty',
            fillcolor='rgba(30, 144, 255, 0.1)',
            hovertemplate="<b>Combined Effect</b><br>Time: %{x:.1f}h<br>Effect: %{y:.3f}<extra></extra>"
        ))
        
        # Update layout
        fig.update_layout(
            xaxis_title="Time (hours)",
            yaxis_title="Effect Level",
            title="Daily Effect Timeline",
            hovermode='closest',
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        print(f"Error updating timeline graph: {e}")
        # Return error graph
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error generating timeline: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            xaxis_title="Time (hours)",
            yaxis_title="Effect Level",
            title="Daily Effect Timeline"
        )
        return fig

# Helper functions for rendering dose lists
def render_doses_list():
    """Render the current doses list"""
    try:
        all_doses = simulator.get_all_doses()
        if not all_doses:
            return html.P("No doses added yet. Add some medications or stimulants above!", className="text-muted")
        
        dose_cards = []
        for dose in all_doses:
            dose_card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Strong(f"{'💊' if dose['type'] == 'medication' else '☕'} {dose.get('medication_name', dose.get('stimulant_name', 'Unknown'))}"),
                            html.Br(),
                            html.Small(f"{dose.get('dosage', dose.get('quantity', 'Unknown'))} {'mg' if dose['type'] == 'medication' else 'units'} at {dose.get('time', 'Unknown time')}")
                        ], width=8),
                        dbc.Col([
                            dbc.Button("❌", id={"type": "remove-dose", "index": dose['id']}, 
                                     color="danger", size="sm", className="w-100")
                        ], width=4)
                    ])
                ])
            ], className="mb-2")
            dose_cards.append(dose_card)
        
        return html.Div(dose_cards)
        
    except Exception as e:
        print(f"Error rendering doses list: {e}")
        return html.P("Error loading doses", className="text-danger")

def render_painkiller_doses_list():
    """Render the current painkiller doses list"""
    try:
        if not hasattr(simulator, 'painkillers') or not simulator.painkillers:
            return html.P("No painkillers added yet. Add some above!", className="text-muted")
        
        dose_cards = []
        for dose in simulator.painkillers:
            dose_card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Strong(f"💊 {dose['name']}"),
                            html.Br(),
                            html.Small(f"{dose.get('pills', 1)} pill(s) at {dose.get('time', 'Unknown time')}")
                        ], width=8),
                        dbc.Col([
                            dbc.Button("❌", id={"type": "remove-pk-dose", "index": dose['id']}, 
                                     color="danger", size="sm", className="w-100")
                        ], width=4)
                    ])
                ])
            ], className="mb-2")
            dose_cards.append(dose_card)
        
        return html.Div(dose_cards)
        
    except Exception as e:
        print(f"Error rendering painkiller doses list: {e}")
        return html.P("Error loading painkillers", className="text-danger")

# Callback for painkiller dosage display
@app.callback(
    Output("pk-dosage-display", "children"),
    [Input("pk-name-dropdown", "value"),
     Input("pk-pills-input", "value")]
)
def update_pk_dosage(pk_name, pills):
    if not pk_name or not pills:
        return ""
    
    try:
        if medications_data.get('painkillers', {}).get(pk_name):
            pk_info = medications_data['painkillers'][pk_name]
            base_dosage = pk_info.get('standard_dose_mg', 0)
            
            if base_dosage > 0:
                total_dosage = base_dosage * pills
                return dbc.Alert([
                    html.Strong(f"Total Dosage: {total_dosage}mg"),
                    html.Br(),
                    html.Small(f"({base_dosage}mg per pill)")
                ], color="info", size="sm")
    except Exception as e:
        print(f"Error calculating dosage: {e}")
    
    return ""

# Callback for painkiller info display
@app.callback(
    Output("pk-info-display", "children"),
    Input("pk-name-dropdown", "value")
)
def update_pk_info(pk_name):
    if not pk_name:
        return ""
    
    try:
        if medications_data.get('painkillers', {}).get(pk_name):
            pk_info = medications_data['painkillers'][pk_name]
            
            onset_hours = pk_info.get('onset_min', 60) / 60.0
            peak_time_hours = pk_info.get('t_peak_min', 120) / 60.0
            peak_duration_hours = pk_info.get('peak_duration_min', 60) / 60.0
            duration_hours = pk_info.get('duration_min', 480) / 60.0
            
            return dbc.Alert([
                html.Strong(f"{pk_name}:"),
                html.Br(),
                html.Small(f"Onset {format_time_hours_minutes(onset_hours)}, Peak at {format_time_hours_minutes(peak_time_hours)}, Peak duration {format_duration_hours_minutes(peak_duration_hours)}, Total {format_duration_hours_minutes(duration_hours)}")
            ], color="info", size="sm")
    except Exception as e:
        print(f"Error loading painkiller info: {e}")
    
    return ""

# Callback for painkiller timeline graph
@app.callback(
    Output("pk-timeline-graph", "figure"),
    [Input("add-pk-btn", "n_clicks"),
     Input("clear-all-pk-btn", "n_clicks")]
)
def update_pk_timeline_graph(add_clicks, clear_clicks):
    try:
        if not hasattr(simulator, 'painkillers') or not simulator.painkillers:
            # Return empty graph
            fig = go.Figure()
            fig.add_annotation(
                text="No painkillers added yet. Add some above!",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                xaxis_title="Time (hours)",
                yaxis_title="Pain Level (0-10)",
                title="Painkiller Timeline",
                yaxis=dict(range=[0, 10])
            )
            return fig
        
        # Generate painkiller timeline (simplified for now)
        time_points = np.arange(0, 24.1, 0.1)
        pain_level = np.zeros_like(time_points)
        
        # Simple pain level calculation (placeholder)
        for dose in simulator.painkillers:
            dose_time = dose['time_hours']
            for i, t in enumerate(time_points):
                if t >= dose_time and t < dose_time + 8:  # 8 hour effect
                    # Simple trapezoid effect
                    time_since_dose = t - dose_time
                    if time_since_dose < 1:  # 1 hour onset
                        effect = 8.0 * (time_since_dose / 1.0)
                    elif time_since_dose < 5:  # 4 hour peak
                        effect = 8.0
                    else:  # 3 hour decline
                        decline_time = time_since_dose - 5
                        effect = 8.0 * (1 - decline_time / 3.0)
                    
                    pain_level[i] = max(pain_level[i], effect)
        
        # Create figure
        fig = go.Figure()
        
        # Add pain level curve
        fig.add_trace(go.Scatter(
            x=time_points,
            y=pain_level,
            mode='lines',
            name='Pain Relief',
            line=dict(color='#e74c3c', width=3),
            fill='tonexty',
            fillcolor='rgba(231, 76, 60, 0.2)',
            hovertemplate="<b>Pain Relief</b><br>Time: %{x:.1f}h<br>Level: %{y:.1f}/10<extra></extra>"
        ))
        
        # Update layout
        fig.update_layout(
            xaxis_title="Time (hours)",
            yaxis_title="Pain Relief Level (0-10)",
            title="Painkiller Timeline",
            yaxis=dict(range=[0, 10]),
            hovermode='closest',
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        print(f"Error updating painkiller timeline graph: {e}")
        # Return error graph
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error generating timeline: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            xaxis_title="Time (hours)",
            yaxis_title="Pain Relief Level (0-10)",
            title="Painkiller Timeline"
        )
        return fig

# Callback for pain relief windows
@app.callback(
    Output("pk-relief-windows", "children"),
    [Input("add-pk-btn", "n_clicks"),
     Input("clear-all-pk-btn", "n_clicks")]
)
def update_pk_relief_windows(add_clicks, clear_clicks):
    try:
        if not hasattr(simulator, 'painkillers') or not simulator.painkillers:
            return html.P("No pain relief windows found", className="text-muted")
        
        # Simple relief window calculation (placeholder)
        relief_windows = []
        for dose in simulator.painkillers:
            start_time = dose['time_hours']
            end_time = start_time + 8  # 8 hour effect
            relief_windows.append({
                'start': start_time,
                'end': end_time,
                'level': 'Strong'  # Placeholder
            })
        
        if not relief_windows:
            return html.P("No significant pain relief windows found", className="text-muted")
        
        # Display relief windows
        window_cards = []
        for i, window in enumerate(relief_windows):
            start_str = format_time_hours_minutes(window['start'])
            end_str = format_time_hours_minutes(window['end'])
            duration = window['end'] - window['start']
            duration_str = format_duration_hours_minutes(duration)
            
            window_card = dbc.Card([
                dbc.CardBody([
                    html.Strong(f"🟢 {window['level']} Relief"),
                    html.Br(),
                    html.Small(f"{start_str} to {end_str} (Duration: {duration_str})")
                ])
            ], className="mb-2")
            window_cards.append(window_card)
        
        return html.Div([
            html.H6("😌 Pain Relief Windows", className="mb-3"),
            html.Div(window_cards)
        ])
        
    except Exception as e:
        print(f"Error updating relief windows: {e}")
        return html.P("Error calculating relief windows", className="text-danger")

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
