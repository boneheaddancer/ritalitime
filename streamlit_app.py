import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from medication_simulator import MedicationSimulator
import json
from datetime import datetime, time, timedelta
import io
import base64

print("Imports completed successfully")

# localStorage functionality for input data persistence
def save_to_local_storage(data, key):
    """Save data to localStorage using base64 encoding"""
    try:
        # Convert data to JSON string and encode to base64
        json_str = json.dumps(data, default=str)
        encoded_data = base64.b64encode(json_str.encode()).decode()
        
        # Store in session state (this will persist across reruns)
        # Only try to access session state if it's available
        try:
            st.session_state[f"localStorage_{key}"] = encoded_data
        except Exception as e:
            print(f"Warning: Could not save to session state: {e}")
            return False
        
        # Note: Browser localStorage not accessible in Streamlit, only session state is used
            
        return True
    except Exception as e:
        print(f"Error saving to localStorage: {e}")
        return False

def load_from_local_storage(key, default=None):
    """Load data from localStorage"""
    try:
        # Only try to get from session state (browser localStorage not accessible in Streamlit)
        try:
            if f"localStorage_{key}" in st.session_state:
                encoded_data = st.session_state[f"localStorage_{key}"]
                json_str = base64.b64decode(encoded_data.encode()).decode()
                return json.loads(json_str)
        except Exception as e:
            print(f"Warning: Could not access session state: {e}")
            return default
            
        return default
    except Exception as e:
        print(f"Error loading from localStorage: {e}")
        return default

def clear_local_storage(key):
    """Clear data from localStorage"""
    try:
        # Remove from session state
        # Only try to access session state if it's available
        try:
            if f"localStorage_{key}" in st.session_state:
                del st.session_state[f"localStorage_{key}"]
        except Exception as e:
            print(f"Warning: Could not access session state: {e}")
            return False
        
        # Note: Browser localStorage not accessible in Streamlit, only session state is used
            
        return True
    except Exception as e:
        print(f"Error clearing localStorage: {e}")
        return False

def save_painkiller_doses(doses):
    """Save painkiller doses to localStorage"""
    return save_to_local_storage(doses, 'painkiller_doses')

def load_painkiller_doses():
    """Load painkiller doses from localStorage"""
    return load_from_local_storage('painkiller_doses', [])

def save_simulator_data(simulator):
    """Save simulator data (medications + stimulants) to localStorage"""
    simulator_data = {
        'medications': simulator.medications,
        'stimulants': simulator.stimulants,
        'sleep_threshold': simulator.sleep_threshold
    }
    return save_to_local_storage(simulator_data, 'simulator_data')

def load_simulator_data():
    """Load simulator data from localStorage"""
    return load_from_local_storage('simulator_data', {
        'medications': [],
        'stimulants': [],
        'sleep_threshold': 0.3
    })

# Initialize localStorage keys
LOCAL_STORAGE_KEYS = {
    'medication_inputs': 'medication_inputs',
    'stimulant_inputs': 'stimulant_inputs', 
    'painkiller_inputs': 'painkiller_inputs',
    'painkiller_doses': 'painkiller_doses',  # Add persistence for actual doses
    'simulator_data': 'simulator_data',  # Add persistence for simulator data
    'sleep_settings': 'sleep_settings',
    'app_settings': 'app_settings'
}

# Load saved input data on app startup
def initialize_local_storage():
    """Initialize localStorage with saved data"""
    try:
        if 'localStorage_initialized' not in st.session_state:
            st.session_state.localStorage_initialized = True
            
            # Load saved medication inputs
            saved_med_inputs = load_from_local_storage(LOCAL_STORAGE_KEYS['medication_inputs'], {})
            if saved_med_inputs:
                st.session_state.saved_medication_inputs = saved_med_inputs
            
            # Load saved stimulant inputs  
            saved_stim_inputs = load_from_local_storage(LOCAL_STORAGE_KEYS['stimulant_inputs'], {})
            if saved_stim_inputs:
                st.session_state.saved_stimulant_inputs = saved_stim_inputs
            
            # Load saved painkiller inputs
            saved_pk_inputs = load_from_local_storage(LOCAL_STORAGE_KEYS['painkiller_inputs'], {})
            if saved_pk_inputs:
                st.session_state.saved_painkiller_inputs = saved_pk_inputs
            
            # Load saved sleep settings
            saved_sleep = load_from_local_storage(LOCAL_STORAGE_KEYS['sleep_settings'], {})
            if saved_sleep:
                st.session_state.saved_sleep_settings = saved_sleep
            
            # Load saved app settings
            saved_app = load_from_local_storage(LOCAL_STORAGE_KEYS['app_settings'], {})
            if saved_app:
                st.session_state.saved_app_settings = saved_app
    except Exception as e:
        print(f"Error initializing localStorage: {e}")
        # Don't fail the app if localStorage fails
        pass

# Auto-save function for input changes
def auto_save_inputs(input_type, data):
    """Automatically save input data when it changes"""
    key = LOCAL_STORAGE_KEYS.get(f'{input_type}_inputs')
    if key:
        save_to_local_storage(data, key)

# Load unified medications file with error handling
print("Attempting to load medications.json...")
medications_data = {}  # Initialize as empty dict
try:
    # Load the raw JSON data directly since it has a nested structure
    with open('medications.json', 'r') as f:
        medications_data = json.load(f)
    st.session_state.medications_loaded = True
    print(f"Medications loaded successfully: {len(medications_data)} categories")
except ValueError as e:
    st.warning(f"⚠️ Warning: Could not load medications.json - {e}")
    st.session_state.medications_loaded = False
    print(f"ValueError loading medications: {e}")
except FileNotFoundError:
    st.warning("⚠️ Warning: medications.json file not found")
    st.session_state.medications_loaded = False
    print("medications.json file not found")
except Exception as e:
    st.warning(f"⚠️ Warning: Unexpected error loading medications.json - {e}")
    st.session_state.medications_loaded = False
    print(f"Unexpected error loading medications: {e}")

# Load profiles with validation
def load_profiles_with_validation():
    """Load profiles and validate medication references"""
    try:
        with open('profiles.json', 'r') as f:
            data = json.load(f)
        
        # Extract preset_profiles from the data structure
        profiles = data.get('preset_profiles', {})
        
        # Convert to list format for easier handling
        profile_list = []
        for profile_key, profile_data in profiles.items():
            profile_data['key'] = profile_key  # Add the key for reference
            profile_list.append(profile_data)
        
        # Validate each profile
        validated_profiles = []
        warnings = []
        
        for profile in profile_list:
            profile_warnings = []
            valid_entries = []
            
            # Check each medication entry
            for entry in profile.get('medications', []):
                med_name = entry.get('medication_name')
                if med_name:
                    # Check if medication exists in unified database
                    if not is_medication_known(med_name):
                        profile_warnings.append(f"Unknown medication: {med_name}")
                        continue
                valid_entries.append(entry)
            
            # Check each stimulant entry
            for entry in profile.get('stimulants', []):
                stim_name = entry.get('stimulant_name')
                if stim_name:
                    # Check if stimulant exists in unified database
                    if not is_stimulant_known(stim_name):
                        profile_warnings.append(f"Unknown stimulant: {stim_name}")
                        continue
                valid_entries.append(entry)
            
            # Create validated profile
            validated_profile = profile.copy()
            # Filter entries based on their content, not type field
            validated_profile['medications'] = [e for e in valid_entries if 'medication_name' in e]
            validated_profile['stimulants'] = [e for e in valid_entries if 'stimulant_name' in e]
            
            validated_profiles.append(validated_profile)
            
            if profile_warnings:
                warnings.append(f"Profile '{profile.get('name', 'Unknown')}': {', '.join(profile_warnings)}")
        
        return validated_profiles, warnings
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.warning(f"⚠️ Warning: Could not load profiles.json - {e}")
        return [], []
    except Exception as e:
        st.warning(f"⚠️ Warning: Unexpected error loading profiles.json - {e}")
        return [], []

def is_medication_known(med_name):
    """Check if medication exists in unified database"""
    try:
        if st.session_state.medications_loaded:
            return med_name in medications_data.get('stimulants', {}).get('prescription_stimulants', {})
        return False
    except:
        return False

def is_stimulant_known(stim_name):
    """Check if stimulant exists in unified database"""
    try:
        if st.session_state.medications_loaded:
            return stim_name in medications_data.get('stimulants', {}).get('common_stimulants', {})
        return False
    except:
        return False

# Load profiles
print("Loading profiles...")
profiles, profile_warnings = load_profiles_with_validation()
print(f"Profiles loaded: {len(profiles)} profiles, {len(profile_warnings)} warnings")

# Show profile warnings
if profile_warnings:
    for warning in profile_warnings:
        st.warning(f"⚠️ {warning}")

# Helper function to convert decimal hours to HH:MM format
def format_time_hours_minutes(decimal_hours):
    """Convert decimal hours to HH:MM format"""
    hours = int(decimal_hours)
    minutes = int((decimal_hours % 1) * 60)
    return f"{hours:02d}:{minutes:02d}"

def format_time_across_midnight(decimal_hours):
    """Convert decimal hours to HH:MM format, handling times across midnight"""
    if decimal_hours < 24:
        # Same day: use standard HH:MM format
        hours = int(decimal_hours)
        minutes = int((decimal_hours % 1) * 60)
        return f"{hours:02d}:{minutes:02d}"
    else:
        # Next day: convert back to 0-23 format (e.g., 25:00 becomes 01:00)
        hours = int(decimal_hours) % 24
        minutes = int((decimal_hours % 1) * 60)
        return f"{hours:02d}:{minutes:02d}"

def format_duration_hours_minutes(decimal_hours):
    """Convert decimal hours to duration format (e.g., 2h 30m)"""
    try:
        # Ensure input is a valid number
        decimal_hours = float(decimal_hours)
        
        # Handle negative values
        if decimal_hours < 0:
            return f"{decimal_hours:.2f}h"
        
        hours = int(decimal_hours)
        minutes = round((decimal_hours % 1) * 60)  # Round instead of truncate
        
        # Handle edge case where rounding gives 60 minutes
        if minutes == 60:
            hours += 1
            minutes = 0
        
        # Format output
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return "0m"  # Handle exactly 0 hours
            
    except (TypeError, ValueError, AttributeError):
        # Fallback for invalid input
        return f"{decimal_hours:.2f}h"

def format_duration_minutes(total_minutes):
    """Convert total minutes to duration format (e.g., 2h 30m)"""
    try:
        # Ensure input is a valid number
        total_minutes = int(total_minutes)
        
        # Handle negative values
        if total_minutes < 0:
            return f"{total_minutes}m"
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        # Format output
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return "0m"  # Handle exactly 0 minutes
            
    except (TypeError, ValueError, AttributeError):
        # Fallback for invalid input
        return f"{total_minutes}m"

# Page configuration
st.set_page_config(
    page_title="ADHD Medication & Stimulant Timeline Simulator",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'simulator' not in st.session_state:
    try:
        # Try to load simulator data from localStorage first
        saved_simulator_data = load_simulator_data()
        st.session_state.simulator = MedicationSimulator()
        
        # Restore saved data if available
        if saved_simulator_data and isinstance(saved_simulator_data, dict):
            if saved_simulator_data.get('medications') or saved_simulator_data.get('stimulants'):
                st.session_state.simulator.medications = saved_simulator_data.get('medications', [])
                st.session_state.simulator.stimulants = saved_simulator_data.get('stimulants', [])
                st.session_state.simulator.sleep_threshold = saved_simulator_data.get('sleep_threshold', 0.3)
                print("MedicationSimulator initialized with saved data")
            else:
                print("MedicationSimulator initialized with default data")
        else:
            print("MedicationSimulator initialized with default data")
    except Exception as e:
        print(f"Error initializing simulator: {e}")
        st.session_state.simulator = MedicationSimulator()
        print("MedicationSimulator initialized with fallback defaults")

print("Streamlit app loaded successfully")

def main():
    print("Main function called")
    
    # Initialize localStorage after Streamlit is ready
    if 'localStorage_initialized' not in st.session_state:
        initialize_local_storage()
    
    # Navigation
    st.sidebar.title("📱 App Navigation")
    
    # Load saved app settings
    saved_app_settings = st.session_state.get('saved_app_settings', {})
    default_app_mode = saved_app_settings.get('app_mode', "ADHD Medications")
    
    app_mode = st.sidebar.selectbox(
        "Choose Application",
        ["ADHD Medications", "Painkillers"],
        index=0 if default_app_mode == "ADHD Medications" else 1,
        key="app_navigation"
    )
    
    # Auto-save app navigation selection
    current_app_settings = {
        'app_mode': app_mode
    }
    save_to_local_storage(current_app_settings, LOCAL_STORAGE_KEYS['app_settings'])
    

    
    if app_mode == "ADHD Medications":
        print("Calling ADHD medications app")
        adhd_medications_app()
    else:
        print("Calling painkillers app")
        painkillers_app()

def adhd_medications_app():
    st.title("💊 ADHD Medication & Stimulant Timeline Simulator")
    st.markdown("Simulate and visualize medication and stimulant effects throughout the day")
    
    # Show localStorage status
    if any(key in st.session_state for key in ['saved_medication_inputs', 'saved_stimulant_inputs', 'saved_painkiller_inputs', 'saved_sleep_settings', 'saved_app_settings']):
        st.success("💾 **Input Data Saved**: Your preferences are automatically saved and will be restored when you return.")
    
    # Sidebar for dose management
    with st.sidebar:
        st.header("📋 Dose Management")
        
        # Tab for different types of doses
        tab1, tab2 = st.tabs(["💊 Medications", "☕ Stimulants"])
        
        with tab1:
            st.subheader("Add New Medication")
            
            # Load available prescription medications from unified database
            available_medications = []
            if st.session_state.medications_loaded and medications_data.get('stimulants', {}).get('prescription_stimulants'):
                available_medications = list(medications_data['stimulants']['prescription_stimulants'].keys())
            
            if not available_medications:
                st.error("No medications available. Please check that medications.json is properly loaded.")
            else:
                # Load saved medication inputs
                saved_med_inputs = st.session_state.get('saved_medication_inputs', {})
                default_time = time(8, 0)
                default_med = available_medications[0] if available_medications else None
                default_dosage = 20.0
                
                if saved_med_inputs:
                    try:
                        if 'dose_time' in saved_med_inputs:
                            time_str = saved_med_inputs['dose_time']
                            hour, minute = map(int, time_str.split(':'))
                            default_time = time(hour, minute)
                        if 'medication_name' in saved_med_inputs and saved_med_inputs['medication_name'] in available_medications:
                            default_med = saved_med_inputs['medication_name']
                        if 'dosage' in saved_med_inputs:
                            default_dosage = float(saved_med_inputs['dosage'])
                    except:
                        pass
                
                col1, col2 = st.columns(2)
                with col1:
                    dose_time = st.time_input("Dose Time", value=default_time, key="med_time")
                    medication_name = st.selectbox("Medication Type", available_medications, index=available_medications.index(default_med) if default_med else 0, key="med_name")
                with col2:
                    dosage = st.number_input("Dosage (mg)", min_value=1.0, max_value=100.0, value=default_dosage, step=1.0, key="med_dosage")
                
                # Auto-save medication inputs
                current_med_inputs = {
                    'dose_time': dose_time.strftime("%H:%M"),
                    'medication_name': medication_name,
                    'dosage': dosage
                }
                auto_save_inputs('medication', current_med_inputs)
            
            # Show medication info if prescription medication is selected
            if medication_name and medication_name != 'Custom':
                try:
                    if st.session_state.medications_loaded and medications_data.get('stimulants', {}).get('prescription_stimulants', {}).get(medication_name):
                        med_info = medications_data['stimulants']['prescription_stimulants'][medication_name]
                        
                        # Convert minutes to hours for display
                        onset_hours = med_info['onset_min'] / 60.0
                        peak_time_hours = med_info['t_peak_min'] / 60.0
                        peak_duration_hours = med_info['peak_duration_min'] / 60.0
                        duration_hours = med_info['duration_min'] / 60.0
                        wear_off_hours = med_info['wear_off_min'] / 60.0
                        
                        st.info(f"**{medication_name}**: Onset {format_time_hours_minutes(onset_hours)}, Peak at {format_time_hours_minutes(peak_time_hours)}, Peak duration {format_duration_hours_minutes(peak_duration_hours)}, Total {format_duration_hours_minutes(duration_hours)}")
                    else:
                        st.warning("Medications data not loaded")
                except Exception as e:
                    st.warning(f"Could not load medication information: {str(e)}")
            
            # Advanced parameters (to override prescription defaults)
            if medication_name:
                with st.expander("Advanced Parameters (Override Defaults)"):
                    # Get current values from JSON for prescription medication
                    default_onset, default_peak, default_duration, default_effect = 1.0, 2.0, 8.0, 1.0
                    if st.session_state.medications_loaded and medications_data.get('stimulants', {}).get('prescription_stimulants', {}).get(medication_name):
                        med_info = medications_data['stimulants']['prescription_stimulants'][medication_name]
                        
                        # Convert minutes to hours for default values
                        default_onset = float(med_info['onset_min']) / 60.0
                        default_peak = float(med_info['t_peak_min']) / 60.0
                        default_duration = float(med_info['duration_min']) / 60.0
                        # Use peak_effect from medication data instead of peak_duration
                        default_effect = float(med_info.get('peak_effect', 1.0))
                    
                    # Load saved advanced parameters
                    saved_adv_params = saved_med_inputs.get('advanced_params', {})
                    default_onset_saved = saved_adv_params.get('onset_time', round(default_onset, 1))
                    default_peak_saved = saved_adv_params.get('peak_time', round(default_peak, 1))
                    default_duration_saved = saved_adv_params.get('duration', round(default_duration, 1))
                    default_effect_saved = saved_adv_params.get('peak_effect', round(default_effect, 1))
                    
                    onset_time = st.slider("Onset Time (hours)", 0.5, 3.0, value=default_onset_saved, step=0.1, key="med_onset")
                    peak_time = st.slider("Peak Time (hours)", 1.0, 6.0, value=default_peak_saved, step=0.1, key="med_peak")
                    duration = st.slider("Duration (hours)", 4.0, 16.0, value=default_duration_saved, step=0.5, key="med_duration")
                    peak_effect = st.slider("Peak Effect", 0.1, 2.0, value=default_effect_saved, step=0.1, key="med_effect")
                    
                    # Show what values are being overridden
                    st.info(f"**Current JSON values**: Onset {format_duration_hours_minutes(default_onset)}, Peak {format_duration_hours_minutes(default_peak)}, Duration {format_duration_hours_minutes(default_duration)}, Effect {default_effect:.2f}")
                    st.info(f"**Override values**: Onset {format_duration_hours_minutes(onset_time)}, Peak {format_duration_hours_minutes(peak_time)}, Duration {format_duration_hours_minutes(duration)}, Effect {peak_effect:.2f}")
                    
                    # Auto-save advanced parameters
                    current_med_inputs['advanced_params'] = {
                        'onset_time': onset_time,
                        'peak_time': peak_time,
                        'duration': duration,
                        'peak_effect': peak_effect
                    }
                    auto_save_inputs('medication', current_med_inputs)
            
            if medication_name and st.button("➕ Add Medication", type="primary", key="add_med"):
                time_str = dose_time.strftime("%H:%M")
                
                # Use prescription medication with custom parameters as override
                custom_params = {
                    'onset_time_min': int(onset_time * 60),
                    'peak_time_min': int(peak_time * 60),
                    'duration_min': int(duration * 60),
                    'peak_effect': peak_effect
                }
                st.session_state.simulator.add_medication(
                    time_str, dosage, medication_name=medication_name, custom_params=custom_params
                )
                # Save simulator data to localStorage for persistence
                save_simulator_data(st.session_state.simulator)
                st.success(f"Added {dosage}mg {medication_name} at {time_str}")
                
                st.rerun()
        
        with tab2:
            st.subheader("Add New Stimulant")
            
            # Load available stimulants from unified database
            available_stimulants = []
            if st.session_state.medications_loaded and medications_data.get('stimulants', {}).get('common_stimulants'):
                available_stimulants = list(medications_data['stimulants']['common_stimulants'].keys())
            
            if not available_stimulants:
                st.error("No stimulants available. Please check that medications.json is properly loaded.")
            else:
                # Load saved stimulant inputs
                saved_stim_inputs = st.session_state.get('saved_stimulant_inputs', {})
                default_stim_time = time(9, 0)
                default_stim = available_stimulants[0] if available_stimulants else None
                default_quantity = 1.0
                
                if saved_stim_inputs:
                    try:
                        if 'stim_time' in saved_stim_inputs:
                            time_str = saved_stim_inputs['stim_time']
                            hour, minute = map(int, time_str.split(':'))
                            default_stim_time = time(hour, minute)
                        if 'stimulant_name' in saved_stim_inputs and saved_stim_inputs['stimulant_name'] in available_stimulants:
                            default_stim = saved_stim_inputs['stimulant_name']
                        if 'quantity' in saved_stim_inputs:
                            default_quantity = float(saved_stim_inputs['quantity'])
                    except:
                        pass
                
                col1, col2 = st.columns(2)
                with col1:
                    stim_time = st.time_input("Consumption Time", value=default_stim_time, key="stim_time")
                    stimulant_name = st.selectbox("Stimulant", available_stimulants, index=available_stimulants.index(default_stim) if default_stim else 0, key="stim_name")
                with col2:
                    quantity = st.number_input("Quantity", min_value=0.5, max_value=5.0, value=default_quantity, step=0.5, key="stim_quantity")
                
                # Auto-save stimulant inputs
                current_stim_inputs = {
                    'stim_time': stim_time.strftime("%H:%M"),
                    'stimulant_name': stimulant_name,
                    'quantity': quantity
                }
                auto_save_inputs('stimulant', current_stim_inputs)
            
            # Show component selection for complex stimulants
            component_name = None
            if stimulant_name and stimulant_name in ['redbull', 'monster']:
                component_name = st.selectbox("Component", ['caffeine', 'taurine'], key="stim_component")
            
            # Advanced parameters for stimulants (override defaults)
            if stimulant_name:
                with st.expander("Advanced Parameters (Override Defaults)"):
                    # Get current values from JSON
                    default_onset, default_peak, default_duration, default_effect = 0.17, 1.0, 6.0, 0.75
                    if st.session_state.medications_loaded and medications_data.get('stimulants', {}).get('common_stimulants', {}).get(stimulant_name):
                        stim_data = medications_data['stimulants']['common_stimulants'][stimulant_name]
                        
                        if component_name and component_name in stim_data:
                            stim_info = stim_data[component_name]
                        elif 'onset_min' in stim_data:
                            stim_info = stim_data
                        else:
                            stim_info = list(stim_data.values())[0] if stim_data else {}
                        
                        # Convert minutes to hours for default values
                        default_onset = float(stim_info.get('onset_min', 10)) / 60.0
                        default_peak = float(stim_info.get('t_peak_min', 60)) / 60.0
                        default_duration = float(stim_info.get('duration_min', 360)) / 60.0
                        default_effect = float(stim_info.get('peak_duration_min', 45)) / 60.0
                    
                    # Load saved advanced parameters
                    saved_adv_params = saved_stim_inputs.get('advanced_params', {})
                    default_onset_saved = saved_adv_params.get('onset_time', round(default_onset, 1))
                    default_peak_saved = saved_adv_params.get('peak_time', round(default_peak, 1))
                    default_duration_saved = saved_adv_params.get('duration', round(default_duration, 1))
                    default_effect_saved = saved_adv_params.get('peak_effect', round(default_effect, 1))
                    
                    onset_time = st.slider("Onset Time (hours)", 0.1, 2.0, value=default_onset_saved, step=0.1, key="stim_onset")
                    peak_time = st.slider("Peak Time (hours)", 0.5, 3.0, value=default_peak_saved, step=0.1, key="stim_peak")
                    duration = st.slider("Duration (hours)", 2.0, 12.0, value=default_duration_saved, step=0.5, key="stim_duration")
                    peak_effect = st.slider("Peak Effect", 0.1, 2.0, value=default_effect_saved, step=0.1, key="stim_effect")
                    
                    # Show what values are being overridden
                    st.info(f"**Current JSON values**: Onset {format_duration_hours_minutes(default_onset)}, Peak {format_duration_hours_minutes(default_peak)}, Duration {format_duration_hours_minutes(default_duration)}, Effect {default_effect:.2f}")
                    st.info(f"**Override values**: Onset {format_duration_hours_minutes(onset_time)}, Peak {format_duration_hours_minutes(peak_time)}, Duration {format_duration_hours_minutes(duration)}, Effect {peak_effect:.2f}")
                    
                    # Auto-save advanced parameters
                    current_stim_inputs['advanced_params'] = {
                        'onset_time': onset_time,
                        'peak_time': peak_time,
                        'duration': duration,
                        'peak_effect': peak_effect
                    }
                    auto_save_inputs('stimulant', current_stim_inputs)
            
            if stimulant_name and st.button("➕ Add Stimulant", type="primary", key="add_stim"):
                time_str = stim_time.strftime("%H:%M")
                
                # Use stimulant with custom parameters as override
                custom_params = {
                    'onset_time_min': int(onset_time * 60),
                    'peak_time_min': int(peak_time * 60),
                    'duration_min': int(duration * 60),
                    'peak_effect': peak_effect
                }
                st.session_state.simulator.add_stimulant(
                    time_str, stimulant_name, component_name, quantity, custom_params
                )
                # Save simulator data to localStorage for persistence
                save_simulator_data(st.session_state.simulator)
                st.success(f"Added {quantity}x {stimulant_name} at {time_str}")
                
                st.rerun()
        
        # Profile management
        st.header("👤 Profile Management")
        
        if profiles:
            profile_names = [p.get('name', 'Unnamed Profile') for p in profiles]
            selected_profile = st.selectbox("Load Profile", profile_names, key="profile_select")
            
            if st.button("📥 Load Profile", key="load_profile"):
                selected_profile_data = next(p for p in profiles if p.get('name') == selected_profile)
                
                # Convert profile data to simulator format and handle old field names
                medications = []
                for med in selected_profile_data.get('medications', []):
                    converted_med = med.copy()
                    # Convert old field names to new ones if they exist
                    if 'onset_time' in med:
                        converted_med['onset_time_min'] = int(med['onset_time'] * 60)
                        converted_med['peak_time_min'] = int(med['peak_time'] * 60)
                        converted_med['duration_min'] = int(med['duration'] * 60)
                    medications.append(converted_med)
                
                stimulants = []
                for stim in selected_profile_data.get('stimulants', []):
                    converted_stim = stim.copy()
                    # Convert old field names to new ones if they exist
                    if 'onset_time' in stim:
                        converted_stim['onset_time_min'] = int(stim['onset_time'] * 60)
                        converted_stim['peak_time_min'] = int(stim['peak_time'] * 60)
                        converted_stim['duration_min'] = int(stim['duration'] * 60)
                    stimulants.append(converted_stim)
                
                simulator_data = {
                    'medications': medications,
                    'stimulants': stimulants,
                    'sleep_threshold': selected_profile_data.get('sleep_threshold', 0.3)
                }
                
                st.session_state.simulator.import_schedule(simulator_data)
                # Save simulator data to localStorage for persistence
                save_simulator_data(st.session_state.simulator)
                st.success(f"Loaded profile: {selected_profile}")
                st.rerun()
        
        # Dose management
        st.header("🗑️ Dose Management")
        
        # Show current doses
        all_doses = st.session_state.simulator.get_all_doses()
        if all_doses:
            st.subheader("Current Doses")
            for dose in all_doses:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    if dose['type'] == 'medication':
                        st.write(f"💊 {dose['dosage']}mg {dose.get('medication_name', 'medication')}")
                    else:
                        st.write(f"☕ {dose['quantity']}x {dose['stimulant_name']}")
                        if dose.get('component_name'):
                            st.write(f"   ({dose['component_name']})")
                
                with col2:
                    # Convert minutes back to time string for display
                    dose_time_str = st.session_state.simulator._minutes_to_time(dose['time'])
                    st.write(f"⏰ {dose_time_str}")
                
                with col3:
                    if st.button("❌", key=f"remove_{dose['id']}"):
                        st.session_state.simulator.remove_dose(dose['id'])
                        # Save simulator data to localStorage for persistence
                        save_simulator_data(st.session_state.simulator)
                        st.rerun()
        else:
            st.info("No doses added yet. Add some medications or stimulants above!")
        
        # Clear all button
        if all_doses:
            if st.button("🗑️ Clear All Doses", type="secondary"):
                st.session_state.simulator.clear_all_doses()
                # Save simulator data to localStorage for persistence
                save_simulator_data(st.session_state.simulator)
                st.rerun()
        
        # Sleep threshold adjustment
        st.header("😴 Sleep Settings")
        
        # Show current sleep threshold impact
        current_threshold = st.session_state.simulator.sleep_threshold
        temp_simulator = MedicationSimulator()
        temp_simulator.medications = st.session_state.simulator.medications.copy()
        temp_simulator.stimulants = st.session_state.simulator.stimulants.copy()
        
        # Test different thresholds
        threshold_impact = []
        for test_threshold in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            temp_simulator.sleep_threshold = test_threshold
            time_points, combined_effect = temp_simulator.generate_daily_timeline()
            if len(combined_effect) > 0:
                sleep_windows = temp_simulator.find_sleep_windows(combined_effect)
                total_sleep_time = sum(end - start for start, end in sleep_windows)
                threshold_impact.append({
                    "Threshold": f"{test_threshold:.1f}",
                    "Sleep Windows": len(sleep_windows),
                    "Total Sleep Time": f"{total_sleep_time:.1f}h",
                    "Current": "✅" if test_threshold == current_threshold else ""
                })
        
        if threshold_impact:
            st.write("**Threshold Impact Preview:**")
            impact_df = pd.DataFrame(threshold_impact)
            st.dataframe(impact_df, use_container_width=True, hide_index=True)
        
        # Load saved sleep settings
        saved_sleep_settings = st.session_state.get('saved_sleep_settings', {})
        default_sleep_threshold = saved_sleep_settings.get('sleep_threshold', st.session_state.simulator.sleep_threshold)
        
        sleep_threshold = st.slider(
            "Sleep Threshold (effect level below which sleep is suitable)",
            0.1, 1.0, default_sleep_threshold, 0.05
        )
        
        # Auto-save sleep settings
        current_sleep_settings = {
            'sleep_threshold': sleep_threshold
        }
        save_to_local_storage(current_sleep_settings, LOCAL_STORAGE_KEYS['sleep_settings'])
        
        if sleep_threshold != st.session_state.simulator.sleep_threshold:
            st.session_state.simulator.sleep_threshold = sleep_threshold
            # Save simulator data to localStorage for persistence
            save_simulator_data(st.session_state.simulator)
            st.rerun()
    
    # Main content area - Make graph wider
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Generate timeline (no caching to ensure real-time updates)
        time_points, combined_effect = st.session_state.simulator.generate_daily_timeline()
        
        if len(time_points) > 0 and len(combined_effect) > 0:
            # Check for failed doses and show warnings
            failed_doses = st.session_state.simulator.get_failed_doses()
            if failed_doses:
                st.warning(f"⚠️ **Warning**: {len(failed_doses)} dose(s) failed to generate curves:")
                for dose in failed_doses:
                    if dose['type'] == 'medication':
                        st.write(f"  • {dose['dosage']}mg {dose.get('medication_name', 'medication')} at {st.session_state.simulator._minutes_to_time(dose['time'])}")
                    else:
                        st.write(f"  • {dose['quantity']}x {dose['stimulant_name']} at {st.session_state.simulator._minutes_to_time(dose['time'])}")
                st.write("Check the console for detailed error information.")
            
            # Create enhanced plot with individual curves toggle
            st.subheader("📊 Daily Effect Timeline")
            
            # Toggle for showing individual curves
            show_individual_curves = st.checkbox("Show Individual Component Curves", value=False, key="show_curves")
            
            # Create figure
            fig = go.Figure()
            
            # Add individual curves if requested
            if show_individual_curves:
                individual_curves = st.session_state.simulator.get_individual_curves()
                
                # Color palette for different doses
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
                
                for i, (label, curve) in enumerate(individual_curves):
                    color = colors[i % len(colors)]  # Cycle through colors
                    
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
                fillcolor='rgba(30, 144, 255, 0.1)',  # Light blue fill
                hovertemplate="<b>Combined Effect</b><br>Time: %{x:.1f}h<br>Effect: %{y:.3f}<extra></extra>"
            ))
            
            # Add sleep threshold line
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
                line=dict(color='purple', width=2, dash='dot'),
                yaxis='y2',
                hovertemplate="<b>Sleep Quality</b><br>Time: %{x:.1f}h<br>Quality: %{y:.3f}<extra></extra>"
            ))
            
            # Add vertical rules for key time points
            all_doses = st.session_state.simulator.get_all_doses()
            for dose in all_doses:
                dose_time_hours = st.session_state.simulator._minutes_to_decimal_hours(dose['time'])
                
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
                    annotation_text=f"Tmax: {format_time_hours_minutes(tmax)}",
                    annotation_position="top"
                )
                
                # Add dose time vertical line
                fig.add_vline(
                    x=dose_time_hours,
                    line_dash="solid",
                    line_color="green",
                    annotation_text=f"Dose: {format_time_hours_minutes(dose_time_hours)}",
                    annotation_position="bottom"
                )
            
            # Update layout
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
                )
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
                    ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)]
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Sleep window analysis
            sleep_windows = st.session_state.simulator.find_sleep_windows(combined_effect)
            if sleep_windows:
                st.subheader("😴 Sleep Windows Analysis")
                
                # Add sleep windows to the chart as shaded areas
                for i, (start, end) in enumerate(sleep_windows):
                    # Calculate sleep quality based on effect level during the window
                    start_idx = np.argmin(np.abs(np.array(time_points) - start))
                    end_idx = np.argmin(np.abs(np.array(time_points) - end))
                    window_effects = combined_effect[start_idx:end_idx+1]
                    avg_effect = np.mean(window_effects) if len(window_effects) > 0 else 0
                    max_effect = np.max(window_effects) if len(window_effects) > 0 else 0
                    
                    # Determine sleep quality
                    if max_effect <= sleep_threshold * 0.5:
                        quality = "Excellent"
                        quality_color = "green"
                        quality_emoji = "🟢"
                    elif max_effect <= sleep_threshold * 0.8:
                        quality = "Good"
                        quality_color = "lightgreen"
                        quality_emoji = "🟡"
                    else:
                        quality = "Fair"
                        quality_color = "orange"
                        quality_emoji = "🟠"
                    
                    # Add shaded area to chart
                    fig.add_vrect(
                        x0=start, x1=end,
                        fillcolor=quality_color,
                        opacity=0.2,
                        layer="below",
                        line_width=0,
                        annotation_text=f"Sleep Window {i+1}<br>{quality_emoji} {quality}",
                        annotation_position="top left"
                    )
                
                # Enhanced sleep windows display - Make table wider
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Sleep windows table with quality assessment
                    sleep_info = []
                    for i, (start, end) in enumerate(sleep_windows):
                        duration = end - start
                        
                        # Check medication timing relative to sleep window
                        nearby_meds = []
                        for dose in all_doses:
                            dose_time_hours = st.session_state.simulator._minutes_to_decimal_hours(dose['time'])
                            # Check if dose is within 4 hours before sleep window
                            if start - 4 <= dose_time_hours <= start:
                                if dose['type'] == 'medication':
                                    nearby_meds.append(f"{dose['dosage']}mg {dose.get('medication_name', 'medication')}")
                                else:
                                    nearby_meds.append(f"{dose['quantity']}x {dose['stimulant_name']}")
                        
                        # Calculate sleep quality
                        start_idx = np.argmin(np.abs(np.array(time_points) - start))
                        end_idx = np.argmin(np.abs(np.array(time_points) - end))
                        window_effects = combined_effect[start_idx:end_idx+1]
                        max_effect = np.max(window_effects) if len(window_effects) > 0 else 0
                        
                        if max_effect <= sleep_threshold * 0.5:
                            quality = "Excellent"
                            quality_emoji = "🟢"
                        elif max_effect <= sleep_threshold * 0.8:
                            quality = "Good"
                            quality_emoji = "🟡"
                        else:
                            quality = "Fair"
                            quality_emoji = "🟠"
                        
                        sleep_info.append({
                            "Window": f"#{i+1}",
                            "Start": format_time_hours_minutes(start),
                            "End": format_time_hours_minutes(end),
                            "Duration": format_duration_hours_minutes(duration),
                            "Quality": f"{quality_emoji} {quality}",
                            "Nearby Doses": ", ".join(nearby_meds) if nearby_meds else "None"
                        })
                    
                    sleep_df = pd.DataFrame(sleep_info)
                    st.dataframe(sleep_df, use_container_width=True, hide_index=True)
                
                with col2:
                    # Sleep insights and recommendations
                    st.subheader("💡 Sleep Insights")
                    
                    # Find best sleep window
                    best_window = None
                    best_quality = 0
                    for i, (start, end) in enumerate(sleep_windows):
                        start_idx = np.argmin(np.abs(np.array(time_points) - start))
                        end_idx = np.argmin(np.abs(np.array(time_points) - end))
                        window_effects = combined_effect[start_idx:end_idx+1]
                        max_effect = np.max(window_effects) if len(window_effects) > 0 else 0
                        quality_score = sleep_threshold - max_effect
                        if quality_score > best_quality:
                            best_quality = quality_score
                            best_window = i
                    
                    if best_window is not None:
                        start, end = sleep_windows[best_window]
                        st.success(f"**Best Sleep Window**: {format_time_hours_minutes(start)} - {format_time_hours_minutes(end)}")
                        
                        # Check for potential issues
                        start_idx = np.argmin(np.abs(np.array(time_points) - start))
                        end_idx = np.argmin(np.abs(np.array(time_points) - end))
                        window_effects = combined_effect[start_idx:end_idx+1]
                        max_effect = np.max(window_effects) if len(window_effects) > 0 else 0
                        
                        if max_effect > sleep_threshold * 0.8:
                            st.warning("⚠️ **Note**: This window has moderate effect levels. Consider adjusting medication timing.")
                        
                        # Check for nearby stimulants
                        nearby_stims = []
                        for dose in all_doses:
                            if dose['type'] == 'stimulant':
                                dose_time_hours = st.session_state.simulator._minutes_to_decimal_hours(dose['time'])
                                if start - 6 <= dose_time_hours <= start:
                                    nearby_stims.append(f"{dose['stimulant_name']} at {format_time_hours_minutes(dose_time_hours)}")
                        
                        if nearby_stims:
                            st.info(f"**Nearby Stimulants**: {', '.join(nearby_stims)}")
                            st.write("Consider avoiding stimulants 6+ hours before sleep.")
                    
                    # Overall sleep quality assessment
                    total_sleep_time = sum(end - start for start, end in sleep_windows)
                    if total_sleep_time >= 7:
                        st.success("✅ **Total Sleep Time**: {:.1f} hours (adequate)")
                    elif total_sleep_time >= 5:
                        st.warning("⚠️ **Total Sleep Time**: {:.1f} hours (moderate)")
                    else:
                        st.error("❌ **Total Sleep Time**: {:.1f} hours (insufficient)")
                    
                    st.write(f"**Sleep Windows Found**: {len(sleep_windows)}")
                    
                    # Sleep optimization recommendations
                    if len(sleep_windows) > 0:
                        st.subheader("🔧 Sleep Optimization")
                        
                        # Find problematic doses that interfere with sleep
                        problematic_doses = []
                        for dose in all_doses:
                            dose_time_hours = st.session_state.simulator._minutes_to_decimal_hours(dose['time'])
                            
                            # Check if dose interferes with any sleep window
                            for start, end in sleep_windows:
                                # If dose is taken during sleep window or too close to start
                                if (start <= dose_time_hours <= end) or (0 <= start - dose_time_hours <= 2):
                                    problematic_doses.append({
                                        'dose': dose,
                                        'time': dose_time_hours,
                                        'issue': 'Taken during sleep window' if start <= dose_time_hours <= end else 'Too close to sleep start'
                                    })
                        
                        if problematic_doses:
                            st.warning("⚠️ **Doses that may interfere with sleep:**")
                            for prob in problematic_doses:
                                dose = prob['dose']
                                if dose['type'] == 'medication':
                                    st.write(f"• {dose['dosage']}mg {dose.get('medication_name', 'medication')} at {format_time_hours_minutes(prob['time'])} - {prob['issue']}")
                                else:
                                    st.write(f"• {dose['quantity']}x {dose['stimulant_name']} at {format_time_hours_minutes(prob['time'])} - {prob['issue']}")
                        
                        # Suggest optimal timing for new doses
                        st.write("**💡 Tips for better sleep:**")
                        st.write("• Avoid stimulants 6+ hours before desired sleep time")
                        st.write("• Take sleep-promoting medications 1-2 hours before sleep")
                        st.write("• Consider adjusting dose timing to create longer sleep windows")
                        
                        # Export sleep schedule
                        st.subheader("📥 Export Sleep Data")
                        sleep_schedule = {
                            'export_time': datetime.now().isoformat(),
                            'sleep_threshold': sleep_threshold,
                            'sleep_windows': [
                                {
                                    'start': start,
                                    'end': end,
                                    'start_formatted': format_time_hours_minutes(start),
                                    'end_formatted': format_time_hours_minutes(end),
                                    'duration': end - start
                                }
                                for start, end in sleep_windows
                            ],
                            'total_sleep_time': sum(end - start for start, end in sleep_windows),
                            'recommendations': [
                                'Avoid stimulants 6+ hours before sleep',
                                'Take sleep-promoting medications 1-2 hours before sleep',
                                'Consider adjusting dose timing for longer sleep windows'
                            ]
                        }
                        
                        # Create downloadable JSON
                        sleep_json = json.dumps(sleep_schedule, indent=2)
                        st.download_button(
                            label="📥 Download Sleep Schedule",
                            data=sleep_json,
                            file_name=f"sleep_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                        
            else:
                st.info("No suitable sleep windows found with current threshold.")
                st.write("💡 **Tip**: Try lowering the sleep threshold or adjusting medication timing to create better sleep opportunities.")
                
                # Show current effect levels at typical sleep times
                st.subheader("🔍 Current Sleep Readiness")
                typical_sleep_times = [22, 23, 0, 1, 2, 3, 4, 5, 6]  # 10 PM to 6 AM
                
                sleep_readiness = []
                for hour in typical_sleep_times:
                    if hour in time_points:
                        idx = list(time_points).index(hour)
                        effect = combined_effect[idx]
                        readiness = max(0, sleep_threshold - effect)
                        sleep_readiness.append({
                            "Time": f"{hour:02d}:00",
                            "Effect Level": f"{effect:.3f}",
                            "Sleep Readiness": f"{readiness:.3f}",
                            "Status": "🟢 Good" if readiness > sleep_threshold * 0.5 else "🟡 Moderate" if readiness > 0 else "🔴 Poor"
                        })
                
                if sleep_readiness:
                    readiness_df = pd.DataFrame(sleep_readiness)
                    st.dataframe(readiness_df, use_container_width=True, hide_index=True)
        
        else:
            # Check if there are doses but they all failed
            all_doses = st.session_state.simulator.get_all_doses()
            if all_doses:
                failed_doses = st.session_state.simulator.get_failed_doses()
                if len(failed_doses) == len(all_doses):
                    st.error("❌ **Error**: All doses failed to generate curves. Check the console for error details.")
                else:
                    st.info("Add some medications or stimulants to see the timeline!")
            else:
                st.info("Add some medications or stimulants to see the timeline!")
    
    with col2:
        # Summary information
        st.subheader("📋 Summary")
        
        # Medication summary
        medications = st.session_state.simulator.get_medication_summary()
        if medications:
            st.write("**💊 Medications:**")
            for med in medications:
                dose_time_str = st.session_state.simulator._minutes_to_time(med['time'])
                st.write(f"• {med['dosage']}mg {med.get('medication_name', 'medication')} at {dose_time_str}")
        
        # Stimulant summary
        stimulants = st.session_state.simulator.get_stimulant_summary()
        if stimulants:
            st.write("**☕ Stimulants:**")
            for stim in stimulants:
                dose_time_str = st.session_state.simulator._minutes_to_time(stim['time'])
                st.write(f"• {stim['quantity']}x {stim['stimulant_name']} at {dose_time_str}")
                if stim.get('component_name'):
                    st.write(f"  ({stim['component_name']})")
        
        if not medications and not stimulants:
            st.info("No doses added yet.")
        
        # Export/Import functionality
        st.subheader("💾 Data Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Export Schedule"):
                filename = st.session_state.simulator.export_schedule()
                st.success(f"Exported to {filename}")
        
        with col2:
            uploaded_file = st.file_uploader("📥 Import Schedule", type=['json'])
            if uploaded_file is not None:
                try:
                    data = json.load(uploaded_file)
                    st.session_state.simulator.import_schedule(data)
                    st.success("Schedule imported successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error importing schedule: {e}")
        
        # localStorage Management
        st.subheader("💾 Input Data Storage")
        st.info("Your input preferences are automatically saved and will be restored when you return.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Saved Inputs", type="secondary"):
                clear_local_storage(LOCAL_STORAGE_KEYS['medication_inputs'])
                clear_local_storage(LOCAL_STORAGE_KEYS['stimulant_inputs'])
                clear_local_storage(LOCAL_STORAGE_KEYS['painkiller_inputs'])
                clear_local_storage(LOCAL_STORAGE_KEYS['sleep_settings'])
                clear_local_storage(LOCAL_STORAGE_KEYS['app_settings'])
                
                # Clear from session state
                for key in ['saved_medication_inputs', 'saved_stimulant_inputs', 'saved_painkiller_inputs', 'saved_sleep_settings', 'saved_app_settings']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.success("All saved input data cleared!")
                st.rerun()
        
        with col2:
            if st.button("📥 Export Input Data", type="secondary"):
                all_input_data = {
                    'medication_inputs': st.session_state.get('saved_medication_inputs', {}),
                    'stimulant_inputs': st.session_state.get('saved_stimulant_inputs', {}),
                    'painkiller_inputs': st.session_state.get('saved_painkiller_inputs', {}),
                    'sleep_settings': st.session_state.get('saved_sleep_settings', {}),
                    'app_settings': st.session_state.get('saved_app_settings', {})
                }
                
                input_json = json.dumps(all_input_data, indent=2)
                st.download_button(
                    label="📥 Download Input Data",
                    data=input_json,
                    file_name=f"input_preferences_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        # Import input data
        st.subheader("📥 Import Input Data")
        uploaded_input_file = st.file_uploader("Upload Input Preferences", type=['json'], key="input_preferences_uploader")
        if uploaded_input_file is not None:
            try:
                input_data = json.load(uploaded_input_file)
                
                # Restore input data to session state
                if 'medication_inputs' in input_data:
                    st.session_state.saved_medication_inputs = input_data['medication_inputs']
                if 'stimulant_inputs' in input_data:
                    st.session_state.saved_stimulant_inputs = input_data['stimulant_inputs']
                if 'painkiller_inputs' in input_data:
                    st.session_state.saved_painkiller_inputs = input_data['painkiller_inputs']
                if 'sleep_settings' in input_data:
                    st.session_state.saved_sleep_settings = input_data['sleep_settings']
                if 'app_settings' in input_data:
                    st.session_state.saved_app_settings = input_data['app_settings']
                
                # Save to localStorage
                for key, data in input_data.items():
                    if key in LOCAL_STORAGE_KEYS.values():
                        save_to_local_storage(data, key)
                
                st.success("Input preferences imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing input preferences: {e}")

def painkillers_app():
    st.title("💊 Painkiller Timeline Simulator")
    st.markdown("Simulate and visualize painkiller effects throughout the day")
    
    # Show localStorage status
    if any(key in st.session_state for key in ['saved_medication_inputs', 'saved_stimulant_inputs', 'saved_painkiller_inputs', 'saved_sleep_settings', 'saved_app_settings']):
        st.success("💾 **Input Data Saved**: Your preferences are automatically saved and will be restored when you return.")
    
    # Initialize session state for painkillers with localStorage persistence
    if 'painkiller_doses' not in st.session_state:
        try:
            # Try to load from localStorage first
            saved_doses = load_painkiller_doses()
            if saved_doses and isinstance(saved_doses, list):
                st.session_state.painkiller_doses = saved_doses
            else:
                st.session_state.painkiller_doses = []
        except Exception as e:
            print(f"Error loading painkiller doses: {e}")
            st.session_state.painkiller_doses = []
    
    # Sidebar for painkiller management
    with st.sidebar:
        st.header("📋 Painkiller Management")
        
        # Load available painkillers from unified database
        available_painkillers = []
        if st.session_state.medications_loaded and medications_data.get('painkillers'):
            available_painkillers = list(medications_data['painkillers'].keys())
        
        st.subheader("Add New Painkiller")
        
        if not available_painkillers:
            st.error("No painkillers available. Please check that medications.json is properly loaded.")
        else:
            # Load saved painkiller inputs
            saved_pk_inputs = st.session_state.get('saved_painkiller_inputs', {})
            default_pk_time = time(8, 0)
            default_pk = available_painkillers[0] if available_painkillers else None
            default_pills = 1
            
            if saved_pk_inputs:
                try:
                    if 'dose_time' in saved_pk_inputs:
                        time_str = saved_pk_inputs['dose_time']
                        hour, minute = map(int, time_str.split(':'))
                        default_pk_time = time(hour, minute)
                    if 'painkiller_name' in saved_pk_inputs and saved_pk_inputs['painkiller_name'] in available_painkillers:
                        default_pk = saved_pk_inputs['painkiller_name']
                    if 'pill_count' in saved_pk_inputs:
                        default_pills = int(saved_pk_inputs['pill_count'])
                except:
                    pass
            
            col1, col2 = st.columns(2)
            with col1:
                dose_time = st.time_input("Dose Time", value=default_pk_time, key="pk_time")
                painkiller_name = st.selectbox("Painkiller Type", available_painkillers, index=available_painkillers.index(default_pk) if default_pk else 0, key="pk_name")
            with col2:
                pill_count = st.number_input("Pills", min_value=1, max_value=4, value=default_pills, step=1, key="pk_pills")
            
            # Auto-save painkiller inputs
            current_pk_inputs = {
                'dose_time': dose_time.strftime("%H:%M"),
                'painkiller_name': painkiller_name,
                'pill_count': pill_count
            }
            auto_save_inputs('painkiller', current_pk_inputs)
        
        # Auto-calculate and display dosage based on product and pill count
        if painkiller_name and painkiller_name in available_painkillers:
            try:
                if st.session_state.medications_loaded and medications_data.get('painkillers', {}).get(painkiller_name):
                    pk_info = medications_data['painkillers'][painkiller_name]
                    
                    # Get base dosage from data
                    base_dosage = pk_info.get('standard_dose_mg', 0)
                    
                    if base_dosage > 0:
                        total_dosage = base_dosage * pill_count
                        st.metric("Total Dosage", f"{total_dosage}mg")
                        
                        # Show per-pill dosage for clarity
                        if pill_count > 1:
                            st.caption(f"({base_dosage}mg per pill)")
                        
                        # Show typical dosing information from data
                        typical_pills = 1 if base_dosage >= 500 else 2
                        typical_dose = base_dosage * typical_pills
                        st.info(f"💡 **Typical dose**: {typical_pills} pill{'s' if typical_pills > 1 else ''} ({typical_dose}mg)")
            except Exception as e:
                print(f"Warning: Could not calculate dosage for {painkiller_name}: {e}")
                pass
        
        # Show painkiller info
        if painkiller_name:
            try:
                if st.session_state.medications_loaded and medications_data.get('painkillers', {}).get(painkiller_name):
                    pk_info = medications_data['painkillers'][painkiller_name]
                    
                    onset_hours = pk_info['onset_min'] / 60.0
                    peak_time_hours = pk_info['t_peak_min'] / 60.0
                    peak_duration_hours = pk_info['peak_duration_min'] / 60.0
                    duration_hours = pk_info['duration_min'] / 60.0
                    wear_off_hours = pk_info['wear_off_min'] / 60.0
                    
                    st.info(f"**{painkiller_name}**: Onset {format_time_hours_minutes(onset_hours)}, Peak at {format_time_hours_minutes(peak_time_hours)}, Peak duration {format_duration_hours_minutes(peak_duration_hours)}, Total {format_duration_hours_minutes(duration_hours)}")
            except Exception as e:
                st.warning(f"Could not load painkiller information: {str(e)}")
        
        if painkiller_name and st.button("➕ Add Painkiller", type="primary", key="add_pk"):
            time_str = dose_time.strftime("%H:%M")
            
            # Calculate actual dosage based on pill count
            base_dosage = 0
            if st.session_state.medications_loaded and medications_data.get('painkillers', {}).get(painkiller_name):
                pk_info = medications_data['painkillers'][painkiller_name]
                base_dosage = pk_info.get('standard_dose_mg', 0)
            
            actual_dosage = base_dosage * pill_count
            
            # Create painkiller dose entry
            dose_entry = {
                'id': len(st.session_state.painkiller_doses),
                'time': time_str,
                'time_hours': dose_time.hour + dose_time.minute / 60.0,
                'name': painkiller_name,
                'pills': pill_count,
                'dosage': actual_dosage,
                'base_dosage': base_dosage
            }
            
            # Add PK parameters if available
            try:
                if st.session_state.medications_loaded and medications_data.get('painkillers', {}).get(painkiller_name):
                    pk_info = medications_data['painkillers'][painkiller_name]
                    dose_entry.update({
                        'onset_min': pk_info['onset_min'],
                        'peak_time_min': pk_info['t_peak_min'],
                        'peak_duration_min': pk_info['peak_duration_min'],
                        'duration_min': pk_info['duration_min'],
                        'wear_off_duration_min': pk_info['wear_off_min']
                    })
            except Exception as e:
                print(f"Warning: Could not add PK parameters for {painkiller_name}: {e}")
                pass
            
            st.session_state.painkiller_doses.append(dose_entry)
            # Save to localStorage for persistence
            save_painkiller_doses(st.session_state.painkiller_doses)
            pill_text = "pill" if pill_count == 1 else "pills"
            st.success(f"Added {pill_count} {pill_text} of {painkiller_name} ({actual_dosage}mg total) at {time_str}")
            st.rerun()
        
        st.divider()
        
        # Current painkiller doses
        st.subheader("Current Painkiller Doses")
        
        if not st.session_state.painkiller_doses:
            st.info("No painkillers added yet")
        else:
            for dose in st.session_state.painkiller_doses:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    pill_text = f"pill(s)" if dose.get('pills', 1) > 1 else "pill"
                    st.write(f"**💊 {dose.get('pills', 1)} {pill_text} {dose['name']} ({dose['dosage']}mg total)** at {dose['time']}")
                
                with col2:
                    if 'duration_min' in dose:
                        duration_hours = dose['duration_min'] / 60.0
                        st.write(f"Duration: {format_duration_hours_minutes(duration_hours)}")
                    else:
                        st.write("Duration: Unknown")
                
                with col3:
                    if st.button("🗑️", key=f"del_pk_{dose['id']}"):
                        st.session_state.painkiller_doses.remove(dose)
                        # Save to localStorage for persistence
                        save_painkiller_doses(st.session_state.painkiller_doses)
                        st.rerun()
                
                # Show curve details in expandable section
                with st.expander(f"Curve details for {dose['name']}"):
                    if all(key in dose for key in ['onset_min', 'peak_time_min', 'duration_min']):
                        onset_hours = dose['onset_min'] / 60.0
                        peak_time_hours = dose['peak_time_min'] / 60.0
                        duration_hours = dose['duration_min'] / 60.0
                        
                        st.write(f"**Onset**: {format_duration_hours_minutes(onset_hours)} → **Tmax**: {format_duration_hours_minutes(peak_time_hours)} → **Duration**: {format_duration_hours_minutes(duration_hours)}")
                        
                        if 'intensity_peak' in dose:
                            st.write(f"**Peak Intensity**: {dose['intensity_peak']}/10")
                        if 'intensity_avg' in dose:
                            st.write(f"**Average Intensity**: {dose['intensity_avg']}/10")
                        
                        # Calculate actual curve phases
                        onset_time = onset_hours
                        tmax_time = peak_time_hours  # Time to maximum effect
                        plateau_duration = dose.get('peak_duration_min', 60) / 60.0  # Duration of therapeutic plateau
                        duration = duration_hours
                        
                        # Calculate phase durations
                        rise_duration = tmax_time  # Time from dose to peak
                        fall_duration = dose.get('wear_off_duration_min', 60) / 60.0 if 'wear_off_duration_min' in dose else 1.0
                        
                        st.write(f"**Rise Phase**: 0h → {format_duration_hours_minutes(tmax_time)} ({format_duration_hours_minutes(rise_duration)})")
                        st.write(f"**Plateau Phase**: {format_duration_hours_minutes(tmax_time)} → {format_duration_hours_minutes(tmax_time + plateau_duration)} ({format_duration_hours_minutes(plateau_duration)})")
                        st.write(f"**Fall Phase**: {format_duration_hours_minutes(tmax_time + plateau_duration)} → {format_duration_hours_minutes(duration)} ({format_duration_hours_minutes(fall_duration)})")
                        
                        # Show timing relative to dose time
                        dose_time_str = dose['time']
                        onset_time_str = format_time_hours_minutes(dose['time_hours'] + onset_time)
                        tmax_time_str = format_time_hours_minutes(dose['time_hours'] + tmax_time)
                        plateau_end_str = format_time_hours_minutes(dose['time_hours'] + tmax_time + plateau_duration)
                        end_time_str = format_time_hours_minutes(dose['time_hours'] + duration)
                        
                        st.write(f"**Timeline**: Dose at {dose_time_str} → Onset at {onset_time_str} → Tmax at {tmax_time_str} → Plateau ends at {plateau_end_str} → Ends at {end_time_str}")
                    else:
                        st.warning("Incomplete painkiller data - some parameters missing")
        
        if st.session_state.painkiller_doses and st.button("🗑️ Clear All Painkillers"):
            st.session_state.painkiller_doses.clear()
            # Save to localStorage for persistence
            save_painkiller_doses(st.session_state.painkiller_doses)
            st.rerun()
    
    # Main content area - Make graph wider
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Generate painkiller timeline
        time_points, pain_level = generate_painkiller_timeline()
        
        # Create painkiller plot
        fig = create_painkiller_plot(time_points, pain_level)
        st.plotly_chart(fig, use_container_width=True)
        
        # Pain relief windows
        pain_relief_windows = find_pain_relief_windows(time_points, pain_level)
        
        if any(pain_relief_windows.values()):
            st.subheader("😌 Pain Relief Windows")
            
            # Display relief windows by category
            for relief_type, windows in pain_relief_windows.items():
                if windows:
                    relief_label = relief_type.title()
                    if relief_type == 'moderate':
                        relief_icon = "🟠"
                        relief_desc = "30% pain reduction"
                    elif relief_type == 'strong':
                        relief_icon = "🟢"
                        relief_desc = "60% pain reduction"
                    else:  # complete
                        relief_icon = "🔵"
                        relief_desc = "80% pain reduction"
                    
                    st.markdown(f"**{relief_icon} {relief_label} Relief ({relief_desc})**")
                    for start, end in windows:
                        start_str = format_time_hours_minutes(start)
                        end_str = format_time_hours_minutes(end)
                        st.info(f"**{start_str}** to **{end_str}** (Duration: {format_duration_hours_minutes(end-start)})")
        else:
            st.warning("⚠️ No significant pain relief windows found")
    
    with col2:
        # Statistics and insights
        st.subheader("📊 Pain Relief Statistics")
        
        if len(st.session_state.painkiller_doses) > 0:
            max_pain_relief_time = time_points[np.argmax(pain_level)] if len(pain_level) > 0 else 0
            max_pain_relief_str = format_time_hours_minutes(max_pain_relief_time)
            
            st.metric("Peak Relief Time", max_pain_relief_str)
            st.metric("Peak Relief Level", f"{pain_level.max():.1f}/10" if len(pain_level) > 0 else "0/10")
            st.metric("Average Relief", f"{pain_level.mean():.1f}/10" if len(pain_level) > 0 else "0/10")
            
            # Show additive effect indicator
            if len(st.session_state.painkiller_doses) > 1:
                if pain_level.max() > 8.0:
                    st.success(f"🚀 **Strong Combined Relief!** Multiple painkillers are working together (max: {pain_level.max():.1f}/10)")
                else:
                    st.info(f"📊 **Multiple Painkillers**: {len(st.session_state.painkiller_doses)} doses with combined relief of {pain_level.max():.1f}/10")
            
            # Pain relief summary metrics based on clinical evidence
            st.subheader("📊 Clinical Relief Summary")
            
            # Calculate clinically meaningful relief metrics
            moderate_relief_hours = np.sum(pain_level > 3.0) * 0.1  # 30% pain reduction
            strong_relief_hours = np.sum(pain_level > 6.0) * 0.1    # 60% pain reduction
            complete_relief_hours = np.sum(pain_level > 8.0) * 0.1  # 80% pain reduction
            
            # Time spent at different relief levels
            minimal_relief_hours = np.sum(pain_level > 1.0) * 0.1   # Any measurable relief
            no_relief_hours = np.sum(pain_level <= 1.0) * 0.1       # No meaningful relief
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Moderate Relief (30%+)", f"{moderate_relief_hours:.1f}h")
                st.metric("Strong Relief (60%+)", f"{strong_relief_hours:.1f}h")
            
            with col2:
                st.metric("Complete Relief (80%+)", f"{complete_relief_hours:.1f}h")
                st.metric("Minimal Relief (10%+)", f"{minimal_relief_hours:.1f}h")
            
            # Additional clinical insights
            st.markdown("---")
            if complete_relief_hours > 0:
                st.success(f"🎯 **Complete Pain Relief**: {complete_relief_hours:.1f} hours of 80%+ pain reduction")
            if strong_relief_hours > 8:
                st.success(f"✅ **Well-Managed Pain**: {strong_relief_hours:.1f} hours of strong relief (60%+)")
            elif strong_relief_hours < 4 and strong_relief_hours > 0:
                st.warning(f"⚠️ **Limited Relief**: Only {strong_relief_hours:.1f} hours of strong relief - consider dose timing")
            
            # Clinical recommendations
            st.markdown("---")
            st.subheader("💡 Clinical Recommendations")
            
            if len(st.session_state.painkiller_doses) == 1:
                st.info("**Single Dose Strategy**: Consider adding a second dose before the first wears off to maintain continuous relief")
            elif len(st.session_state.painkiller_doses) > 1:
                if strong_relief_hours > 12:
                    st.success("**Excellent Coverage**: Your dosing schedule provides comprehensive pain relief throughout the day")
                elif strong_relief_hours > 8:
                    st.info("**Good Coverage**: Consider minor timing adjustments to minimize gaps in relief")
                else:
                    st.warning("**Gaps in Relief**: Review timing to ensure continuous pain control")
            
            # Specific recommendations based on painkiller types
            painkiller_types = [dose['name'] for dose in st.session_state.painkiller_doses]
            if 'paracetamol_500mg' in painkiller_types and 'ibuprofen_400mg' in painkiller_types:
                st.success("**Combination Therapy**: Paracetamol + Ibuprofen is clinically proven to work synergistically")
        else:
            st.info("Add painkillers to see statistics")

def generate_painkiller_timeline():
    """Generate timeline for painkiller effects"""
    # Use dynamic time points from simulator if available, otherwise fallback to 24h
    if 'simulator' in st.session_state and hasattr(st.session_state.simulator, 'time_points') and len(st.session_state.simulator.time_points) > 0:
        time_points = st.session_state.simulator.time_points
    else:
        time_points = np.arange(0, 24.1, 0.1)  # Fallback to 24 hours in 0.1 hour intervals
    pain_level = np.zeros_like(time_points)
    
    for dose in st.session_state.painkiller_doses:
        if not all(key in dose for key in ['time_hours', 'onset_min', 'peak_time_min', 'duration_min']):
            continue
            
        dose_time = dose['time_hours']
        onset_hours = dose['onset_min'] / 60.0
        tmax_hours = dose['peak_time_min'] / 60.0  # Time to maximum effect (Tmax)
        duration_hours = dose['duration_min'] / 60.0
        peak_duration_hours = dose.get('peak_duration_min', 60) / 60.0  # Duration of peak effect
        
        # Calculate pill count effect on intensity
        pill_count = dose.get('pills', 1)
        
        # For modified-release formulations, multiple pills primarily extend duration
        # For immediate-release, multiple pills increase peak intensity
        if 'mr' in dose['name'].lower() or 'modified' in dose['name'].lower():
            # MR: Multiple pills extend duration, slight increase in peak
            intensity_multiplier = min(1.5, 1.0 + (pill_count - 1) * 0.2)  # Max 50% increase
            duration_multiplier = 1.0 + (pill_count - 1) * 0.3  # 30% duration increase per pill
        else:
            # Immediate release: Multiple pills increase peak intensity
            intensity_multiplier = min(2.0, 1.0 + (pill_count - 1) * 0.4)  # Max 100% increase
            duration_multiplier = 1.0 + (pill_count - 1) * 0.1  # 10% duration increase per pill
        
        base_intensity = dose.get('intensity_peak', 5.0)  # Default to 5/10 if not specified
        adjusted_intensity = base_intensity * intensity_multiplier
        adjusted_duration = duration_hours * duration_multiplier
        adjusted_peak_duration = peak_duration_hours * duration_multiplier
        
        # Calculate effect curve for this dose
        for i, t in enumerate(time_points):
            if t < dose_time:
                continue
            
            time_since_dose = t - dose_time
            
            if time_since_dose < onset_hours:
                # Rising phase (0 to onset)
                effect = 0
            elif time_since_dose < tmax_hours:
                # Rising phase (onset to Tmax)
                progress = (time_since_dose - onset_hours) / (tmax_hours - onset_hours)
                effect = adjusted_intensity * progress
            elif time_since_dose < tmax_hours + adjusted_peak_duration:
                # Peak phase (Tmax to end of peak duration)
                effect = adjusted_intensity
            elif time_since_dose < adjusted_duration:
                # Falling phase (end of peak to end of duration)
                plateau_end = tmax_hours + adjusted_peak_duration
                wear_off_duration = dose.get('wear_off_duration_min', 60) / 60.0 * duration_multiplier
                
                if time_since_dose < plateau_end + wear_off_duration:
                    # In wear-off phase
                    fall_progress = (time_since_dose - plateau_end) / wear_off_duration
                    effect = adjusted_intensity * (1 - fall_progress)
                else:
                    # Beyond wear-off - no effect
                    effect = 0
            else:
                # No effect
                effect = 0
            
            # Add to total pain relief (use maximum effect if multiple doses overlap)
            pain_level[i] = max(pain_level[i], effect)
    
    return time_points, pain_level

def create_painkiller_plot(time_points, pain_level):
    """Create the painkiller timeline visualization"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Combined Pain Relief Timeline", "Individual Painkillers"),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3]
    )
    
    # Main pain relief curve
    fig.add_trace(
        go.Scatter(
            x=time_points,
            y=pain_level,
            mode='lines',
            name='Combined Relief',
            line=dict(color='#e74c3c', width=4),
            fill='tonexty',
            fillcolor='rgba(231, 76, 60, 0.2)'
        ),
        row=1, col=1
    )
    
    # Pain relief threshold lines based on clinical evidence
    # Moderate relief (clinically meaningful pain reduction)
    fig.add_hline(
        y=3.0,
        line_dash="dash",
        line_color="orange",
        annotation_text="Moderate Relief (30% pain reduction)",
        row=1, col=1
    )
    
    # Strong relief (substantial pain reduction)
    fig.add_hline(
        y=6.0,
        line_dash="dash",
        line_color="green",
        annotation_text="Strong Relief (60% pain reduction)",
        row=1, col=1
    )
    
    # Individual painkiller curves
    for dose in st.session_state.painkiller_doses:
        if not all(key in dose for key in ['time_hours', 'onset_min', 'peak_time_min', 'duration_min']):
            continue
            
        dose_time = dose['time_hours']
        onset_hours = dose['onset_min'] / 60.0
        tmax_hours = dose['peak_time_min'] / 60.0  # Time to maximum effect (Tmax)
        duration_hours = dose['duration_min'] / 60.0
        peak_duration_hours = dose.get('peak_duration_min', 60) / 60.0  # Duration of peak effect
        
        # Generate individual curve
        individual_effect = np.zeros_like(time_points)
        for i, t in enumerate(time_points):
            if t < dose_time:
                continue
            
            time_since_dose = t - dose_time
            
            if time_since_dose < onset_hours:
                # Rising phase (0 to onset)
                effect = 0
            elif time_since_dose < tmax_hours:
                # Rising phase (onset to Tmax)
                progress = (time_since_dose - onset_hours) / (tmax_hours - onset_hours)
                effect = dose.get('intensity_peak', 5.0) * progress
            elif time_since_dose < tmax_hours + peak_duration_hours:
                # Peak phase (Tmax to end of peak duration)
                effect = dose.get('intensity_peak', 5.0)
            elif time_since_dose < duration_hours:
                # Falling phase (end of peak to end of duration)
                fall_duration = duration_hours - (tmax_hours + peak_duration_hours)
                fall_progress = (time_since_dose - (tmax_hours + peak_duration_hours)) / fall_duration
                effect = dose.get('intensity_peak', 5.0) * (1 - fall_progress)
            else:
                effect = 0
            
            individual_effect[i] = effect
        
        # Add individual curve
        fig.add_trace(
            go.Scatter(
                x=time_points,
                y=individual_effect,
                mode='lines',
                name=f"{dose['name']}",
                line=dict(color='#f39c12', width=2, dash='dash'),
                opacity=0.7
            ),
            row=2, col=1
        )
        
        # Add dose markers
        pill_text = f"({dose.get('pills', 1)} pills)" if dose.get('pills', 1) > 1 else ""
        fig.add_vline(
            x=dose['time_hours'],
            line_width=3,
            line_color="red",
            annotation_text=f"{dose['dosage']}mg {pill_text}",
            annotation_position="top left",
            annotation=dict(
                yshift=10,
                font=dict(size=10),
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="red",
                borderwidth=1
            ),
            row=1, col=1
        )
        
        # Peak window shading (from Tmax to end of peak duration)
        peak_start = dose_time + tmax_hours
        peak_end = dose_time + tmax_hours + peak_duration_hours
        
        # Ensure peak window doesn't extend beyond total duration
        total_duration = dose_time + duration_hours
        if peak_end > total_duration:
            peak_end = total_duration
        
        fig.add_vrect(
            x0=peak_start, x1=peak_end,
            fillcolor="rgba(0, 255, 0, 0.1)",
            layer="below",
            line_width=0,
            annotation_text="Peak Relief",
            annotation_position="top right",
            annotation=dict(
                yshift=20,
                font=dict(size=9),
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="green",
                borderwidth=1
            )
        )
    
    # Update layout
    max_relief = max(10.1, pain_level.max() * 1.1) if len(pain_level) > 0 else 10.1
    
    # Create custom x-axis tick labels that span the actual time range
    if len(time_points) > 0:
        start_hour = time_points.min()
        end_hour = time_points.max()
        
        # Create ticks that span the full range with reasonable spacing
        if end_hour - start_hour <= 24:
            # For 24h or less, use standard hourly ticks
            tick_hours = list(range(int(start_hour), int(end_hour) + 1, max(1, int(end_hour - start_hour) // 8)))
        else:
            # For longer periods, use 3-4 hour spacing
            spacing = max(1, int((end_hour - start_hour) // 8))
            tick_hours = list(range(int(start_hour), int(end_hour) + 1, spacing))
        
        # Ensure we have start and end points
        if start_hour not in tick_hours:
            tick_hours.insert(0, start_hour)
        if end_hour not in tick_hours:
            tick_hours.append(end_hour)
            
        tick_labels = [format_time_across_midnight(hour) for hour in tick_hours]
    else:
        # Fallback to 24h format
        tick_hours = list(range(0, 25, 3))
        tick_labels = [format_time_hours_minutes(hour) for hour in tick_hours]
    
    fig.update_xaxes(
        title_text="Time (hours)", 
        range=[time_points.min() if len(time_points) > 0 else 0, time_points.max() if len(time_points) > 0 else 24], 
        tickmode='array',
        tickvals=tick_hours,
        ticktext=tick_labels,
        row=1, col=1
    )
    fig.update_yaxes(title_text="Pain Relief Level (/10)", range=[0, max_relief], row=1, col=1)
    
    fig.update_xaxes(
        title_text="Time (hours)", 
        range=[time_points.min() if len(time_points) > 0 else 0, time_points.max() if len(time_points) > 0 else 24], 
        tickmode='array',
        tickvals=tick_hours,
        ticktext=tick_labels,
        row=2, col=1
    )
    fig.update_yaxes(title_text="Individual Relief", row=2, col=1)
    
    # Update hover template
    for trace in fig.data:
        if trace.x is not None and len(trace.x) > 0:
            hover_x = [format_time_across_midnight(x) for x in trace.x]
            trace.customdata = hover_x
            trace.hovertemplate = (
                "<b>%{fullData.name}</b><br>" +
                "Time: %{customdata}<br>" +
                "Relief: %{y:.1f}/10<br>" +
                "<extra></extra>"
            )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Pain Relief Timeline",
        hovermode='x unified'
    )
    
    return fig

def find_pain_relief_windows(time_points, pain_level):
    """Find windows where pain relief is clinically meaningful"""
    relief_windows = {
        'moderate': [],  # 30% pain reduction (3/10)
        'strong': [],    # 60% pain reduction (6/10)
        'complete': []   # 80% pain reduction (8/10)
    }
    
    thresholds = {
        'moderate': 3.0,
        'strong': 6.0,
        'complete': 8.0
    }
    
    for relief_type, threshold in thresholds.items():
        above_threshold = pain_level > threshold
        
        if not np.any(above_threshold):
            continue
        
        # Find start and end points of relief windows
        start_idx = None
        for i, above in enumerate(above_threshold):
            if above and start_idx is None:
                start_idx = i
            elif not above and start_idx is not None:
                end_idx = i - 1
                relief_windows[relief_type].append((time_points[start_idx], time_points[end_idx]))
                start_idx = None
        
        # Handle case where relief extends to end of day
        if start_idx is not None:
            relief_windows[relief_type].append((time_points[start_idx], time_points[-1]))
    
    return relief_windows

if __name__ == "__main__":
    main()
