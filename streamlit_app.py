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
from data_schema import load_med_file

# Load unified medications file with error handling
try:
    medications_data = load_med_file("medications.json")
    st.session_state.medications_loaded = True
except ValueError as e:
    st.warning(f"⚠️ Warning: Could not load medications.json - {e}")
    st.session_state.medications_loaded = False
except FileNotFoundError:
    st.warning("⚠️ Warning: medications.json file not found")
    st.session_state.medications_loaded = False
except Exception as e:
    st.warning(f"⚠️ Warning: Unexpected error loading medications.json - {e}")
    st.session_state.medications_loaded = False

# Load profiles with validation
def load_profiles_with_validation():
    """Load profiles and validate medication references"""
    try:
        with open('profiles.json', 'r') as f:
            profiles = json.load(f)
        
        # Validate each profile
        validated_profiles = []
        warnings = []
        
        for profile in profiles:
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
            validated_profile['medications'] = [e for e in valid_entries if e.get('type') == 'medication']
            validated_profile['stimulants'] = [e for e in valid_entries if e.get('type') == 'stimulant']
            
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
profiles, profile_warnings = load_profiles_with_validation()

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

def format_duration_hours_minutes(decimal_hours):
    """Convert decimal hours to duration format (e.g., 2h 30m)"""
    hours = int(decimal_hours)
    minutes = int((decimal_hours % 1) * 60)
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{minutes}m"

# Page configuration
st.set_page_config(
    page_title="ADHD Medication & Stimulant Timeline Simulator",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'simulator' not in st.session_state:
    st.session_state.simulator = MedicationSimulator()

def main():
    # Navigation
    st.sidebar.title("📱 App Navigation")
    app_mode = st.sidebar.selectbox(
        "Choose Application",
        ["ADHD Medications", "Painkillers"],
        key="app_navigation"
    )
    
    if app_mode == "ADHD Medications":
        adhd_medications_app()
    else:
        painkillers_app()

def adhd_medications_app():
    st.title("💊 ADHD Medication & Stimulant Timeline Simulator")
    st.markdown("Simulate and visualize medication and stimulant effects throughout the day")
    
    # Sidebar for dose management
    with st.sidebar:
        st.header("📋 Dose Management")
        
        # Tab for different types of doses
        tab1, tab2 = st.tabs(["💊 Medications", "☕ Stimulants"])
        
        with tab1:
            st.subheader("Add New Medication")
            
            # Load available prescription medications from unified database
            try:
                if st.session_state.medications_loaded:
                    available_medications = list(medications_data['stimulants']['prescription_stimulants'].keys())
                else:
                    available_medications = ['ritalin_IR', 'ritalin_LA', 'concerta', 'adderall_IR', 'adderall_XR', 'vyvanse', 'dexedrine_IR', 'dexedrine_ER']
            except:
                available_medications = ['ritalin_IR', 'ritalin_LA', 'concerta', 'adderall_IR', 'adderall_XR', 'vyvanse', 'dexedrine_IR', 'dexedrine_ER']
            
            col1, col2 = st.columns(2)
            with col1:
                dose_time = st.time_input("Dose Time", value=time(8, 0), key="med_time")
                medication_name = st.selectbox("Medication Type", available_medications, key="med_name")
            with col2:
                dosage = st.number_input("Dosage (mg)", min_value=1.0, max_value=100.0, value=20.0, step=1.0, key="med_dosage")
            
            # Show medication info if prescription medication is selected
            if medication_name != 'Custom':
                try:
                    if st.session_state.medications_loaded:
                        med_info = medications_data['stimulants']['prescription_stimulants'][medication_name]
                        
                        # Convert minutes to hours for display
                        onset_hours = med_info['onset_min'] / 60.0
                        peak_time_hours = med_info['peak_time_min'] / 60.0
                        peak_duration_hours = med_info['peak_duration_min'] / 60.0
                        duration_hours = med_info['duration_min'] / 60.0
                        wear_off_hours = med_info['wear_off_duration_min'] / 60.0
                        
                        st.info(f"**{medication_name}**: Onset {format_time_hours_minutes(onset_hours)}, Peak at {format_time_hours_minutes(peak_time_hours)}, Peak duration {format_duration_hours_minutes(peak_duration_hours)}, Total {format_duration_hours_minutes(duration_hours)}")
                    else:
                        st.warning("Medications data not loaded")
                except:
                    st.warning("Could not load medication information")
            
            # Advanced parameters (to override prescription defaults)
            with st.expander("Advanced Parameters (Override Defaults)"):
                # Get current values from JSON for prescription medication
                try:
                    if st.session_state.medications_loaded:
                        med_info = medications_data['stimulants']['prescription_stimulants'][medication_name]
                        
                        # Convert minutes to hours for default values
                        default_onset = med_info['onset_min'] / 60.0
                        default_peak = med_info['peak_time_min'] / 60.0
                        default_duration = med_info['duration_min'] / 60.0
                        default_effect = med_info['peak_duration_min'] / 60.0
                    else:
                        default_onset, default_peak, default_duration, default_effect = 1.0, 2.0, 8.0, 1.0
                except:
                    default_onset, default_peak, default_duration, default_effect = 1.0, 2.0, 8.0, 1.0
                
                onset_time = st.slider("Onset Time (hours)", 0.5, 3.0, default_onset, 0.1, key="med_onset")
                peak_time = st.slider("Peak Time (hours)", 1.0, 6.0, default_peak, 0.1, key="med_peak")
                duration = st.slider("Duration (hours)", 4.0, 16.0, default_duration, 0.5, key="med_duration")
                peak_effect = st.slider("Peak Effect", 0.1, 2.0, default_effect, 0.1, key="med_effect")
                
                # Show what values are being overridden
                st.info(f"**Current JSON values**: Onset {format_duration_hours_minutes(default_onset)}, Peak {format_duration_hours_minutes(default_peak)}, Duration {format_duration_hours_minutes(default_duration)}, Effect {default_effect:.2f}")
                st.info(f"**Override values**: Onset {format_duration_hours_minutes(onset_time)}, Peak {format_duration_hours_minutes(peak_time)}, Duration {format_duration_hours_minutes(duration)}, Effect {peak_effect:.2f}")
            
            if st.button("➕ Add Medication", type="primary", key="add_med"):
                time_str = dose_time.strftime("%H:%M")
                
                # Use prescription medication with custom parameters as override
                custom_params = {
                    'onset_time': onset_time,
                    'peak_time': peak_time,
                    'duration': duration,
                    'peak_effect': peak_effect
                }
                st.session_state.simulator.add_medication(
                    time_str, dosage, medication_name=medication_name, custom_params=custom_params
                )
                st.success(f"Added {dosage}mg {medication_name} at {time_str}")
                
                st.rerun()
        
        with tab2:
            st.subheader("Add New Stimulant")
            
            # Load available stimulants from unified database
            try:
                if st.session_state.medications_loaded:
                    available_stimulants = list(medications_data['stimulants']['common_stimulants'].keys())
                else:
                    available_stimulants = ['coffee', 'redbull', 'monster']
            except:
                available_stimulants = ['coffee', 'redbull', 'monster']
            
            col1, col2 = st.columns(2)
            with col1:
                stim_time = st.time_input("Consumption Time", value=time(9, 0), key="stim_time")
                stimulant_name = st.selectbox("Stimulant", available_stimulants, key="stim_name")
            with col2:
                quantity = st.number_input("Quantity", min_value=0.5, max_value=5.0, value=1.0, step=0.5, key="stim_quantity")
            
            # Show component selection for complex stimulants
            if stimulant_name in ['redbull', 'monster']:
                component_name = st.selectbox("Component", ['caffeine', 'taurine'], key="stim_component")
            else:
                component_name = None
            
            # Advanced parameters for stimulants (override defaults)
            with st.expander("Advanced Parameters (Override Defaults)"):
                # Get current values from JSON
                try:
                    if st.session_state.medications_loaded:
                        stim_data = medications_data['stimulants']['common_stimulants'][stimulant_name]
                        
                        if component_name and component_name in stim_data:
                            stim_info = stim_data[component_name]
                        elif 'onset_min' in stim_data:
                            stim_info = stim_data
                        else:
                            stim_info = list(stim_data.values())[0] if stim_data else {}
                        
                        # Convert minutes to hours for default values
                        default_onset = stim_info.get('onset_min', 10) / 60.0
                        default_peak = stim_info.get('peak_time_min', 60) / 60.0
                        default_duration = stim_info.get('duration_min', 360) / 60.0
                        default_effect = stim_info.get('peak_duration_min', 45) / 60.0
                    else:
                        default_onset, default_peak, default_duration, default_effect = 0.17, 1.0, 6.0, 0.75
                except:
                    default_onset, default_peak, default_duration, default_effect = 0.17, 1.0, 6.0, 0.75
                
                onset_time = st.slider("Onset Time (hours)", 0.1, 2.0, default_onset, 0.1, key="stim_onset")
                peak_time = st.slider("Peak Time (hours)", 0.5, 3.0, default_peak, 0.1, key="stim_peak")
                duration = st.slider("Duration (hours)", 2.0, 12.0, default_duration, 0.5, key="stim_duration")
                peak_effect = st.slider("Peak Effect", 0.1, 2.0, default_effect, 0.1, key="stim_effect")
                
                # Show what values are being overridden
                st.info(f"**Current JSON values**: Onset {format_duration_hours_minutes(default_onset)}, Peak {format_duration_hours_minutes(default_peak)}, Duration {format_duration_hours_minutes(default_duration)}, Effect {default_effect:.2f}")
                st.info(f"**Override values**: Onset {format_duration_hours_minutes(onset_time)}, Peak {format_duration_hours_minutes(peak_time)}, Duration {format_duration_hours_minutes(duration)}, Effect {peak_effect:.2f}")
            
            if st.button("➕ Add Stimulant", type="primary", key="add_stim"):
                time_str = stim_time.strftime("%H:%M")
                
                # Use stimulant with custom parameters as override
                custom_params = {
                    'onset_time': onset_time,
                    'peak_time': peak_time,
                    'duration': duration,
                    'peak_effect': peak_effect
                }
                st.session_state.simulator.add_stimulant(
                    time_str, stimulant_name, component_name, quantity, custom_params
                )
                st.success(f"Added {quantity}x {stimulant_name} at {time_str}")
                
                st.rerun()
        
        # Profile management
        st.header("👤 Profile Management")
        
        if profiles:
            profile_names = [p.get('name', 'Unnamed Profile') for p in profiles]
            selected_profile = st.selectbox("Load Profile", profile_names, key="profile_select")
            
            if st.button("📥 Load Profile", key="load_profile"):
                selected_profile_data = next(p for p in profiles if p.get('name') == selected_profile)
                st.session_state.simulator.import_schedule(selected_profile_data)
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
                        st.rerun()
        else:
            st.info("No doses added yet. Add some medications or stimulants above!")
        
        # Clear all button
        if all_doses:
            if st.button("🗑️ Clear All Doses", type="secondary"):
                st.session_state.simulator.clear_all_doses()
                st.rerun()
        
        # Sleep threshold adjustment
        st.header("😴 Sleep Settings")
        sleep_threshold = st.slider(
            "Sleep Threshold (effect level below which sleep is suitable)",
            0.1, 1.0, st.session_state.simulator.sleep_threshold, 0.05
        )
        if sleep_threshold != st.session_state.simulator.sleep_threshold:
            st.session_state.simulator.sleep_threshold = sleep_threshold
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Generate timeline with caching
        @st.cache_data(show_spinner=False)
        def generate_timeline():
            return st.session_state.simulator.generate_daily_timeline()
        
        time_points, combined_effect = generate_timeline()
        
        if len(time_points) > 0 and len(combined_effect) > 0:
            # Create enhanced plot with individual curves toggle
            st.subheader("📊 Daily Effect Timeline")
            
            # Toggle for showing individual curves
            show_individual_curves = st.checkbox("Show Individual Component Curves", value=False, key="show_curves")
            
            # Create figure
            fig = go.Figure()
            
            # Add individual curves if requested
            if show_individual_curves:
                individual_curves = st.session_state.simulator.get_individual_curves()
                for label, curve in individual_curves:
                    fig.add_trace(go.Scatter(
                        x=time_points,
                        y=curve,
                        mode='lines',
                        name=f"Component: {label}",
                        line=dict(color='lightgray', width=1, dash='dot'),
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
                )
            )
            
            # Update x-axis to show time labels
            fig.update_xaxes(
                tickmode='array',
                tickvals=list(range(0, 25, 2)),
                ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)]
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Sleep window analysis
            sleep_windows = st.session_state.simulator.find_sleep_windows(combined_effect)
            if sleep_windows:
                st.subheader("😴 Sleep Windows")
                sleep_info = []
                for start, end in sleep_windows:
                    duration = end - start
                    sleep_info.append({
                        "Start Time": format_time_hours_minutes(start),
                        "End Time": format_time_hours_minutes(end),
                        "Duration": format_duration_hours_minutes(duration)
                    })
                
                sleep_df = pd.DataFrame(sleep_info)
                st.dataframe(sleep_df, use_container_width=True)
            else:
                st.info("No suitable sleep windows found with current threshold.")
        
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

def painkillers_app():
    st.title("💊 Painkiller Timeline Simulator")
    st.markdown("Simulate and visualize painkiller effects throughout the day")
    
    # Sidebar for painkiller management
    with st.sidebar:
        st.header("📋 Painkiller Management")
        
        # Load available painkillers from unified database
        try:
            if st.session_state.medications_loaded:
                available_painkillers = list(medications_data['painkillers'].keys())
            else:
                available_painkillers = ['paracetamol_500mg', 'ibuprofen_400mg', 'panodil_665mg_mr']
        except:
            available_painkillers = ['paracetamol_500mg', 'ibuprofen_400mg', 'panodil_665mg_mr']
        
        st.subheader("Add New Painkiller")
        
        col1, col2 = st.columns(2)
        with col1:
            dose_time = st.time_input("Dose Time", value=time(8, 0), key="pk_time")
            painkiller_name = st.selectbox("Painkiller Type", available_painkillers, key="pk_name")
        with col2:
            dosage = st.number_input("Dosage (mg)", min_value=100.0, max_value=1000.0, value=500.0, step=50.0, key="pk_dosage")
        
        # Show painkiller info
        try:
            if st.session_state.medications_loaded:
                pk_info = medications_data['painkillers'][painkiller_name]
                
                onset_hours = pk_info['onset_min'] / 60.0
                peak_time_hours = pk_info['peak_time_min'] / 60.0
                peak_duration_hours = pk_info['peak_duration_min'] / 60.0
                duration_hours = pk_info['duration_min'] / 60.0
                
                st.info(f"**{painkiller_name}**: Onset {format_time_hours_minutes(onset_hours)}, Peak at {format_time_hours_minutes(peak_time_hours)}, Duration {format_duration_hours_minutes(duration_hours)}")
        except:
            st.warning("Could not load painkiller information")
        
        if st.button("➕ Add Painkiller", type="primary", key="add_pk"):
            time_str = dose_time.strftime("%H:%M")
            
            # For now, we'll add painkillers as medications with custom parameters
            # In a full implementation, you'd want a separate painkiller class
            st.info("Painkiller functionality coming soon!")
    
    # Main content area for painkillers
    st.info("Painkiller simulation functionality is under development. Please use the ADHD Medications tab for now.")

if __name__ == "__main__":
    main()
