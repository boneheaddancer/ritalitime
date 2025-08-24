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
import pandas as pd
import json
import base64
from datetime import time, datetime
import os

# Import existing modules
from medication_simulator import MedicationSimulator
import data_schema

# Performance optimization: Caching for timeline calculations
from functools import lru_cache
import time

# Cache for timeline calculations (5 minute TTL)
@lru_cache(maxsize=128)
def cached_timeline_calculation(medications_hash, stimulants_hash, timestamp):
    """Cached timeline calculation to improve performance"""
    try:
        # Generate timeline data
        sim = get_simulator()
        time_points, combined_effect = sim.generate_daily_timeline()
        return time_points, combined_effect
    except Exception as e:
        print(f"Error in cached timeline calculation: {e}")
        return np.array([]), np.array([])

def get_timeline_cache_key():
    """Generate cache key for timeline calculations"""
    try:
        # Create hash of current medications and stimulants
        sim = get_simulator()
        med_hash = hash(str(sim.medications))
        stim_hash = hash(str(sim.stimulants))
        # Round timestamp to 5-minute intervals for caching
        timestamp = int(time.time() // 300) * 300
        return med_hash, stim_hash, timestamp
    except Exception as e:
        print(f"Error generating cache key: {e}")
        return 0, 0, 0

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="RitaliTime - Medication Timeline Simulator"
)



# App configuration
app.config.suppress_callback_exceptions = True

# Enable callback exceptions suppression for dynamic elements
app.config.suppress_callback_exceptions = True

# Load custom header with Dexie.js and persistence
with open('assets/custom-header.html', 'r') as f:
    custom_header = f.read()

# Insert custom CSS into the header
custom_css = '''
        <style>
            /* Beautiful Custom Checkboxes */
            .custom-checkbox .form-check-input {
                width: 1.5em;
                height: 1.5em;
                margin-top: 0.25em;
                border: 2px solid #dee2e6;
                border-radius: 0.375rem;
                transition: all 0.2s ease-in-out;
                cursor: pointer;
            }
            
            .custom-checkbox .form-check-input:checked {
                background-color: var(--bs-primary);
                border-color: var(--bs-primary);
                box-shadow: 0 0 0 0.2rem rgba(var(--bs-primary-rgb), 0.25);
            }
            
            .custom-checkbox .form-check-input:focus {
                border-color: var(--bs-primary);
                box-shadow: 0 0 0 0.2rem rgba(var(--bs-primary-rgb), 0.25);
            }
            
            .custom-checkbox .form-check-input:hover:not(:checked) {
                border-color: var(--bs-primary);
                transform: scale(1.05);
            }
            
            .custom-checkbox .form-check-label {
                cursor: pointer;
                font-weight: 500;
                color: #495057;
                transition: color 0.2s ease-in-out;
            }
            
            .custom-checkbox .form-check-label:hover {
                color: var(--bs-primary);
            }
            
            /* Section styling */
            .text-primary { color: #0d6efd !important; }
            .text-success { color: #198754 !important; }
            .text-warning { color: #ffc107 !important; }
            
            /* Card enhancements */
            .card {
                border: none;
                box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
                transition: box-shadow 0.15s ease-in-out;
            }
            
            .card:hover {
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            }
            
            .card-header {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-bottom: 1px border-bottom: 1px solid #dee2e6;
            }
        </style>
'''

# Insert CSS into the header and set as index_string
custom_header = custom_header.replace('</head>', f'{custom_css}\n    </head>')
app.index_string = custom_header

# Initialize global simulator instance
simulator = None

def get_simulator():
    """Get or create simulator instance"""
    global simulator
    if simulator is None:
        simulator = MedicationSimulator()
        # Initialize painkillers list in simulator
        if not hasattr(simulator, 'painkillers'):
            simulator.painkillers = []
    return simulator

# Global state for persistence
app_state = {
    'medications': [],
    'stimulants': [],
    'painkillers': [],
    'app_settings': {},
    'user_preferences': {}
}

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

# Data persistence functions
def save_app_state():
    """Save current app state to IndexedDB via JavaScript"""
    try:
        sim = get_simulator()
        data_to_save = {
            'medications': sim.medications,
            'stimulants': sim.stimulants,
            'painkillers': sim.painkillers if hasattr(sim, 'painkillers') else [],
            'app_settings': app_state['app_settings'],
            'user_preferences': app_state['user_preferences'],
            'sleep_threshold': sim.sleep_threshold if hasattr(sim, 'sleep_threshold') else 0.3
        }
        
        # Store in app_state for immediate use
        app_state.update(data_to_save)
        
        # Return data for JavaScript callback
        return data_to_save
    except Exception as e:
        print(f"Error saving app state: {e}")
        return {}

def load_app_state():
    """Load app state from IndexedDB via JavaScript"""
    try:
        # This will be called when the app loads
        # For now, we'll use the existing data
        sim = get_simulator()
        
        # Load from app_state if available
        if app_state.get('medications'):
            sim.medications = app_state['medications']
        if app_state.get('stimulants'):
            sim.stimulants = app_state['stimulants']
        if app_state.get('painkillers'):
            sim.painkillers = app_state['painkillers']
        if app_state.get('sleep_threshold'):
            sim.sleep_threshold = app_state['sleep_threshold']
            
        return True
    except Exception as e:
        print(f"Error loading app state: {e}")
        return False

# Enhanced error handling and validation
def validate_medication_input(dose_time, med_name, dosage, onset_time, peak_time, duration, peak_effect):
    """Validate medication input parameters"""
    errors = []
    
    if not dose_time:
        errors.append("Dose time is required")
    if not med_name:
        errors.append("Medication name is required")
    if not dosage or dosage < 0.1 or dosage > 1000:
        errors.append("Dosage must be between 0.1 and 1000 mg")
    if onset_time < 0.1 or onset_time > 3.0:
        errors.append("Onset time must be between 0.1 and 3.0 hours")
    if peak_time < 0.5 or peak_time > 6.0:
        errors.append("Peak time must be between 0.5 and 6.0 hours")
    if duration < 1.0 or duration > 16.0:
        errors.append("Duration must be between 1.0 and 16.0 hours")
    if peak_effect < 0.1 or peak_effect > 2.0:
        errors.append("Peak effect must be between 0.1 and 2.0")
    
    return errors

def validate_stimulant_input(dose_time, stim_name, quantity, onset_time, peak_time, duration, peak_effect):
    """Validate stimulant input parameters"""
    errors = []
    
    if not dose_time:
        errors.append("Dose time is required")
    if not stim_name:
        errors.append("Stimulant name is required")
    if not quantity or quantity < 0.1 or quantity > 10:
        errors.append("Quantity must be between 0.1 and 10")
    if onset_time < 0.05 or onset_time > 2.0:
        errors.append("Onset time must be between 0.05 and 2.0 hours")
    if peak_time < 0.1 or peak_time > 6.0:
        errors.append("Peak time must be between 0.1 and 6.0 hours")
    if duration < 0.5 or duration > 24.0:
        errors.append("Duration must be between 0.5 and 24.0 hours")
    if peak_effect < 0.1 or peak_effect > 3.0:
        errors.append("Peak effect must be between 0.1 and 3.0")
    
    return errors

def validate_painkiller_input(dose_time, pk_name, pills):
    """Validate painkiller input parameters"""
    errors = []
    
    if not dose_time:
        errors.append("Dose time is required")
    if not pk_name:
        errors.append("Painkiller name is required")
    if not pills or pills < 1 or pills > 10:
        errors.append("Pill count must be between 1 and 10")
    
    return errors

# Helper functions for time formatting
def format_time_hours_minutes(hours):
    """Format decimal hours as HH:MM"""
    if hours < 0:
        return "00:00"
    total_minutes = int(hours * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"

def format_time_across_midnight(hours):
    """Format decimal hours as HH:MM, handling times across midnight"""
    if hours < 24:
        # Same day: use standard HH:MM format
        total_minutes = int(hours * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"
    else:
        # Next day: convert back to 0-23 format (e.g., 25:00 becomes 01:00)
        total_minutes = int(hours * 60)
        h = (total_minutes // 60) % 24
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
    # Responsive header
    dbc.Row([
        dbc.Col([
            html.H1("💊 RitaliTime", className="text-center mb-2 d-none d-md-block"),
            html.H2("💊 RitaliTime", className="text-center mb-2 d-md-none"),  # Smaller on mobile
            html.P("Medication Timeline Simulator", 
                   className="text-center text-muted mb-4")
        ])
    ]),
    
    # Navigation tabs with mobile optimization
    dbc.Tabs([
        dbc.Tab(label="ADHD Medications", tab_id="adhd-tab", className="px-2"),
        dbc.Tab(label="Settings", tab_id="settings-tab", className="px-2"),  # Shortened for mobile
    ], id="main-tabs", active_tab="adhd-tab", className="mb-3"),
    
    # Content area
    html.Div(id="tab-content"),
    
    # Hidden div for storing data
    dcc.Store(id="medication-store"),
    dcc.Store(id="stimulant-store"),
    dcc.Store(id="painkiller-store"),
    dcc.Store(id="app-settings-store"),
    
    # Hidden div to trigger timeline updates
    html.Div(id="timeline-trigger", style={"display": "none"}, children="initial"),
    
    # Hidden div to trigger painkiller updates
    html.Div(id="pk-trigger", style={"display": "none"}, children="initial"),
    
    # JavaScript callbacks for IndexedDB operations
    dcc.Store(id="db-operation-trigger"),
    html.Div(id="db-operation-result", style={"display": "none"}),
    

    
    # Success toast (always present in layout)
    html.Div(id="med-selection-toast"),
    
    # File download component
    dcc.Download(id="download-data"),
    
    # Performance optimization: Loading states
    dcc.Loading(
        id="loading-1",
        type="default",
        children=html.Div(id="loading-output")
    ),
    
], fluid=True, className="mt-3 px-2")  # Reduced margins for mobile

# Callback to render tab content
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "adhd-tab":
        return render_adhd_tab()
    elif active_tab == "settings-tab":
        return render_settings_tab()
    return "Select a tab"

# Initial callback for sleep analysis display and slider initialization (tab selection only)
@app.callback(
    [Output("sleep-analysis-display", "children"),
     Output("sleep-threshold-slider", "value")],
    Input("main-tabs", "active_tab"),
    prevent_initial_call=False
)
def initialize_sleep_components(active_tab):
    """Initialize sleep analysis display and slider when ADHD tab is selected"""
    if active_tab == "adhd-tab":
        try:
            sim = get_simulator()
            sleep_threshold = sim.sleep_threshold
            
            # Generate initial sleep analysis
            time_points, combined_effect = sim.generate_daily_timeline()
            
            if len(combined_effect) > 0:
                sleep_windows = sim.find_sleep_windows(combined_effect)
                
                if sleep_windows:
                    # Create initial sleep analysis display
                    sleep_info = []
                    for i, (start, end) in enumerate(sleep_windows):
                        duration = end - start
                        start_str = format_time_across_midnight(start)
                        end_str = format_time_across_midnight(end)
                        duration_str = format_duration_hours_minutes(duration)
                        
                        sleep_info.append({
                            "Window": f"#{i+1}",
                            "Start": start_str,
                            "End": end_str,
                            "Duration": duration_str
                        })
                    
                    total_sleep_time = sum(end - start for start, end in sleep_windows)
                    
                    if total_sleep_time >= 7:
                        summary_color = "success"
                        summary_icon = "✅"
                    elif total_sleep_time >= 5:
                        summary_color = "warning"
                        summary_icon = "⚠️"
                    else:
                        summary_color = "danger"
                        summary_icon = "❌"
                    
                    sleep_display = [
                        dbc.Alert([
                            html.Strong(f"{summary_icon} Total Sleep Time: {total_sleep_time:.1f} hours across {len(sleep_windows)} window(s)"),
                            html.Br(),
                            html.Small(f"Sleep threshold: {sleep_threshold:.2f}")
                        ], color=summary_color, className="mb-3"),
                        html.Div([
                            html.H6("Sleep Windows:", className="mb-2"),
                            dbc.Table.from_dataframe(
                                pd.DataFrame(sleep_info),
                                striped=True,
                                bordered=True,
                                hover=True,
                                size="sm"
                            )
                        ])
                    ]
                else:
                    sleep_display = [
                        dbc.Alert("No suitable sleep windows found with current threshold.", color="info"),
                        html.Small(f"Sleep threshold: {sleep_threshold:.2f}")
                    ]
            else:
                sleep_display = [
                    html.P("No timeline data available for sleep analysis.", className="text-muted")
                ]
            
            return sleep_display, sleep_threshold
                
        except Exception as e:
            print(f"Error initializing sleep components: {e}")
            return [
                html.P("Error initializing sleep analysis.", className="text-danger")
            ], 0.3
    
    return dash.no_update, dash.no_update

# Update callback for sleep analysis when timeline changes
@app.callback(
    Output("sleep-analysis-display", "children", allow_duplicate=True),
    Input("timeline-trigger", "children"),
    prevent_initial_call=True
)
def update_sleep_analysis_on_timeline_change(timeline_trigger):
    """Update sleep analysis display when timeline changes"""
    try:
        # Get current sleep threshold from simulator
        sim = get_simulator()
        sleep_threshold = sim.sleep_threshold
        
        # Generate sleep analysis
        time_points, combined_effect = sim.generate_daily_timeline()
        
        if len(combined_effect) > 0:
            # Find sleep windows
            sleep_windows = sim.find_sleep_windows(combined_effect)
            
            if sleep_windows:
                # Create sleep analysis display
                sleep_info = []
                for i, (start, end) in enumerate(sleep_windows):
                    duration = end - start
                    start_str = format_time_across_midnight(start)
                    end_str = format_time_across_midnight(end)
                    duration_str = format_duration_hours_minutes(duration)
                    
                    sleep_info.append({
                        "Window": f"#{i+1}",
                        "Start": start_str,
                        "End": end_str,
                        "Duration": duration_str
                    })
                
                # Create sleep summary
                total_sleep_time = sum(end - start for start, end in sleep_windows)
                sleep_summary = f"**Total Sleep Time**: {total_sleep_time:.1f} hours across {len(sleep_windows)} window(s)"
                
                if total_sleep_time >= 7:
                    summary_color = "success"
                    summary_icon = "✅"
                elif total_sleep_time >= 5:
                    summary_color = "warning"
                    summary_icon = "⚠️"
                else:
                    summary_color = "danger"
                    summary_icon = "❌"
                
                return [
                    dbc.Alert([
                        html.Strong(f"{summary_icon} {sleep_summary}"),
                        html.Br(),
                        html.Small(f"Sleep threshold: {sleep_threshold:.2f}")
                    ], color=summary_color, className="mb-3"),
                    html.Div([
                        html.H6("Sleep Windows:", className="mb-2"),
                        html.P(f"Sleep threshold: {sleep_threshold:.2f}"),
                        dbc.Table.from_dataframe(
                            pd.DataFrame(sleep_info),
                            striped=True,
                            bordered=True,
                            hover=True,
                            size="sm"
                        )
                    ])
                ]
            else:
                return [
                    dbc.Alert("No suitable sleep windows found with current threshold.", color="info"),
                    html.Small(f"Sleep threshold: {sleep_threshold:.2f}")
                ]
        else:
            return [
                html.P("No timeline data available for sleep analysis.", className="text-muted")
            ]
            
    except Exception as e:
        print(f"Error updating sleep analysis: {e}")
        return [
            html.P("Error updating sleep analysis.", className="text-danger")
        ]

def render_adhd_tab():
    """Render the ADHD medications tab"""
    return dbc.Row([
        dbc.Col([
            dbc.Row([
                # Left column - Input forms (responsive)
                dbc.Col([
                    render_medication_forms(),
                    html.Hr(),
                    render_stimulant_forms(),
                    html.Hr(),
                    render_painkiller_forms(),
                    html.Hr(),
                    render_sleep_settings(),
                    html.Div(id="sleep-analysis-display", className="mt-3"),
                ], width=12, lg=6),  # Full width on mobile, half on large screens
                
                # Right column - Current doses and timeline (responsive)
                dbc.Col([
                    render_current_doses(),
                    html.Hr(),
                    render_painkiller_doses(),
                    html.Hr(),
                    render_painkiller_timeline(),
                    html.Hr(),
                    render_timeline_visualization(),
                ], width=12, lg=6)  # Full width on mobile, half on large screens
            ])
        ], width=12)
    ])

def render_medication_forms():
    """Render medication input forms"""
    available_medications = []
    if medications_data.get('stimulants', {}).get('prescription_stimulants'):
        med_data = medications_data['stimulants']['prescription_stimulants']
        available_medications = [
            {"label": med_data[med].get('display_name', med), "value": med} 
            for med in med_data.keys()
        ]
    
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
                        type="text",
                        value="08:00",
                        placeholder="HH:MM",
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Medication Type"),
                    dcc.Dropdown(
                        id="med-name-dropdown",
                        options=[],
                        value=None,
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
            ),
            
            # Validation alert
            dbc.Alert(
                id="med-validation-alert",
                is_open=False,
                duration=4000,
                className="mt-3"
            )
        ])
    ], className="mb-4")

def render_stimulant_forms():
    """Render stimulant input forms"""
    available_stimulants = []
    if medications_data.get('stimulants', {}).get('common_stimulants'):
        stim_data = medications_data['stimulants']['common_stimulants']
        available_stimulants = [
            {"label": stim_data[stim].get('display_name', stim), "value": stim} 
            for stim in stim_data.keys()
        ]
    
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
                        type="text",
                        value="09:00",
                        placeholder="HH:MM",
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Stimulant"),
                    dcc.Dropdown(
                        id="stim-name-dropdown",
                        options=[],
                        value=None,
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
            html.Div(id="stim-component-section", className="mb-3", style={"display": "none"}),
            html.Div([
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
            ], id="stim-component-dropdown-container", style={"display": "none"}, className="mb-3"),
            
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
            ),
            
            # Validation alert
            dbc.Alert(
                id="stim-validation-alert",
                is_open=False,
                duration=4000,
                className="mt-3"
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



def render_painkiller_forms():
    """Render painkiller input forms"""
    available_painkillers = []
    if medications_data.get('painkillers'):
        pk_data = medications_data['painkillers']
        available_painkillers = [
            {"label": pk_data[pk].get('display_name', pk), "value": pk} 
            for pk in pk_data.keys()
        ]
    
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
                        type="text",
                        value="08:00",
                        placeholder="HH:MM",
                        className="form-control"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Painkiller Type"),
                    dcc.Dropdown(
                        id="pk-name-dropdown",
                        options=available_painkillers,
                        value=None,
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
            html.Div(id="pk-info-display", className="mb-3"),
            
            # Validation alert
            dbc.Alert(
                id="pk-validation-alert",
                is_open=False,
                duration=4000,
                className="mt-3"
            )
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

def render_sleep_settings():
    """Render sleep settings and threshold adjustment"""
    return dbc.Card([
        dbc.CardHeader([
            html.H4("😴 Sleep Settings", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Label("Sleep Threshold (effect level below which sleep is suitable)"),
            dcc.Slider(
                id="sleep-threshold-slider",
                min=0.1,
                max=1.0,
                step=0.05,
                value=0.3,
                marks={0.1: "0.1", 0.3: "0.3", 0.5: "0.5", 0.7: "0.7", 1.0: "1.0"},
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            html.Small("Adjust this threshold to see how it affects sleep quality analysis", className="text-muted")
        ])
    ], className="mb-4")

def render_settings_tab():
    """Render the settings tab"""
    return dbc.Row([
        dbc.Col([
            html.H4("⚙️ Settings", className="mb-4"),
            
            # Medication Selection Card
            dbc.Card([
                dbc.CardHeader([
                    html.H5("💊 Medication Selection", className="mb-0")
                ]),
                dbc.CardBody([
                    html.P("Select which medications you'd like to have available in your dropdowns:", className="text-muted mb-3"),
                    
                    # Prescription Stimulants Section
                    html.H6("Prescription Stimulants", className="text-primary mb-3"),
                    dbc.Col([
                        dbc.Checkbox(
                            id=f"med-check-{med_key}",
                            label=med_data.get('display_name', med_key),
                            value=True,
                            className="custom-checkbox mb-2",
                            style={
                                '--bs-primary': '#0d6efd',
                                '--bs-primary-rgb': '13, 110, 253'
                            }
                        ) for med_key, med_data in medications_data.get('stimulants', {}).get('prescription_stimulants', {}).items()
                    ], width=6, className="mb-4"),
                    
                    # Common Stimulants Section
                    html.H6("Common Stimulants", className="text-success mb-3"),
                    dbc.Col([
                        dbc.Checkbox(
                            id=f"stim-check-{stim_key}",
                            label=stim_data.get('display_name', stim_key),
                            value=True,
                            className="custom-checkbox mb-2",
                            style={
                                '--bs-primary': '#198754',
                                '--bs-primary-rgb': '25, 135, 84'
                            }
                        ) for stim_key, stim_data in medications_data.get('stimulants', {}).get('common_stimulants', {}).items()
                    ], width=6, className="mb-4"),
                    
                    # Painkillers Section
                    html.H6("Painkillers", className="text-warning mb-3"),
                    dbc.Col([
                        dbc.Checkbox(
                            id=f"pk-check-{pk_key}",
                            label=pk_data.get('display_name', pk_key),
                            value=True,
                            className="custom-checkbox mb-2",
                            style={
                                '--bs-primary': '#ffc107',
                                '--bs-primary-rgb': '255, 193, 7'
                            }
                        ) for pk_key, pk_data in medications_data.get('painkillers', {}).items()
                    ], width=6, className="mb-3"),
                    
                    dbc.Button("Save Medication Selection", id="save-med-selection-btn", color="primary", className="w-100")
                ])
            ], className="mb-4"),
            
            # Data Export/Import Card
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Data Export/Import", className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Export Data"),
                            dbc.Button("Export All Data", id="export-data-btn", color="primary", className="w-100"),
                            html.Br(),
                            html.Small("Export all current medications, stimulants, and painkillers to JSON.")
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Import Data"),
                            dcc.Upload(
                                id="upload-data",
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select Files')
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'margin': '10px'
                                },
                                multiple=False
                            ),
                            html.Br(),
                            html.Small("Import medications, stimulants, and painkillers from a JSON file.")
                        ], width=6)
                    ])
                ]),
                html.Hr(),
                dbc.CardHeader([
                    html.H5("User Preferences", className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Label("Default Dose Time (ADHD Medications)"),
                    dcc.Input(
                        id="default-med-time",
                        type="text",
                        value="08:00",
                        placeholder="HH:MM",
                        className="form-control"
                    ),
                    html.Br(),
                    dbc.Label("Default Dose Time (Stimulants)"),
                    dcc.Input(
                        id="default-stim-time",
                        type="text",
                        value="09:00",
                        placeholder="HH:MM",
                        className="form-control"
                    ),
                    html.Br(),
                    dbc.Label("Default Dose Time (Painkillers)"),
                    dcc.Input(
                        id="default-pk-time",
                        type="text",
                        value="08:00",
                        placeholder="HH:MM",
                        className="form-control"
                    ),
                    html.Br(),
                    dbc.Label("Default Pill Count (Painkillers)"),
                    dcc.Input(
                        id="default-pills",
                        type="number",
                        min=1,
                        max=10,
                        step=1,
                        value=1,
                        className="form-control"
                    ),
                    html.Br(),
                    dbc.Button("Save Preferences", id="save-prefs-btn", color="success", className="w-100"),
                    html.Hr(),
                    html.H6("Data Management", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Load from IndexedDB", id="load-db-btn", color="info", className="w-100 mb-2"),
                            html.Small("Load your saved data from browser storage", className="text-muted")
                        ], width=6),
                        dbc.Col([
                            dbc.Button("Clear All Data", id="clear-db-btn", color="danger", className="w-100 mb-2"),
                            html.Small("Clear all saved data (cannot be undone)", className="text-muted")
                        ], width=6)
                    ])
                ])
            ])
        ], width=12)
    ])

# Callback for sleep threshold updates
@app.callback(
    Output("app-settings-store", "data", allow_duplicate=True),
    Input("sleep-threshold-slider", "value"),
    prevent_initial_call=True
)
def update_sleep_threshold(sleep_threshold):
    """Update sleep threshold in app state"""
    if sleep_threshold is not None:
        app_state['sleep_threshold'] = sleep_threshold
        return app_state
    
    return no_update

# Callback for saving medication selection and showing toast
@app.callback(
    [Output("app-settings-store", "data", allow_duplicate=True),
     Output("med-selection-toast", "children")],
    Input("save-med-selection-btn", "n_clicks"),
    [State(f"med-check-{med_key}", "value") for med_key in medications_data.get('stimulants', {}).get('prescription_stimulants', {}).keys()] +
    [State(f"stim-check-{stim_key}", "value") for stim_key in medications_data.get('stimulants', {}).get('common_stimulants', {}).keys()] +
    [State(f"pk-check-{pk_key}", "value") for pk_key in medications_data.get('painkillers', {}).keys()],
    prevent_initial_call=True
)
def save_medication_selection_and_toast(n_clicks, *checkbox_values):
    """Save medication selection preferences and show success toast"""
    print(f"Save button clicked! n_clicks: {n_clicks}")
    print(f"Checkbox values: {checkbox_values}")
    
    if not n_clicks or n_clicks is None:
        print("No clicks detected, returning no_update")
        return no_update, ""
    
    print(f"Button clicked {n_clicks} times!")
    
    # Get all medication keys
    med_keys = list(medications_data.get('stimulants', {}).get('prescription_stimulants', {}).keys())
    stim_keys = list(medications_data.get('stimulants', {}).get('common_stimulants', {}).keys())
    pk_keys = list(medications_data.get('painkillers', {}).keys())
    
    print(f"Med keys: {med_keys}")
    print(f"Stim keys: {stim_keys}")
    print(f"PK keys: {pk_keys}")
    
    # Create selection mapping
    med_selection = {}
    for i, key in enumerate(med_keys):
        med_selection[key] = checkbox_values[i] if checkbox_values[i] is not None else True
    
    stim_selection = {}
    for i, key in enumerate(stim_keys):
        stim_selection[key] = checkbox_values[len(med_keys) + i] if checkbox_values[len(med_keys) + i] is not None else True
    
    pk_selection = {}
    for i, key in enumerate(pk_keys):
        pk_selection[key] = checkbox_values[len(med_keys) + len(stim_keys) + i] if checkbox_values[len(med_keys) + len(stim_keys) + i] is not None else True
    
    print(f"Med selection: {med_selection}")
    print(f"Stim selection: {stim_selection}")
    print(f"PK selection: {pk_selection}")
    
    # Update app state
    app_state['app_settings']['medication_selection'] = {
        'prescription_stimulants': med_selection,
        'common_stimulants': stim_selection,
        'painkillers': pk_selection
    }
    
    print(f"Updated app state: {app_state['app_settings']['medication_selection']}")
    
    # Create success toast
    toast = dbc.Toast(
        "Medication selection saved successfully! Your dropdowns have been updated.",
        id="med-selection-toast",
        header="Success",
        is_open=True,
        duration=3000,
        icon="success",
        style={"position": "fixed", "top": 66, "right": 10, "width": 350}
    )
    
    # Return the updated settings data
    updated_settings = {
        'medication_selection': app_state['app_settings']['medication_selection']
    }
    
    print(f"Returning updated settings: {updated_settings}")
    return updated_settings, toast

# Callback to update medication dropdown options
@app.callback(
    Output("med-name-dropdown", "options"),
    [Input("app-settings-store", "data"),
     Input("main-tabs", "active_tab")]
)
def update_medication_dropdown(settings_data, active_tab):
    """Update medication dropdown options based on selection"""
    print(f"Medication dropdown callback triggered - active_tab: {active_tab}")
    print(f"Settings data: {settings_data}")
    
    # Only update when ADHD tab is active
    if active_tab != "adhd-tab":
        print(f"Wrong tab ({active_tab}), returning no_update")
        return no_update
    
    if not settings_data or 'app_settings' not in settings_data or 'medication_selection' not in settings_data['app_settings']:
        print("No settings data or medication selection, showing all medications")
        # Default: show all medications
        return [
            {'label': med_data.get('display_name', med_key), 'value': med_key}
            for med_key, med_data in medications_data.get('stimulants', {}).get('prescription_stimulants', {}).items()
        ]
    
    selection = settings_data['app_settings']['medication_selection']
    print(f"Using selection: {selection}")
    
    options = []
    
    # Add selected prescription stimulants
    for med_key, is_selected in selection.get('prescription_stimulants', {}).items():
        if is_selected:
            med_data = medications_data['stimulants']['prescription_stimulants'].get(med_key, {})
            options.append({
                'label': med_data.get('display_name', med_key),
                'value': med_key
            })
    
    print(f"Returning options: {options}")
    return options

# Callback to initialize medication selection checkboxes
@app.callback(
    [Output(f"med-check-{med_key}", "value") for med_key in medications_data.get('stimulants', {}).get('prescription_stimulants', {}).keys()] +
    [Output(f"stim-check-{stim_key}", "value") for stim_key in medications_data.get('stimulants', {}).get('common_stimulants', {}).keys()] +
    [Output(f"pk-check-{pk_key}", "value") for pk_key in medications_data.get('painkillers', {}).keys()],
    [Input("app-settings-store", "data"),
     Input("main-tabs", "active_tab")]
)
def initialize_medication_selection(settings_data, active_tab):
    """Initialize medication selection checkboxes with saved values"""
    # Only run when settings tab is active
    if active_tab != "settings-tab":
        return no_update
    
    if not settings_data or 'app_settings' not in settings_data or 'medication_selection' not in settings_data['app_settings']:
        # Default: all checked
        med_keys = list(medications_data.get('stimulants', {}).get('prescription_stimulants', {}).keys())
        stim_keys = list(medications_data.get('stimulants', {}).get('common_stimulants', {}).keys())
        pk_keys = list(medications_data.get('painkillers', {}).keys())
        return [True] * (len(med_keys) + len(stim_keys) + len(pk_keys))
    
    selection = settings_data['app_settings']['medication_selection']
    
    # Get values for each category
    med_values = [selection.get('prescription_stimulants', {}).get(key, True) for key in medications_data.get('stimulants', {}).get('prescription_stimulants', {}).keys()]
    stim_values = [selection.get('common_stimulants', {}).get(key, True) for key in medications_data.get('stimulants', {}).get('common_stimulants', {}).keys()]
    pk_values = [selection.get('painkillers', {}).get(key, True) for key in medications_data.get('painkillers', {}).keys()]
    
    return med_values + stim_values + pk_values

# Callback to update stimulant dropdown options
@app.callback(
    Output("stim-name-dropdown", "options"),
    [Input("app-settings-store", "data"),
     Input("main-tabs", "active_tab")]
)
def update_stimulant_dropdown(settings_data, active_tab):
    """Update stimulant dropdown options based on selection"""
    # Only update when ADHD tab is active
    if active_tab != "adhd-tab":
        return no_update
    
    if not settings_data or 'app_settings' not in settings_data or 'medication_selection' not in settings_data['app_settings']:
        # Default: show all stimulants
        return [
            {'label': stim_data.get('display_name', stim_key), 'value': stim_key}
            for stim_key, stim_data in medications_data.get('stimulants', {}).get('common_stimulants', {}).items()
        ]
    
    selection = settings_data['app_settings']['medication_selection']
    options = []
    
    # Add selected common stimulants
    for stim_key, is_selected in selection.get('common_stimulants', {}).items():
        if is_selected:
            stim_data = medications_data['stimulants']['common_stimulants'].get(stim_key, {})
            options.append({
                'label': stim_data.get('display_name', stim_key),
                'value': stim_key
            })
    
    return options

# Callback to update painkiller dropdown options
@app.callback(
    Output("pk-name-dropdown", "options"),
    Input("app-settings-store", "data")
)
def update_painkiller_dropdown(settings_data):
    """Update painkiller dropdown options based on selection"""
    
    if not settings_data or 'app_settings' not in settings_data or 'medication_selection' not in settings_data['app_settings']:
        # Default: show all painkillers
        return [
            {'label': pk_data.get('display_name', pk_key), 'value': pk_key}
            for pk_key, pk_data in medications_data.get('painkillers', {}).items()
        ]
    
    selection = settings_data['app_settings']['medication_selection']
    options = []
    
    # Add selected painkillers
    for pk_key, is_selected in selection.get('painkillers', {}).items():
        if is_selected:
            pk_data = medications_data['painkillers'].get(pk_key, {})
            options.append({
                'label': pk_data.get('display_name', pk_key),
                'value': pk_key
            })
    
    return options

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
    [Output("stim-component-section", "children"),
     Output("stim-component-dropdown-container", "style")],
    Input("stim-name-dropdown", "value")
)
def update_stim_component(stim_name):
    if stim_name and stim_name in ['redbull', 'monster']:
        return "", {"display": "block"}
    return "", {"display": "none"}



# Callback for adding medication
@app.callback(
    [Output("current-doses-display", "children", allow_duplicate=True),
     Output("med-time-input", "value"),
     Output("med-name-dropdown", "value"),
     Output("med-dosage-input", "value"),
     Output("med-onset-slider", "value"),
     Output("med-peak-slider", "value"),
     Output("med-duration-slider", "value"),
     Output("med-effect-slider", "value"),
     Output("med-validation-alert", "children"),
     Output("med-validation-alert", "is_open"),
     Output("timeline-trigger", "children", allow_duplicate=True)],
    [Input("add-med-btn", "n_clicks")],
    [State("med-time-input", "value"),
     State("med-name-dropdown", "value"),
     State("med-dosage-input", "value"),
     State("med-onset-slider", "value"),
     State("med-peak-slider", "value"),
     State("med-duration-slider", "value"),
     State("med-effect-slider", "value")],
    prevent_initial_call=True
)
def add_medication(n_clicks, dose_time, med_name, dosage, onset_time, peak_time, duration, peak_effect):
    print(f"DEBUG: add_medication called with n_clicks={n_clicks}")
    if not n_clicks:
        # Initial load - return current doses display
        print("DEBUG: Initial load, returning current state without changes")
        return render_doses_list(), "08:00", None, 20.0, 1.0, 2.0, 8.0, 1.0, "", False, dash.no_update
    
    if not all([dose_time, med_name, dosage]):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, "Please fill in all required fields", True, dash.no_update
    
    # Validate input
    validation_errors = validate_medication_input(dose_time, med_name, dosage, onset_time, peak_time, duration, peak_effect)
    if validation_errors:
        error_message = html.Ul([html.Li(error) for error in validation_errors])
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error_message, True, dash.no_update
    
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
        
        print(f"DEBUG: Adding medication to simulator: {med_name}, {dosage}mg at {dose_time}")
        sim = get_simulator()
        sim.add_medication(
            dose_time, float(dosage), medication_name=med_name, custom_params=custom_params
        )
        print(f"DEBUG: Medication added. Simulator now has {len(sim.medications)} medications")
        
        # Save to app state for persistence
        app_state['medications'] = sim.medications.copy()
        
        # Trigger timeline update
        timeline_trigger = f"med-added-{datetime.now().timestamp()}"
        
        # Don't reset form values - keep them for the next dose
        return render_doses_list(), dose_time, med_name, dosage, onset_time, peak_time, duration, peak_effect, dbc.Alert("Medication added successfully!", color="success"), True, timeline_trigger
        
    except Exception as e:
        print(f"Error adding medication: {e}")
        error_message = f"Error adding medication: {str(e)}"
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert(error_message, color="danger"), True, dash.no_update



# Callback for adding stimulant
@app.callback(
    [Output("current-doses-display", "children", allow_duplicate=True),
     Output("stim-time-input", "value"),
     Output("stim-name-dropdown", "value"),
     Output("stim-quantity-input", "value"),
     Output("stim-onset-slider", "value"),
     Output("stim-peak-slider", "value"),
     Output("stim-duration-slider", "value"),
     Output("stim-effect-slider", "value"),
     Output("stim-validation-alert", "children"),
     Output("stim-validation-alert", "is_open"),
     Output("timeline-trigger", "children", allow_duplicate=True)],
    [Input("add-stim-btn", "n_clicks")],
    [State("stim-time-input", "value"),
     State("stim-name-dropdown", "value"),
     State("stim-quantity-input", "value"),
     State("stim-onset-slider", "value"),
     State("stim-peak-slider", "value"),
     State("stim-duration-slider", "value"),
     State("stim-effect-slider", "value"),
     State("stim-component-dropdown", "value")],
    prevent_initial_call=True
)
def add_stimulant(n_clicks, dose_time, stim_name, quantity, onset_time, peak_time, duration, peak_effect, component_name):
    if not n_clicks:
        # Initial load - return current doses display
        return render_doses_list(), "09:00", None, 1.0, 0.17, 1.0, 6.0, 0.75, "", False, dash.no_update
    
    if not all([dose_time, stim_name, quantity]):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, "Please fill in all required fields", True, dash.no_update
    
    # Validate input
    validation_errors = validate_stimulant_input(dose_time, stim_name, quantity, onset_time, peak_time, duration, peak_effect)
    if validation_errors:
        error_message = html.Ul([html.Li(error) for error in validation_errors])
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error_message, True, dash.no_update
    
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
        
        sim = get_simulator()
        sim.add_stimulant(
            dose_time, stim_name, component_name, float(quantity), custom_params
        )
        
        # Save to app state for persistence
        app_state['stimulants'] = sim.stimulants.copy()
        
        # Trigger timeline update
        timeline_trigger = f"stim-added-{datetime.now().timestamp()}"
        
        # Don't reset form values - keep them for the next dose
        return render_doses_list(), dose_time, stim_name, quantity, onset_time, peak_time, duration, peak_effect, dbc.Alert("Stimulant added successfully!", color="success"), True, timeline_trigger
        
    except Exception as e:
        print(f"Error adding stimulant: {e}")
        error_message = f"Error adding stimulant: {str(e)}"
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error_message, True, dash.no_update

# Callback for adding painkiller


# Callback for clearing all doses
@app.callback(
    [Output("current-doses-display", "children", allow_duplicate=True),
     Output("timeline-trigger", "children", allow_duplicate=True)],
    Input("clear-all-doses-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_all_doses(n_clicks):
    if n_clicks:
        sim = get_simulator()
        sim.clear_all_doses()
        # Update app state for persistence
        app_state['medications'] = []
        app_state['stimulants'] = []
        
        # Trigger timeline update
        timeline_trigger = f"doses-cleared-{datetime.now().timestamp()}"
        
        return render_doses_list(), timeline_trigger
    return render_doses_list(), dash.no_update



# Enhanced timeline callback with caching and visual enhancements
@app.callback(
    Output("timeline-graph", "figure"),
    [Input("show-individual-curves", "value"),
     Input("timeline-trigger", "children"),
     Input("sleep-threshold-slider", "value")]
)
def update_timeline_graph(show_individual, timeline_trigger, sleep_threshold):
    try:
        # Clear the cache to ensure fresh calculation
        cached_timeline_calculation.cache_clear()
        
        # Generate timeline data directly from simulator
        sim = get_simulator()
        print(f"DEBUG: Generating timeline for {len(sim.medications)} medications and {len(sim.stimulants)} stimulants")
        print(f"DEBUG: Medications: {sim.medications}")
        print(f"DEBUG: Stimulants: {sim.stimulants}")
        print(f"DEBUG: Timeline trigger value: {timeline_trigger}")
        print(f"DEBUG: Timeline generation started at: {datetime.now().timestamp()}")
        time_points, combined_effect = sim.generate_daily_timeline()
        print(f"DEBUG: Timeline generated - time_points: {len(time_points)}, combined_effect: {len(combined_effect)}")
        if len(combined_effect) > 0:
            print(f"DEBUG: Combined effect range: {np.min(combined_effect):.6f} to {np.max(combined_effect):.6f}")
            print(f"DEBUG: Non-zero effects: {np.count_nonzero(combined_effect)}")
        print(f"DEBUG: Timeline generation completed at: {datetime.now().timestamp()}")
        
        # Check simulator state after timeline generation
        sim_after = get_simulator()
        print(f"DEBUG: Simulator state after timeline: {len(sim_after.medications)} medications, {len(sim_after.stimulants)} stimulants")
        
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
            individual_curves = sim.get_individual_curves()
            
            # Color palette for different doses
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
            
            for i, (label, curve) in enumerate(individual_curves):
                color = colors[i % len(colors)]
                
                # Add filled area under the curve
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
                    customdata=[format_time_across_midnight(x) for x in time_points],
                    hovertemplate=f"<b>{label}</b><br>Time: %{{customdata}}<br>Effect: %{{y:.3f}}<extra></extra>"
                ))
        
        # Add combined effect curve with enhanced styling
        fig.add_trace(go.Scatter(
            x=time_points,
            y=combined_effect,
            mode='lines',
            name='Combined Effect',
            line=dict(color='blue', width=3),
            fill='tonexty',
            fillcolor='rgba(30, 144, 255, 0.1)',  # Light blue fill
            customdata=[format_time_across_midnight(x) for x in time_points],
            hovertemplate="<b>Combined Effect</b><br>Time: %{customdata}<br>Effect: %{y:.3f}<extra></extra>"
        ))
        
        # Add sleep threshold line (get from slider input or simulator)
        if sleep_threshold is None:
            sleep_threshold = app_state.get('sleep_threshold', getattr(sim, 'sleep_threshold', 0.3))
        fig.add_hline(
            y=sleep_threshold,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Sleep Threshold ({sleep_threshold:.2f})",
            annotation_position="top right"
        )
        
        # Add sleep quality indicator (inverted effect level for sleep)
        sleep_quality = np.maximum(0, sleep_threshold - combined_effect)
        fig.add_trace(go.Scatter(
            x=time_points,
            y=sleep_quality,
            mode='lines',
            name='Sleep Quality',
            line=dict(color='blue', width=2, dash='dot'),
            yaxis='y2',
            customdata=[format_time_across_midnight(x) for x in time_points],
            hovertemplate="<b>Sleep Quality</b><br>Time: %{customdata}<br>Quality: %{y:.3f}<extra></extra>"
        ))
        
        # Add vertical rules for key time points
        all_doses = sim.get_all_doses()
        for dose in all_doses:
            dose_time_hours = sim._minutes_to_decimal_hours(dose['time'])
            
            # Calculate Tmax (peak time)
            if dose['type'] == 'medication':
                tmax = dose_time_hours + dose.get('peak_time', 2.0)
            else:
                tmax = dose_time_hours + dose.get('peak_time', 1.0)
            
            # Add Tmax vertical line
            fig.add_vline(
                x=tmax,
                line_dash="dot",
                line_color="orange",
                annotation_text=f"Tmax: {format_time_across_midnight(tmax)}",
                annotation_position="top"
            )
            
            # Add dose time vertical line
            fig.add_vline(
                x=dose_time_hours,
                line_dash="solid",
                line_color="green",
                annotation_text=f"Dose: {format_time_across_midnight(dose_time_hours)}",
                annotation_position="bottom"
            )
        
        # Update layout with enhanced features
        fig.update_layout(
            title="Medication & Stimulant Effect Timeline",
            xaxis_title="Time (hours)",
            yaxis_title="Effect Level",
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            yaxis2=dict(
                title="Sleep Quality",
                overlaying="y",
                side="right",
                range=[0, sleep_threshold],
                tickformat=".2f"
            ),
            # Mobile optimization
            margin=dict(l=50, r=50, t=80, b=50),
            height=500  # Increased height for better visibility
        )
        
        # Update x-axis to show dynamic time labels
        if len(time_points) > 0:
            start_hour = time_points.min()
            end_hour = time_points.max()
            
            # Create ticks that span the full range
            if end_hour - start_hour <= 24:
                # For 24h or less, use 2-hour spacing
                tick_hours = list(range(int(start_hour), int(end_hour) + 1, 2))
            else:
                # For longer periods, use 3-4 hour spacing
                spacing = max(2, int((end_hour - start_hour) // 8))
                tick_hours = list(range(int(start_hour), int(end_hour) + 1, spacing))
            
            # Ensure we have start and end points
            if start_hour not in tick_hours:
                tick_hours.insert(0, start_hour)
            if end_hour not in tick_hours:
                tick_hours.append(end_hour)
                
            tick_labels = [format_time_across_midnight(hour) for hour in tick_hours]
            
            fig.update_xaxes(
                tickmode='array',
                tickvals=tick_hours,
                ticktext=tick_labels,
                range=[start_hour, end_hour]
            )
        else:
            # Fallback to 24h format
            fig.update_xaxes(
                tickmode='array',
                tickvals=list(range(0, 25, 2)),
                ticktext=[format_time_across_midnight(h) for h in range(0, 25, 2)]
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
        sim = get_simulator()
        all_doses = sim.get_all_doses()
        if not all_doses:
            return html.P("No doses added yet. Add some medications or stimulants above!", className="text-muted")
        
        dose_cards = []
        for dose in all_doses:
            # Get the pretty name for the medication/stimulant
            display_name = dose.get('medication_name', dose.get('stimulant_name', 'Unknown'))
            if dose['type'] == 'medication' and medications_data.get('stimulants', {}).get('prescription_stimulants', {}).get(display_name):
                display_name = medications_data['stimulants']['prescription_stimulants'][display_name].get('display_name', display_name)
            elif dose['type'] == 'stimulant' and medications_data.get('stimulants', {}).get('common_stimulants', {}).get(display_name):
                display_name = medications_data['stimulants']['common_stimulants'][display_name].get('display_name', display_name)
            
            dose_card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Strong(f"{'💊' if dose['type'] == 'medication' else '☕'} {display_name}"),
                            html.Br(),
                            html.Small(f"{dose.get('dosage', dose.get('quantity', 'Unknown'))} {'mg' if dose['type'] == 'medication' else 'units'} at {dose.get('time', 'Unknown time')}")
                        ], width=8),
                        dbc.Col([
                            dbc.Button("Delete", id={"type": "remove-dose", "index": dose['id']}, 
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
        sim = get_simulator()
        if not hasattr(sim, 'painkillers') or not sim.painkillers:
            return html.P("No painkillers added yet. Add some above!", className="text-muted")
        
        dose_cards = []
        for dose in sim.painkillers:
            # Get the pretty name for the painkiller
            display_name = dose['name']
            if medications_data.get('painkillers', {}).get(display_name):
                display_name = medications_data['painkillers'][display_name].get('display_name', display_name)
            
            dose_card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Strong(f"💊 {display_name}"),
                            html.Br(),
                            html.Small(f"{dose.get('pills', 1)} pill(s) at {dose.get('time', 'Unknown time')}")
                        ], width=8),
                        dbc.Col([
                            dbc.Button("Delete", id={"type": "remove-pk-dose", "index": dose['id']}, 
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

# Unified callback for all painkiller operations
@app.callback(
    [Output("pk-dosage-display", "children"),
     Output("pk-info-display", "children"),
     Output("pk-timeline-graph", "figure"),
     Output("pk-relief-windows", "children"),
     Output("current-pk-doses-display", "children", allow_duplicate=True)],
    [Input("add-pk-btn", "n_clicks"),
     Input("clear-all-pk-btn", "n_clicks"),
     Input({"type": "remove-pk-dose", "index": ALL}, "n_clicks")],
    [State("pk-name-dropdown", "value"),
     State("pk-pills-input", "value"),
     State("pk-time-input", "value")],
    prevent_initial_call=True
)
def update_painkiller_components(add_clicks, clear_clicks, remove_clicks, pk_name, pills, dose_time):
    """Unified callback for all painkiller components"""
    
    print(f"DEBUG: update_painkiller_components called with pk_name={pk_name}, pills={pills}, add_clicks={add_clicks}, clear_clicks={clear_clicks}")
    
    # Handle case where elements might not exist yet
    if pk_name is None and pills is None and add_clicks is None and clear_clicks is None:
        return "", "", dash.no_update, "", dash.no_update
    
    # Handle removing individual painkiller doses
    if remove_clicks and any(remove_clicks):
        try:
            ctx = callback_context
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                button_data = json.loads(button_id)
                
                if button_data['type'] == 'remove-pk-dose':
                    dose_id = button_data['index']
                    sim = get_simulator()
                    if hasattr(sim, 'painkillers') and sim.painkillers:
                        sim.painkillers = [d for d in sim.painkillers if d['id'] != dose_id]
                        print(f"DEBUG: Removed painkiller dose with ID: {dose_id}")
                        
                        # Update app state
                        app_state['painkillers'] = sim.painkillers.copy()
        except Exception as e:
            print(f"Error removing painkiller dose: {e}")
            print(f"DEBUG: Exception details: {e}")
            import traceback
            traceback.print_exc()
    
    # Handle clearing all painkillers
    if clear_clicks:
        try:
            sim = get_simulator()
            sim.clear_all_painkillers()
            # Update app state for persistence
            app_state['painkillers'] = []
            print("DEBUG: Cleared all painkillers")
        except Exception as e:
            print(f"Error clearing painkillers: {e}")
    
    # Handle adding painkillers
    if add_clicks and pk_name and pills:
        try:
            sim = get_simulator()
            
            # Convert time string to hours (use input value or default to 08:00)
            if not dose_time:
                dose_time = "08:00"  # Default time
            hour, minute = map(int, dose_time.split(':'))
            time_hours = hour + minute / 60.0
            
            # Create painkiller dose entry
            dose_entry = {
                'id': sim.get_next_dose_id(),
                'time_hours': time_hours,
                'name': pk_name,
                'pills': int(pills),
                'time': dose_time
            }
            
            sim.painkillers.append(dose_entry)
            
            # Save to app state for persistence
            app_state['painkillers'] = sim.painkillers.copy()
            
            print(f"DEBUG: Added painkiller: {pk_name}, {pills} pills")
            print(f"DEBUG: Simulator now has {len(sim.painkillers)} painkillers: {sim.painkillers}")
            print(f"DEBUG: App state painkillers: {app_state['painkillers']}")
        except Exception as e:
            print(f"Error adding painkiller: {e}")
    else:
        print(f"DEBUG: Not adding painkiller: add_clicks={add_clicks}, pk_name={pk_name}, pills={pills}")
        print(f"DEBUG: Current simulator painkillers: {get_simulator().painkillers}")
    
    # Update dosage display
    dosage_display = ""
    if pk_name and pills:
        try:
            if medications_data.get('painkillers', {}).get(pk_name):
                pk_info = medications_data['painkillers'][pk_name]
                base_dosage = pk_info.get('standard_dose_mg', 0)
                
                if base_dosage > 0:
                    total_dosage = base_dosage * pills
                    dosage_display = dbc.Alert([
                        html.Strong(f"Total Dosage: {total_dosage}mg"),
                        html.Br(),
                        html.Small(f"({base_dosage}mg per pill)")
                    ], color="info")
        except Exception as e:
            print(f"Error calculating dosage: {e}")
    
    # Update info display
    info_display = ""
    if pk_name:
        try:
            if medications_data.get('painkillers', {}).get(pk_name):
                pk_info = medications_data['painkillers'][pk_name]
                
                onset_hours = pk_info.get('onset_min', 60) / 60.0
                peak_time_hours = pk_info.get('t_peak_min', 120) / 60.0
                peak_duration_hours = pk_info.get('peak_duration_min', 60) / 60.0
                duration_hours = pk_info.get('duration_min', 480) / 60.0
                
                info_display = dbc.Alert([
                    html.Strong(f"{pk_name}:"),
                    html.Br(),
                    html.Small(f"Onset {format_time_across_midnight(onset_hours)}, Peak at {format_time_across_midnight(peak_time_hours)}, Peak duration {format_duration_hours_minutes(peak_duration_hours)}, Total {format_duration_hours_minutes(duration_hours)}")
                ], color="info")
        except Exception as e:
            print(f"Error loading painkiller info: {e}")
    
    # Update timeline graph - always update when there are painkillers
    timeline_figure = dash.no_update
    try:
        sim = get_simulator()
        if not hasattr(sim, 'painkillers') or not sim.painkillers:
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
            timeline_figure = fig
        else:
            # Generate painkiller timeline - expand to show full day including midnight crossing
            # Find the earliest and latest times to show
            all_times = [dose['time_hours'] for dose in sim.painkillers]
            earliest_time = min(all_times)
            latest_time = max(all_times)
            
            # If we have doses that span across midnight, show the full 24-hour period
            if latest_time - earliest_time > 12:  # More than 12 hours apart
                time_points = np.arange(0, 24.1, 0.1)
            else:
                # Show from earliest dose to latest dose + effect duration
                start_time = max(0, earliest_time - 1)  # 1 hour before earliest dose
                end_time = min(24, latest_time + 8)     # 8 hours after latest dose
                time_points = np.arange(start_time, end_time + 0.1, 0.1)
            
            pain_level = np.zeros_like(time_points)
            
            # Simple pain level calculation
            for dose in sim.painkillers:
                dose_time = dose['time_hours']
                for i, t in enumerate(time_points):
                    # For doses after midnight (before noon), treat them as next day
                    # This ensures 01:00 appears after 17:25 in the timeline
                    normalized_dose_time = dose_time
                    if dose_time < 12:  # Dose is before noon (likely after midnight)
                        # Check if this dose should be treated as next day
                        # If we have other doses after noon, this one is from next day
                        has_afternoon_doses = any(d['time_hours'] > 12 for d in sim.painkillers)
                        if has_afternoon_doses:
                            normalized_dose_time = dose_time + 24
                    
                    # Calculate time difference
                    time_diff = t - normalized_dose_time
                    
                    if time_diff >= 0 and time_diff < 8:  # 8 hour effect
                        # Simple trapezoid effect
                        if time_diff < 1:  # 1 hour onset
                            effect = 8.0 * (time_diff / 1.0)
                        elif time_diff < 5:  # 4 hour peak
                            effect = 8.0
                        else:  # 3 hour decline
                            decline_time = time_diff - 5
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
                customdata=[format_time_across_midnight(x) for x in time_points],
                hovertemplate="<b>Pain Relief</b><br>Time: %{customdata}<br>Level: %{y:.1f}/10<extra></extra>"
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
            
            timeline_figure = fig
    except Exception as e:
        print(f"Error updating painkiller timeline: {e}")
        timeline_figure = dash.no_update
    
    # Update relief windows
    relief_windows = ""
    if add_clicks or clear_clicks:
        try:
            sim = get_simulator()
            if not hasattr(sim, 'painkillers') or not sim.painkillers:
                relief_windows = html.P("No pain relief windows found", className="text-muted")
            else:
                # Simple relief window calculation
                relief_windows_list = []
                for dose in sim.painkillers:
                    start_time = dose['time_hours']
                    end_time = start_time + 8  # 8 hour effect
                    relief_windows_list.append({
                        'start': start_time,
                        'end': end_time,
                        'level': 'Strong'  # Placeholder
                    })
                
                if not relief_windows_list:
                    relief_windows = html.P("No significant pain relief windows found", className="text-muted")
                else:
                    # Display relief windows
                    window_cards = []
                    for i, window in enumerate(relief_windows_list):
                        start_str = format_time_across_midnight(window['start'])
                        end_str = format_time_across_midnight(window['end'])
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
                    
                    relief_windows = html.Div([
                        html.H6("😌 Pain Relief Windows", className="mb-3"),
                        html.Div(window_cards)
                    ])
        except Exception as e:
            print(f"Error updating relief windows: {e}")
            relief_windows = html.P("Error calculating relief windows", className="text-danger")
    

    
    # Update dose display
    dose_display = render_painkiller_doses_list()
    
    print(f"DEBUG: Final simulator painkillers before return: {get_simulator().painkillers}")
    print(f"DEBUG: Final app state painkillers: {app_state['painkillers']}")
    print(f"DEBUG: Dose display rendered: {dose_display is not None}")
    
    return dosage_display, info_display, timeline_figure, relief_windows, dose_display



















# Callback for pain relief windows


# Callback for data export
@app.callback(
    Output("download-data", "data"),
    Input("export-data-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_data(n_clicks):
    if n_clicks:
        try:
            # Prepare data for export
            export_data = {
                'medications': simulator.medications,
                'stimulants': simulator.stimulants,
                'painkillers': simulator.painkillers,
                'app_settings': app_state['app_settings'],
                'user_preferences': app_state['user_preferences'],
                'export_date': datetime.now().isoformat(),
                'version': '2.0.0'
            }
            
            # Convert to JSON string
            json_data = json.dumps(export_data, indent=2, default=str)
            
            # Return data for download
            return dict(
                content=json_data,
                filename=f"ritalitime_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                type="application/json"
            )
            
        except Exception as e:
            print(f"Error exporting data: {e}")
            return None
    
    return None

# Callback for data import
@app.callback(
    [Output("current-doses-display", "children", allow_duplicate=True),
     Output("current-pk-doses-display", "children", allow_duplicate=True)],
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def import_data(contents, filename):
    if not contents:
        return dash.no_update, dash.no_update
    
    try:
        # Parse uploaded file
        import base64
        decoded = base64.b64decode(contents.split(',')[1])
        import_data = json.loads(decoded.decode('utf-8'))
        
        # Validate import data
        if not isinstance(import_data, dict):
            raise ValueError("Invalid import file format")
        
        # Import medications
        if 'medications' in import_data and isinstance(import_data['medications'], list):
            simulator.medications = import_data['medications']
            app_state['medications'] = simulator.medications.copy()
        
        # Import stimulants
        if 'stimulants' in import_data and isinstance(import_data['stimulants'], list):
            simulator.stimulants = import_data['stimulants']
            app_state['stimulants'] = simulator.stimulants.copy()
        
        # Import painkillers
        if 'painkillers' in import_data and isinstance(import_data['painkillers'], list):
            simulator.painkillers = import_data['painkillers']
            app_state['painkillers'] = simulator.painkillers.copy()
        
        # Import app settings
        if 'app_settings' in import_data and isinstance(import_data['app_settings'], dict):
            app_state['app_settings'].update(import_data['app_settings'])
        
        # Import user preferences
        if 'user_preferences' in import_data and isinstance(import_data['user_preferences'], dict):
            app_state['user_preferences'].update(import_data['user_preferences'])
        
        print(f"Data imported successfully from {filename}")
        
        # Return updated displays
        return render_doses_list(), render_painkiller_doses_list()
        
    except Exception as e:
        print(f"Error importing data: {e}")
        return dash.no_update, dash.no_update

# Callback for saving user preferences
@app.callback(
    Output("save-prefs-btn", "children"),
    Input("save-prefs-btn", "n_clicks"),
    [State("default-med-time", "value"),
     State("default-stim-time", "value"),
     State("default-pk-time", "value"),
     State("default-pills", "value")]
)
def save_user_preferences(n_clicks, med_time, stim_time, pk_time, pills):
    if n_clicks:
        try:
            # Save preferences to app state
            app_state['user_preferences'] = {
                'default_med_time': med_time,
                'default_stim_time': stim_time,
                'default_pk_time': pk_time,
                'default_pills': pills
            }
            
            print("User preferences saved successfully")
            return "Preferences Saved! ✅"
            
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return "Error Saving ❌"
    
    return "Save Preferences"

# Callback for manual data loading from IndexedDB
@app.callback(
    Output("db-operation-trigger", "data", allow_duplicate=True),
    Input("load-db-btn", "n_clicks"),
    prevent_initial_call=True
)
def manual_load_data(n_clicks):
    """Manually trigger data loading from IndexedDB"""
    if n_clicks:
        return {"operation": "load", "data": "manual-load"}
    return dash.no_update

# Callback for clearing all data from IndexedDB
@app.callback(
    Output("db-operation-trigger", "data", allow_duplicate=True),
    Input("clear-db-btn", "n_clicks"),
    prevent_initial_call=True
)
def manual_clear_data(n_clicks):
    """Manually trigger clearing all data from IndexedDB"""
    if n_clicks:
        return {"operation": "clear", "data": "manual-clear"}
    return dash.no_update

# Callback for removing doses
# TEMPORARILY DISABLED - remove dose callback
# @app.callback(
#     Output("current-doses-display", "children", allow_duplicate=True),
#     [Input({"type": "remove-dose", "index": ALL}, "n_clicks")],
#     prevent_initial_call=True
# )
# def remove_dose_callback(remove_clicks):
#     """Handle dose removal for medications/stimulants"""
#     ctx = callback_context
#     
#     print(f"DEBUG: remove_dose_callback called with remove_clicks: {remove_clicks}")
#     print(f"DEBUG: callback context triggered: {ctx.triggered}")
#     
#     if not ctx.triggered:
#         print("DEBUG: No trigger, returning no_update")
#         return dash.no_update
#     
#     try:
#         # Get the button that was clicked
#         button_id = ctx.triggered[0]['prop_id'].split('.')[0]
#         button_data = json.loads(button_id)
#         print(f"DEBUG: Button data: {button_data}")
#         
#         if button_data['type'] == 'remove-dose':
#             # Remove medication/stimulant dose
#             dose_id = button_data['index']
#             
#             # Check if this is a real button click (n_clicks > 0)
#             if not remove_clicks or all(click is None for click in remove_clicks):
#                 print(f"DEBUG: Ignoring automatic trigger for dose ID: {dose_id}")
#                 return dash.no_update
#             
#             sim = get_simulator()
#             print(f"DEBUG: About to remove dose with ID: {dose_id}")
#             sim.remove_dose(dose_id)
#             print(f"Removed dose with ID: {dose_id}")
#             
#             # Return updated display
#             return render_doses_list()
#         
#     except Exception as e:
#         print(f"Error removing dose: {e}")
#     
#     return dash.no_update

# Callback for removing doses (medications and stimulants)
@app.callback(
    [Output("current-doses-display", "children", allow_duplicate=True),
     Output("timeline-trigger", "children", allow_duplicate=True)],
    [Input({"type": "remove-dose", "index": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def remove_dose_callback(remove_clicks):
    """Handle dose removal for medications/stimulants"""
    ctx = callback_context
    
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    try:
        # Get the button that was clicked
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_data = json.loads(button_id)
        
        if button_data['type'] == 'remove-dose':
            dose_id = button_data['index']
            
            # Check if this is a real button click (n_clicks > 0)
            if not remove_clicks or all(click is None for click in remove_clicks):
                return dash.no_update, dash.no_update
            
            sim = get_simulator()
            sim.remove_dose(dose_id)
            print(f"Removed dose with ID: {dose_id}")
            
            # Update app state
            app_state['medications'] = sim.medications.copy()
            app_state['stimulants'] = sim.stimulants.copy()
            
            # Trigger timeline update
            timeline_trigger = f"dose-removed-{datetime.now().timestamp()}"
            
            # Return updated display
            return render_doses_list(), timeline_trigger
        
    except Exception as e:
        print(f"Error removing dose: {e}")
    
    return dash.no_update, dash.no_update



# JavaScript callbacks for IndexedDB operations
app.clientside_callback(
    """
    function(trigger) {
        if (!trigger) return window.dash_clientside.no_update;
        
        const operation = trigger.operation;
        const data = trigger.data;
        
        // Check if RitaliTimeDB is available
        if (typeof window.ritaliTimeDB === 'undefined' || !window.ritaliTimeDB) {
            console.error('RitaliTimeDB not available');
            return JSON.stringify({ success: false, error: 'Database not available' });
        }
        
        try {
            console.log('Starting IndexedDB operation:', operation);
            
            // Handle async operations properly
            if (operation === 'save') {
                console.log('Executing save operation...');
                if (typeof window.ritaliTimeDB.exportData !== 'function') {
                    console.error('exportData method not found on ritaliTimeDB');
                    return JSON.stringify({ success: false, error: 'exportData method not available' });
                }
                
                // Use a synchronous approach for now - just return success
                // The actual save will happen in the background
                try {
                    window.ritaliTimeDB.exportData().then(exportData => {
                        localStorage.setItem('ritalitime_backup', JSON.stringify(exportData));
                        console.log('Save operation completed in background');
                    }).catch(error => {
                        console.error('Background save error:', error);
                    });
                    
                    return JSON.stringify({ success: true, message: 'Save initiated' });
                } catch (error) {
                    return JSON.stringify({ success: false, error: error.message });
                }
                
            } else if (operation === 'load') {
                console.log('Executing load operation...');
                if (typeof window.ritaliTimeDB.exportData !== 'function') {
                    console.error('exportData method not found on ritaliTimeDB');
                    return JSON.stringify({ success: false, error: 'exportData method not available' });
                }
                
                // Try to load from localStorage backup first (synchronous)
                const backup = localStorage.getItem('ritalitime_backup');
                if (backup) {
                    try {
                        const parsedBackup = JSON.parse(backup);
                        console.log('Load operation successful from backup');
                        return JSON.stringify({ success: true, data: parsedBackup, fromBackup: true });
                    } catch (e) {
                        console.error('Backup data corrupted:', e);
                    }
                }
                
                // Return error if no backup available
                return JSON.stringify({ success: false, error: 'No backup data available' });
                
            } else if (operation === 'clear') {
                console.log('Executing clear operation...');
                if (typeof window.ritaliTimeDB.clearAllData !== 'function') {
                    console.error('clearAllData method not found on ritaliTimeDB');
                    return JSON.stringify({ success: false, error: 'clearAllData method not available' });
                }
                
                // Clear localStorage immediately (synchronous)
                localStorage.removeItem('ritalitime_backup');
                
                // Clear IndexedDB in background
                try {
                    window.ritaliTimeDB.clearAllData().then(() => {
                        console.log('Clear operation completed in background');
                    }).catch(error => {
                        console.error('Background clear error:', error);
                    });
                    
                    return JSON.stringify({ success: true, message: 'Clear initiated' });
                } catch (error) {
                    return JSON.stringify({ success: false, error: error.message });
                }
                
            } else {
                return JSON.stringify({ success: false, error: 'Unknown operation' });
            }
            
        } catch (error) {
            console.error('Operation error:', error);
            return JSON.stringify({ success: false, error: error.message });
        }
    }
    """,
    Output("db-operation-result", "children"),
    Input("db-operation-trigger", "data"),
    prevent_initial_call=True
)

# Callback to save data to IndexedDB
@app.callback(
    Output("db-operation-trigger", "data"),
    [Input("add-med-btn", "n_clicks"),
     Input("add-stim-btn", "n_clicks"),
     Input("add-pk-btn", "n_clicks"),
     Input("clear-all-doses-btn", "n_clicks"),
     Input("clear-all-pk-btn", "n_clicks"),
     Input("sleep-threshold-slider", "value")],
    prevent_initial_call=True
)
def trigger_db_save(med_clicks, stim_clicks, pk_clicks, clear_clicks, clear_pk_clicks, sleep_threshold):
    """Trigger database save when data changes"""
    ctx = callback_context
    
    if not ctx.triggered:
        return dash.no_update
    
    # Save current state
    save_app_state()
    
    # Trigger IndexedDB save
    return {"operation": "save", "data": "auto-save"}

# Callback to load data from IndexedDB on app start
@app.callback(
    Output("timeline-trigger", "children", allow_duplicate=True),
    Input("main-tabs", "active_tab"),
    prevent_initial_call='initial_duplicate'
)
def load_data_on_start(active_tab):
    """Load data from IndexedDB when app starts"""
    if active_tab == "adhd-tab":
        # Load app state
        load_app_state()
        
        # Trigger timeline update
        return f"data-loaded-{datetime.now().timestamp()}"
    
    return dash.no_update

# Callback to handle data loading from IndexedDB
@app.callback(
    [Output("current-doses-display", "children", allow_duplicate=True),
     Output("current-pk-doses-display", "children", allow_duplicate=True),
     Output("sleep-threshold-slider", "value", allow_duplicate=True)],
    Input("db-operation-result", "children"),
    prevent_initial_call=True
)
def handle_db_operation_result(result):
    """Handle results from IndexedDB operations"""
    if not result:
        return dash.no_update, dash.no_update, dash.no_update
    
    try:
        # Parse the result
        if isinstance(result, str):
            result = json.loads(result)
        
        if result.get('success') and result.get('data'):
            data = result['data']
            
            # Update simulator with loaded data
            sim = get_simulator()
            
            if data.get('medications'):
                sim.medications = data['medications']
                app_state['medications'] = data['medications']
            
            if data.get('stimulants'):
                sim.stimulants = data['stimulants']
                app_state['stimulants'] = data['stimulants']
            
            if data.get('painkillers'):
                sim.painkillers = data['painkillers']
                app_state['painkillers'] = data['painkillers']
            
            if data.get('sleep_threshold'):
                sim.sleep_threshold = data['sleep_threshold']
                app_state['sleep_threshold'] = data['sleep_threshold']
            
            if data.get('app_settings'):
                app_state['app_settings'] = data['app_settings']
            
            if data.get('user_preferences'):
                app_state['user_preferences'] = data['user_preferences']
            
            print(f"Data loaded from {'backup' if result.get('fromBackup') else 'IndexedDB'}")
            
            # Return updated displays
            return render_doses_list(), render_painkiller_doses_list(), sim.sleep_threshold
        
    except Exception as e:
        print(f"Error handling DB operation result: {e}")
    
    return dash.no_update, dash.no_update, dash.no_update

# Main application entry point
if __name__ == "__main__":
    print("Starting RitaliTime Dash application...")
    print(f"Medications loaded: {len(medications_data)} categories")
    
    # Run the app
    app.run(
        debug=True,
        host="127.0.0.1",
        port=8080
    )
