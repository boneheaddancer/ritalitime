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
            
            # Load available prescription medications
            try:
                with open('meds_stimulants.json', 'r') as f:
                    med_data = json.load(f)
                available_medications = list(med_data['prescription_stimulants'].keys())
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
                    with open('meds_stimulants.json', 'r') as f:
                        med_data = json.load(f)
                    med_info = med_data['prescription_stimulants'][medication_name]
                    
                    # Convert minutes to hours for display
                    onset_hours = med_info['onset_min'] / 60.0
                    peak_time_hours = med_info['peak_time_min'] / 60.0
                    peak_duration_hours = med_info['peak_duration_min'] / 60.0
                    duration_hours = med_info['duration_min'] / 60.0
                    wear_off_hours = med_info['wear_off_duration_min'] / 60.0
                    
                    st.info(f"**{medication_name}**: Onset {format_time_hours_minutes(onset_hours)}, Peak at {format_time_hours_minutes(peak_time_hours)}, Peak duration {format_duration_hours_minutes(peak_duration_hours)}, Total {format_duration_hours_minutes(duration_hours)}")
                except:
                    st.warning("Could not load medication information")
            
            # Advanced parameters (to override prescription defaults)
            with st.expander("Advanced Parameters (Override Defaults)"):
                # Get current values from JSON for prescription medication
                try:
                    with open('meds_stimulants.json', 'r') as f:
                        med_data = json.load(f)
                    med_info = med_data['prescription_stimulants'][medication_name]
                    
                    # Convert minutes to hours for default values
                    default_onset = med_info['onset_min'] / 60.0
                    default_peak = med_info['peak_time_min'] / 60.0
                    default_duration = med_info['duration_min'] / 60.0
                    default_effect = med_info['peak_duration_min'] / 60.0
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
            
            # Load available stimulants
            try:
                with open('meds_stimulants.json', 'r') as f:
                    stim_data = json.load(f)
                available_stimulants = list(stim_data['common_stimulants'].keys())
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
                    with open('meds_stimulants.json', 'r') as f:
                        stim_data = json.load(f)
                    
                    if stimulant_name in ['redbull', 'monster'] and component_name:
                        stim_info = stim_data['common_stimulants'][stimulant_name][component_name]
                    else:
                        stim_info = stim_data['common_stimulants'][stimulant_name]
                    
                    # Convert minutes to hours for default values
                    default_onset = stim_info['onset_min'] / 60.0
                    default_peak = stim_info['peak_time_min'] / 60.0
                    default_duration = stim_info['duration_min'] / 60.0
                    default_effect = stim_info['peak_duration_min'] / 60.0
                except:
                    default_onset, default_peak, default_duration, default_effect = 0.17, 1.0, 6.0, 0.75
                
                stim_onset = st.slider("Onset Time (hours)", 0.1, 1.0, default_onset, 0.05, key="stim_onset")
                stim_peak = st.slider("Peak Time (hours)", 0.5, 2.0, default_peak, 0.1, key="stim_peak")
                stim_duration = st.slider("Duration (hours)", 2.0, 10.0, default_duration, 0.5, key="stim_duration")
                stim_effect = st.slider("Peak Effect", 0.1, 2.0, default_effect, 0.1, key="stim_effect")
                
                # Show what values are being overridden
                st.info(f"**Current JSON values**: Onset {format_duration_hours_minutes(default_onset)}, Peak {format_duration_hours_minutes(default_peak)}, Duration {format_duration_hours_minutes(default_duration)}, Effect {default_effect:.2f}")
                st.info(f"**Override values**: Onset {format_duration_hours_minutes(stim_onset)}, Peak {format_duration_hours_minutes(stim_peak)}, Duration {format_duration_hours_minutes(stim_duration)}, Effect {stim_effect:.2f}")
            
            if st.button("➕ Add Stimulant", type="primary", key="add_stim"):
                time_str = stim_time.strftime("%H:%M")
                try:
                    # Use custom parameters if they differ from defaults
                    custom_params = None
                    if (abs(stim_onset - default_onset) > 0.01 or 
                        abs(stim_peak - default_peak) > 0.01 or 
                        abs(stim_duration - default_duration) > 0.01 or 
                        abs(stim_effect - default_effect) > 0.01):
                        custom_params = {
                            'onset_time': stim_onset,
                            'peak_time': stim_peak,
                            'duration': stim_duration,
                            'peak_effect': stim_effect
                        }
                    
                    st.session_state.simulator.add_stimulant(
                        time_str, stimulant_name, component_name, quantity, custom_params
                    )
                    stim_label = f"{quantity}x {stimulant_name}"
                    if component_name:
                        stim_label += f" ({component_name})"
                    st.success(f"Added {stim_label} at {time_str}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding stimulant: {e}")
        
        st.divider()
        
        # Current doses
        st.subheader("Current Doses")
        all_doses = st.session_state.simulator.get_all_doses()
        
        if not all_doses:
            st.info("No doses added yet")
        else:
            for dose in all_doses:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    if dose['type'] == 'medication':
                        if dose.get('medication_name'):
                            st.write(f"**💊 {dose['dosage']}mg {dose['medication_name']}** at {format_time_hours_minutes(dose['time'])}")
                        else:
                            st.write(f"**💊 {dose['dosage']}mg** at {format_time_hours_minutes(dose['time'])}")
                    else:
                        stim_label = f"☕ {dose['quantity']}x {dose['stimulant_name']}"
                        if dose['component_name']:
                            stim_label += f" ({dose['component_name']})"
                        st.write(f"**{stim_label}** at {format_time_hours_minutes(dose['time'])}")
                
                with col2:
                    if dose['type'] == 'medication':
                        st.write(f"Duration: {format_duration_hours_minutes(dose['duration'])}")
                    else:
                        st.write(f"Effect: {dose['peak_effect']:.2f}")
                
                with col3:
                    if st.button("🗑️", key=f"del_{dose['id']}"):
                        st.session_state.simulator.remove_dose(dose['id'])
                        st.rerun()
                
                # Show curve details in expandable section
                with st.expander(f"Curve details for {dose.get('dosage', dose.get('stimulant_name', 'dose'))}"):
                    if dose['type'] == 'medication':
                        st.write(f"**Onset**: {format_duration_hours_minutes(dose['onset_time'])} → **Peak**: {format_duration_hours_minutes(dose['peak_time'])} → **Duration**: {format_duration_hours_minutes(dose['duration'])}")
                    else:
                        st.write(f"**Onset**: {format_duration_hours_minutes(dose['onset_time'])} → **Peak**: {format_duration_hours_minutes(dose['peak_time'])} → **Duration**: {format_duration_hours_minutes(dose['duration'])}")
                    
                    # Calculate actual curve phases based on new implementation
                    onset_time = dose['onset_time']      # Time from dose to onset
                    peak_time = dose['peak_time']        # Time from dose to peak effect
                    duration = dose['duration']          # Total duration
                    
                    # Use new parameters if available
                    if 'peak_duration' in dose:
                        peak_duration = dose['peak_duration']
                        fall_start = onset_time + peak_duration
                    else:
                        # Fallback to old calculation
                        min_fall_duration = 1.0
                        fall_start = max(peak_time, duration - min_fall_duration)
                    
                    # Calculate phase durations
                    rise_duration = onset_time
                    plateau_duration = fall_start - onset_time
                    fall_duration = duration - fall_start
                    
                    st.write(f"**Rise Phase**: 0h → {format_duration_hours_minutes(onset_time)} ({format_duration_hours_minutes(rise_duration)})")
                    st.write(f"**Plateau Phase**: {format_duration_hours_minutes(onset_time)} → {format_duration_hours_minutes(fall_start)} ({format_duration_hours_minutes(plateau_duration)})")
                    st.write(f"**Fall Phase**: {format_duration_hours_minutes(fall_start)} → {format_duration_hours_minutes(duration)} ({format_duration_hours_minutes(fall_duration)})")
                    
                    # Show additional timing info if available
                    if 'peak_duration' in dose and 'wear_off_duration' in dose:
                        st.write(f"**Peak Duration**: {format_duration_hours_minutes(dose['peak_duration'])}")
                        st.write(f"**Wear-off Duration**: {format_duration_hours_minutes(dose['wear_off_duration'])}")
                    
                    # Show timing relative to dose time
                    dose_time_str = format_time_hours_minutes(dose['time'])
                    onset_time_str = format_time_hours_minutes(dose['time'] + onset_time)
                    peak_time_str = format_time_hours_minutes(dose['time'] + peak_time)
                    end_time_str = format_time_hours_minutes(dose['time'] + duration)
                    
                    st.write(f"**Timeline**: Dose at {dose_time_str} → Onset at {onset_time_str} → Peak at {peak_time_str} → Ends at {end_time_str}")
        
        if all_doses and st.button("🗑️ Clear All"):
            st.session_state.simulator.clear_all_doses()
            st.rerun()
        
        st.divider()
        
        # Sleep threshold
        st.subheader("Sleep Settings")
        sleep_threshold = st.slider(
            "Sleep Threshold", 
            0.05, 2.0,  # More granular range starting from 0.05
            st.session_state.simulator.sleep_threshold, 
            0.01,  # Much more granular step size
            help="Effect level below which sleep is suitable (0.01 = very sensitive, 2.0 = very tolerant)"
        )
        st.session_state.simulator.sleep_threshold = sleep_threshold
        
        # Show current threshold value with interpretation
        if sleep_threshold < 0.2:
            threshold_desc = "Very sensitive to effects"
        elif sleep_threshold < 0.5:
            threshold_desc = "Moderately sensitive to effects"
        elif sleep_threshold < 1.0:
            threshold_desc = "Tolerant to moderate effects"
        else:
            threshold_desc = "Very tolerant to effects"
        
        st.info(f"**Current Threshold**: {sleep_threshold:.2f} - {threshold_desc}")
        
        # Sleep preferences
        st.markdown("**😴 Sleep Preferences:**")
        
        # Initialize sleep preferences in session state if not present
        if 'sleep_time' not in st.session_state:
            st.session_state.sleep_time = time(22, 0)  # Default 22:00
        if 'sleep_duration' not in st.session_state:
            st.session_state.sleep_duration = 7.5  # Default 7h30m
        
        # Use the session state values directly for the widgets
        preferred_sleep_time = st.time_input("Preferred Sleep Time", value=st.session_state.sleep_time, key="sleep_time_input")
        preferred_sleep_duration = st.number_input("Sleep Duration (hours)", min_value=6.0, max_value=12.0, value=st.session_state.sleep_duration, step=0.5, key="sleep_duration_input")
        
        # Update session state when widgets change
        if preferred_sleep_time != st.session_state.sleep_time:
            st.session_state.sleep_time = preferred_sleep_time
        if preferred_sleep_duration != st.session_state.sleep_duration:
            st.session_state.sleep_duration = preferred_sleep_duration
        
        # Handle pending sleep preferences from profile loading
        if hasattr(st.session_state, 'pending_sleep_time'):
            st.session_state.sleep_time = st.session_state.pending_sleep_time
            del st.session_state.pending_sleep_time
        if hasattr(st.session_state, 'pending_sleep_duration'):
            st.session_state.sleep_duration = st.session_state.pending_sleep_duration
            del st.session_state.pending_sleep_duration
        
        # Show sleep window with formatted duration
        sleep_start = datetime.combine(datetime.today().date(), preferred_sleep_time)
        sleep_end = sleep_start + timedelta(hours=preferred_sleep_duration)
        if sleep_end.time() < sleep_start.time():  # Wraps to next day
            sleep_end = sleep_end + timedelta(days=1)
        duration_formatted = format_duration_hours_minutes(preferred_sleep_duration)
        st.info(f"**Sleep Window**: {sleep_start.strftime('%H:%M')} - {sleep_end.strftime('%H:%M')} ({duration_formatted})")
        

        
        # Effect scale info
        if len(all_doses) > 1:
            st.info(f"📏 **Effect Scale**: Hill saturation prevents unlimited additive effects - multiple doses saturate near {st.session_state.simulator.emax:.1f}")
        
        # Export/Import
        st.divider()
        st.subheader("Data Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Export"):
                filename = st.session_state.simulator.export_schedule()
                with open(filename, 'r') as f:
                    json_data = f.read()
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=filename,
                    mime="application/json"
                )
        
        with col2:
            uploaded_file = st.file_uploader("📥 Import", type=['json'])
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read()
                    data = json.loads(content)
                    st.session_state.simulator.import_schedule(data)
                    st.success("Schedule imported successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error importing file: {e}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Generate timeline
        time_points, effect_level = st.session_state.simulator.generate_daily_timeline()
        
        # Create interactive plot
        fig = create_timeline_plot(time_points, effect_level, all_doses)
        st.plotly_chart(fig, use_container_width=True)
        
        # Sleep windows
        sleep_windows = st.session_state.simulator.find_sleep_windows(effect_level)
        if sleep_windows:
            st.subheader("😴 Sleep Windows")
            for start, end in sleep_windows:
                start_str = format_time_hours_minutes(start)
                end_str = format_time_hours_minutes(end)
                st.info(f"**{start_str}** to **{end_str}** (Duration: {format_duration_hours_minutes(end-start)})")
        else:
            st.warning("⚠️ No suitable sleep windows found with current threshold")
    
    with col2:
        # Statistics and insights
        st.subheader("📊 Daily Statistics")
        
        if effect_level.max() > 0:
            max_effect_time = time_points[np.argmax(effect_level)]
            max_effect_str = format_time_hours_minutes(max_effect_time)
            
            st.metric("Peak Effect Time", max_effect_str)
            st.metric("Peak Effect Level", f"{effect_level.max():.2f}")
            st.metric("Average Effect", f"{effect_level.mean():.2f}")
            
            # Show additive effect indicator
            if effect_level.max() > 1.0:
                st.success(f"🚀 **Additive Effects Detected!** Multiple doses are overlapping to create enhanced effects (max: {effect_level.max():.2f})")
            elif len(all_doses) > 1:
                st.info(f"📊 **Multiple Doses**: {len(all_doses)} doses with combined peak effect of {effect_level.max():.2f}")
            
            # Effect summary metrics
            st.subheader("📊 Effect Summary")
            
            # Calculate useful metrics
            above_sleep_threshold = effect_level > st.session_state.simulator.sleep_threshold
            effective_hours = np.sum(above_sleep_threshold) * 0.1  # 0.1 hour intervals
            
            # Time spent at different effect levels
            peak_effect_threshold = effect_level.max() * 0.8  # 80% of peak
            peak_duration = np.sum(effect_level >= peak_effect_threshold) * 0.1
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Effective Hours", f"{effective_hours:.1f}h")
                st.metric("Peak Duration", f"{peak_duration:.1f}h")
            
            with col2:
                st.metric("Sleep Hours", f"{24-effective_hours:.1f}h")
                st.metric("Below Threshold", f"{np.sum(effect_level < 0.1) * 0.1:.1f}h")
        else:
            st.info("Add doses to see statistics")
        
        # Quick profiles
        st.subheader("⚡ Quick Profiles")
        
        # Save current schedule as quick profile
        if all_doses:
            if st.button("💾 Save Current as Quick Profile", type="primary"):
                st.session_state.show_save_input = True
            
            if st.session_state.get('show_save_input', False):
                profile_name = st.text_input("Profile Name:", value="My Schedule", key="profile_name_input")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Confirm Save", key="confirm_save"):
                        if profile_name.strip():
                            # Save to session state
                            if 'saved_profiles' not in st.session_state:
                                st.session_state.saved_profiles = {}
                            st.session_state.saved_profiles[profile_name] = {
                                'medications': st.session_state.simulator.medications.copy(),
                                'stimulants': st.session_state.simulator.stimulants.copy(),
                                'sleep_threshold': st.session_state.simulator.sleep_threshold,
                                'preferred_sleep_time': preferred_sleep_time.hour + preferred_sleep_time.minute / 60.0,
                                'preferred_sleep_duration': preferred_sleep_duration
                            }
                            st.session_state.show_save_input = False
                            st.success(f"Profile '{profile_name}' saved!")
                            st.rerun()
                        else:
                            st.error("Please enter a profile name")
                with col2:
                    if st.button("Cancel", key="cancel_save"):
                        st.session_state.show_save_input = False
                        st.rerun()
        else:
            st.info("Add doses to save as a quick profile")
        
        # Preset profiles with detailed information
        st.write("**Preset Profiles:**")
        
        # Load preset profiles from JSON file
        try:
            with open('profiles.json', 'r') as f:
                profiles_data = json.load(f)
            preset_profiles = profiles_data.get('preset_profiles', {})
        except Exception as e:
            st.error(f"Could not load profiles: {e}")
            preset_profiles = {}
        
        # Display preset profiles in a grid
        if preset_profiles:
            # Create a grid layout for preset profiles
            profile_keys = list(preset_profiles.keys())
            for i in range(0, len(profile_keys), 2):
                col1, col2 = st.columns(2)
                
                # Left column
                with col1:
                    profile_key = profile_keys[i]
                    profile = preset_profiles[profile_key]
                    st.markdown(f"**{profile['name']}**")
                    st.markdown(f"*{profile['description']}*")
                    
                    # Show medication details
                    if profile['medications']:
                        for med in profile['medications']:
                            st.markdown(f"• **{med['time']}** - {med['dosage']}mg {med['medication_name']} ({format_duration_hours_minutes(med['duration'])} duration)")
                    
                    # Show stimulant details
                    if profile['stimulants']:
                        for stim in profile['stimulants']:
                            st.markdown(f"• **{stim['time']}** - {stim['quantity']}x {stim['stimulant_name']} ({format_duration_hours_minutes(stim['duration'])} duration)")
                    
                    if st.button(f"Load {profile['name']}", key=f"load_{profile_key}"):
                        st.session_state.simulator.clear_all_doses()
                        
                        # Load medications
                        for med in profile['medications']:
                            st.session_state.simulator.add_medication(
                                med['time'], 
                                med['dosage'], 
                                med['onset_time'], 
                                med['peak_time'], 
                                med['duration']
                            )
                        
                        # Load stimulants
                        for stim in profile['stimulants']:
                            st.session_state.simulator.add_stimulant(
                                stim['time'],
                                stim['stimulant_name'],
                                stim.get('component_name'),
                                stim['quantity']
                            )
                        
                        # Load sleep preferences
                        if 'preferred_sleep_time' in profile:
                            sleep_hours = int(profile['preferred_sleep_time'])
                            sleep_minutes = int((profile['preferred_sleep_time'] % 1) * 60)
                            st.session_state.pending_sleep_time = time(sleep_hours, sleep_minutes)
                        if 'preferred_sleep_duration' in profile:
                            st.session_state.pending_sleep_duration = profile['preferred_sleep_duration']
                        
                        st.rerun()
                
                # Right column (if there's a second profile)
                with col2:
                    if i + 1 < len(profile_keys):
                        profile_key = profile_keys[i + 1]
                        profile = preset_profiles[profile_key]
                        st.markdown(f"**{profile['name']}**")
                        st.markdown(f"*{profile['description']}*")
                        
                        # Show medication details
                        if profile['medications']:
                            for med in profile['medications']:
                                st.markdown(f"• **{med['time']}** - {med['dosage']}mg {med['medication_name']} ({format_duration_hours_minutes(med['duration'])} duration)")
                        
                        # Show stimulant details
                        if profile['stimulants']:
                            for stim in profile['stimulants']:
                                st.markdown(f"• **{stim['time']}** - {stim['quantity']}x {stim['stimulant_name']} ({format_duration_hours_minutes(stim['duration'])} duration)")
                        
                        if st.button(f"Load {profile['name']}", key=f"load_{profile_key}"):
                            st.session_state.simulator.clear_all_doses()
                            
                            # Load medications
                            for med in profile['medications']:
                                st.session_state.simulator.add_medication(
                                    med['time'], 
                                    med['dosage'], 
                                    med['onset_time'], 
                                    med['peak_time'], 
                                    med['duration']
                                )
                            
                            # Load stimulants
                            for stim in profile['stimulants']:
                                st.session_state.simulator.add_stimulant(
                                    stim['time'],
                                    stim['stimulant_name'],
                                    stim.get('component_name'),
                                    stim['quantity']
                                )
                            
                            # Load sleep preferences
                            if 'preferred_sleep_time' in profile:
                                sleep_hours = int(profile['preferred_sleep_time'])
                                sleep_minutes = int((profile['preferred_sleep_time'] % 1) * 60)
                                st.session_state.pending_sleep_time = time(sleep_hours, sleep_minutes)
                            if 'preferred_sleep_duration' in profile:
                                st.session_state.pending_sleep_duration = profile['preferred_sleep_duration']
                            
                            st.rerun()
        else:
            st.info("No preset profiles found. Check profiles.json file.")
        
        # Load saved profiles if any exist
        if 'saved_profiles' in st.session_state and st.session_state.saved_profiles:
            st.markdown("---")
            st.markdown("**💾 Saved Profiles:**")
            for profile_name, profile_data in st.session_state.saved_profiles.items():
                st.markdown(f"**{profile_name}**")
                med_count = len(profile_data['medications'])
                stim_count = len(profile_data['stimulants'])
                st.markdown(f"• {med_count} medications, {stim_count} stimulants  \n• Sleep threshold: {profile_data['sleep_threshold']:.2f}")
                if 'preferred_sleep_time' in profile_data and 'preferred_sleep_duration' in profile_data:
                    sleep_time_str = format_time_hours_minutes(profile_data['preferred_sleep_time'])
                    sleep_duration_str = format_duration_hours_minutes(profile_data['preferred_sleep_duration'])
                    st.markdown(f"• Preferred Sleep: {sleep_time_str} - {sleep_duration_str}")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(f"Load {profile_name}", key=f"load_{profile_name}"):
                        st.session_state.simulator.medications = profile_data['medications'].copy()
                        st.session_state.simulator.stimulants = profile_data['stimulants'].copy()
                        st.session_state.simulator.sleep_threshold = profile_data['sleep_threshold']
                        # Load sleep preferences if available
                        if 'preferred_sleep_time' in profile_data:
                            sleep_hours = int(profile_data['preferred_sleep_time'])
                            sleep_minutes = int((profile_data['preferred_sleep_time'] % 1) * 60)
                            st.session_state.pending_sleep_time = time(sleep_hours, sleep_minutes)
                        if 'preferred_sleep_duration' in profile_data:
                            st.session_state.pending_sleep_duration = profile_data['preferred_sleep_duration']
                        st.rerun()
                with col2:
                    if st.button(f"Delete", key=f"delete_{profile_name}"):
                        del st.session_state.saved_profiles[profile_name]
                        st.rerun()
                st.markdown("---")

def create_timeline_plot(time_points, effect_level, all_doses):
    """Create the main timeline visualization with enhanced features"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Combined Effect Timeline", "Individual Doses"),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3]
    )
    
    # Main effect curve (bold)
    fig.add_trace(
        go.Scatter(
            x=time_points,
            y=effect_level,
            mode='lines',
            name='Combined Effect',
            line=dict(color='#1f77b4', width=4),
            fill='tonexty',
            fillcolor='rgba(31, 119, 180, 0.2)'
        ),
        row=1, col=1
    )
    
    # Sleep threshold line
    fig.add_hline(
        y=st.session_state.simulator.sleep_threshold,
        line_dash="dash",
        line_color="red",
        annotation_text="Sleep Threshold",
        row=1, col=1
    )
    
    # Saturation threshold line
    fig.add_hline(
        y=st.session_state.simulator.saturation_threshold,
        line_dash="dot",
        line_color="purple",
        annotation_text="Saturation Threshold",
        row=1, col=1
    )
    
    # Preferred sleep time visualization
    if 'sleep_time' in st.session_state and 'sleep_duration' in st.session_state:
        sleep_time = st.session_state.sleep_time
        sleep_duration = st.session_state.sleep_duration
        
        # Convert time to decimal hours
        sleep_start_hours = sleep_time.hour + sleep_time.minute / 60.0
        sleep_end_hours = sleep_start_hours + sleep_duration
        
        # Handle midnight wrap-around
        if sleep_end_hours > 24:
            # Sleep window wraps to next day
            # First part (same day)
            fig.add_vrect(
                x0=sleep_start_hours, x1=24,
                fillcolor="rgba(0, 0, 255, 0.1)",
                layer="below",
                line_width=0
            )
            # Second part (next day)
            fig.add_vrect(
                x0=0, x1=sleep_end_hours - 24,
                fillcolor="rgba(0, 0, 255, 0.1)",
                layer="below",
                line_width=0,
                annotation_text="Preferred Sleep",
                annotation_position="top right"
            )
        else:
            # Sleep window within same day
            fig.add_vrect(
                x0=sleep_start_hours, x1=sleep_end_hours,
                fillcolor="rgba(0, 0, 255, 0.1)",
                layer="below",
                line_width=0,
                annotation_text="Preferred Sleep",
                annotation_position="top right"
            )
        
        # Add vertical line for preferred sleep start time
        fig.add_vline(
            x=sleep_start_hours,
            line_width=2,
            line_color="blue",
            line_dash="dash",
            annotation_text="Sleep Time",
            row=1, col=1
        )
    
    # Individual dose curves with enhanced styling
    individual_curves = st.session_state.simulator.get_individual_curves()
    for label, individual_effect in individual_curves:
        # Different colors for different types
        if 'mg' in label:  # Medication
            line_color = '#ff7f0e'  # Orange
            line_style = 'solid'
        else:  # Stimulant
            line_color = '#2ca02c'  # Green
            line_style = 'dash'
        
        fig.add_trace(
            go.Scatter(
                x=time_points,
                y=individual_effect,
                mode='lines',
                name=label,
                line=dict(color=line_color, width=2, dash=line_style),
                opacity=0.7
            ),
            row=2, col=1
        )
    
    # Enhanced dose markers with peak windows and wear-off shading
    # First, collect all dose times to detect overlaps
    dose_times = [dose['time'] for dose in all_doses]
    time_groups = {}
    
    # Group doses by time (with small tolerance for "same time")
    tolerance = 0.1  # 6 minutes tolerance
    for i, dose in enumerate(all_doses):
        dose_time = dose['time']
        grouped = False
        
        for group_time in time_groups:
            if abs(dose_time - group_time) <= tolerance:
                time_groups[group_time].append(i)
                grouped = True
                break
        
        if not grouped:
            time_groups[dose_time] = [i]
    
    # Now add dose markers with intelligent positioning to prevent overlaps
    for dose_time, dose_indices in time_groups.items():
        for i, dose_idx in enumerate(dose_indices):
            dose = all_doses[dose_idx]
            
            if dose['type'] == 'medication':
                marker_color = "orange"
                marker_text = f"{dose['dosage']}mg"
            else:
                marker_color = "green"
                marker_text = f"{dose['stimulant_name']}"
                if dose.get('component_name'):
                    marker_text += f" ({dose['component_name']})"
            
            # Intelligent annotation positioning to prevent overlaps
            if len(dose_indices) > 1:
                # Multiple doses at same time - use more sophisticated positioning
                if i == 0:
                    annotation_position = "top left"
                    yshift = 10
                elif i == 1:
                    annotation_position = "top right"
                    yshift = 10
                elif i == 2:
                    annotation_position = "bottom left"
                    yshift = -10
                elif i == 3:
                    annotation_position = "bottom right"
                    yshift = -10
                else:
                    # For more than 4 doses, alternate between top and bottom with increasing offsets
                    if i % 2 == 0:
                        annotation_position = "top left"
                        yshift = 10 + (i // 2) * 15
                    else:
                        annotation_position = "bottom right"
                        yshift = -10 - (i // 2) * 15
            else:
                # Single dose - use default position
                annotation_position = "top left"
                yshift = 10
            
            # Dose time marker with intelligent positioning
            fig.add_vline(
                x=dose['time'],
                line_width=3,
                line_color=marker_color,
                annotation_text=marker_text,
                annotation_position=annotation_position,
                annotation=dict(
                    yshift=yshift,
                    font=dict(size=10),
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor=marker_color,
                    borderwidth=1
                ),
                row=1, col=1
            )
            
            # Peak window shading (onset to fall start)
            onset_time = dose['onset_time']
            fall_start = onset_time + dose.get('peak_duration', 1.0)
            duration = dose['duration']
            
            # Calculate absolute times
            dose_time_abs = dose['time']
            peak_start = dose_time_abs + onset_time
            peak_end = dose_time_abs + fall_start
            wear_off_start = dose_time_abs + fall_start
            wear_off_end = dose_time_abs + duration
            
            # Peak window (shaded green - optimal effect) - positioned to avoid dose labels
            peak_annotation_position = "top left" if i % 2 == 0 else "top right"
            fig.add_vrect(
                x0=peak_start, x1=peak_end,
                fillcolor="rgba(0, 255, 0, 0.1)",
                layer="below",
                line_width=0,
                annotation_text="Peak Window",
                annotation_position=peak_annotation_position,
                annotation=dict(
                    yshift=20 + (i * 5),  # Stagger peak window labels
                    font=dict(size=9),
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor="green",
                    borderwidth=1
                )
            )
            
            # Wear-off interval (shaded red - fading effect) - positioned to avoid overlaps
            wear_off_annotation_position = "bottom left" if i % 2 == 0 else "bottom right"
            fig.update_xaxes(range=[0, 24])
            if wear_off_end <= 24:  # Same day
                fig.add_vrect(
                    x0=wear_off_start, x1=wear_off_end,
                    fillcolor="rgba(255, 0, 0, 0.1)",
                    layer="below",
                    line_width=0,
                    annotation_text="Wear-off",
                    annotation_position=wear_off_annotation_position,
                    annotation=dict(
                        yshift=-20 - (i * 5),  # Stagger wear-off labels
                        font=dict(size=9),
                        bgcolor="rgba(255, 255, 255, 0.9)",
                        bordercolor="red",
                        borderwidth=1
                    )
                )
            else:  # Wraps to next day
                # First part (same day)
                fig.add_vrect(
                    x0=wear_off_start, x1=24,
                    fillcolor="rgba(255, 0, 0, 0.1)",
                    layer="below",
                    line_width=0
                )
                # Second part (next day)
                fig.add_vrect(
                    x0=0, x1=wear_off_end - 24,
                    fillcolor="rgba(255, 0, 0, 0.1)",
                    layer="below",
                    line_width=0
                )
    
    # Update layout
    max_effect = max(1.1, effect_level.max() * 1.1) if len(effect_level) > 0 else 1.1
    max_effect = max(max_effect, st.session_state.simulator.emax * 1.1)
    
    # Create custom x-axis tick labels in HH:MM format
    tick_hours = list(range(0, 25, 3))  # Every 3 hours: 0, 3, 6, 9, 12, 15, 18, 21, 24
    tick_labels = [format_time_hours_minutes(hour) for hour in tick_hours]
    
    fig.update_xaxes(
        title_text="Time (24h)", 
        range=[0, 24], 
        tickmode='array',
        tickvals=tick_hours,
        ticktext=tick_labels,
        row=1, col=1
    )
    fig.update_yaxes(title_text="Effect Level", range=[0, max_effect], row=1, col=1)
    
    fig.update_xaxes(
        title_text="Time (24h)", 
        range=[0, 24], 
        tickmode='array',
        tickvals=tick_hours,
        ticktext=tick_labels,
        row=2, col=1
    )
    fig.update_yaxes(title_text="Individual Effects", row=2, col=1)
    
    # Update hover template to show time in HH:MM format
    # Create custom hover template that converts decimal hours to HH:MM
    for trace in fig.data:
        if trace.x is not None and len(trace.x) > 0:
            # Convert x values (decimal hours) to HH:MM format for hover
            hover_x = [format_time_hours_minutes(x) for x in trace.x]
            trace.customdata = hover_x
            trace.hovertemplate = (
                "<b>%{fullData.name}</b><br>" +
                "Time: %{customdata}<br>" +
                "Effect: %{y:.2f}<br>" +
                "<extra></extra>"
            )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="24-Hour Effect Timeline",
        hovermode='x unified'
    )
    
    return fig

def painkillers_app():
    st.title("💊 Painkiller Timeline Simulator")
    st.markdown("Simulate and visualize painkiller effects throughout the day")
    
    # Clinical evidence explanation
    with st.expander("📚 Clinical Evidence & Relief Thresholds"):
        st.markdown("""
        **Pain Relief Thresholds Based on Clinical Research:**
        
        - **🟠 Moderate Relief (3/10)**: 30% pain reduction - clinically meaningful improvement
        - **🟢 Strong Relief (6/10)**: 60% pain reduction - substantial pain control
        - **🔵 Complete Relief (8/10)**: 80% pain reduction - near-complete pain elimination
        
        **Pharmacokinetic Parameters:**
        - **Onset**: Time from dose to first measurable effect
        - **Tmax**: Time from dose to maximum effect (peak concentration)
        - **Plateau Duration**: How long the therapeutic effect is maintained at maximum level
        - **Total Duration**: Complete duration of therapeutic effect
        
        **Multiple Pills Effect:**
        - **Modified-Release (MR)**: Multiple pills primarily extend duration (30% per pill) with moderate peak increase (20% per pill)
        - **Immediate-Release**: Multiple pills increase peak intensity (40% per pill) with slight duration extension (10% per pill)
        
        **Fixed Dosage Per Pill:**
        - Each pill contains a standardized amount of active ingredient
        - Dosage cannot be adjusted manually - only pill count can be changed
        - This ensures consistent, predictable dosing and prevents medication errors
        
        **Evidence Base:**
        - Pain reduction ≥30% is considered clinically meaningful in clinical trials
        - 60% reduction represents "good" pain control according to WHO guidelines
        - 80% reduction indicates "excellent" pain management outcomes
        
        **Note**: Individual response varies. These thresholds are based on population studies.
        """)
    
    # Initialize session state for painkillers
    if 'painkiller_doses' not in st.session_state:
        st.session_state.painkiller_doses = []
    
    # Sidebar for painkiller management
    with st.sidebar:
        st.header("📋 Painkiller Management")
        
        st.subheader("Add New Painkiller")
        st.caption("💊 Dosage is automatically calculated based on product and pill count")
        
        # Load available painkillers from JSON
        try:
            with open('painkillers.json', 'r') as f:
                painkiller_data = json.load(f)
            available_painkillers = list(painkiller_data.keys())
        except:
            available_painkillers = ['paracetamol_500mg', 'ibuprofen_400mg', 'panodil_665mg_mr']
        
        col1, col2 = st.columns(2)
        with col1:
            dose_time = st.time_input("Dose Time", value=time(8, 0), key="painkiller_time")
            painkiller_name = st.selectbox("Painkiller Type", available_painkillers, key="painkiller_name")
        with col2:
            pill_count = st.number_input("Pills", min_value=1, max_value=4, value=1, step=1, key="painkiller_pills")
            
            # Auto-calculate and display dosage based on product and pill count
            if painkiller_name in available_painkillers:
                try:
                    with open('painkillers.json', 'r') as f:
                        painkiller_data = json.load(f)
                    base_dosage = 0
                    if painkiller_name == "paracetamol_500mg":
                        base_dosage = 500
                    elif painkiller_name == "ibuprofen_400mg":
                        base_dosage = 400
                    elif painkiller_name == "panodil_665mg_mr":
                        base_dosage = 665
                    
                    if base_dosage > 0:
                        total_dosage = base_dosage * pill_count
                        st.metric("Total Dosage", f"{total_dosage}mg")
                        
                        # Show per-pill dosage for clarity
                        if pill_count > 1:
                            st.caption(f"({base_dosage}mg per pill)")
                        
                        # Show typical dosing information
                        if painkiller_name == "panodil_665mg_mr":
                            st.info("💡 **Typical dose**: 2 pills (1330mg) every 6-8 hours")
                        elif painkiller_name == "paracetamol_500mg":
                            st.info("💡 **Typical dose**: 1-2 pills (500-1000mg) every 4-6 hours")
                        elif painkiller_name == "ibuprofen_400mg":
                            st.info("💡 **Typical dose**: 1-2 pills (400-800mg) every 6-8 hours")
                except:
                    pass
        
        # Show painkiller info if available
        if painkiller_name in available_painkillers:
            try:
                with open('painkillers.json', 'r') as f:
                    painkiller_data = json.load(f)
                pk_info = painkiller_data[painkiller_name]
                
                # Convert minutes to hours for display
                onset_hours = pk_info['onset_min'] / 60.0
                peak_time_hours = pk_info['time_until_peak_min'] / 60.0
                peak_duration_hours = pk_info['peak_duration_min'] / 60.0
                duration_hours = pk_info['duration_min'] / 60.0
                wear_off_hours = pk_info['wear_off_duration_min'] / 60.0
                
                st.info(f"**{painkiller_name}**: Onset {format_time_hours_minutes(onset_hours)}, Peak at {format_time_hours_minutes(peak_time_hours)}, Peak duration {format_duration_hours_minutes(peak_duration_hours)}, Total {format_duration_hours_minutes(duration_hours)}")
            except:
                st.warning("Could not load painkiller information")
        
        if st.button("➕ Add Painkiller", type="primary", key="add_painkiller"):
            time_str = dose_time.strftime("%H:%M")
            
            # Calculate actual dosage based on pill count
            base_dosage = 0
            if painkiller_name == "paracetamol_500mg":
                base_dosage = 500
            elif painkiller_name == "ibuprofen_400mg":
                base_dosage = 400
            elif painkiller_name == "panodil_665mg_mr":
                base_dosage = 665
            
            actual_dosage = base_dosage * pill_count
            
            # Create painkiller dose entry
            dose_entry = {
                'id': len(st.session_state.painkiller_doses),
                'time': dose_time.hour + dose_time.minute / 60.0,
                'time_str': time_str,
                'name': painkiller_name,
                'pills': pill_count,
                'dosage': actual_dosage,
                'onset_min': painkiller_data[painkiller_name]['onset_min'],
                'peak_time_min': painkiller_data[painkiller_name]['time_until_peak_min'],
                'peak_duration_min': painkiller_data[painkiller_name]['peak_duration_min'],
                'duration_min': painkiller_data[painkiller_name]['duration_min'],
                'wear_off_duration_min': painkiller_data[painkiller_name]['wear_off_duration_min'],
                'intensity_peak': painkiller_data[painkiller_name]['intensity_peak'],
                'intensity_avg': painkiller_data[painkiller_name]['intensity_avg']
            }
            
            st.session_state.painkiller_doses.append(dose_entry)
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
                    st.write(f"**💊 {dose.get('pills', 1)} {pill_text} {dose['name']} ({dose['dosage']}mg total)** at {dose['time_str']}")
                
                with col2:
                    duration_hours = dose['duration_min'] / 60.0
                    st.write(f"Duration: {format_duration_hours_minutes(duration_hours)}")
                
                with col3:
                    if st.button("🗑️", key=f"del_pk_{dose['id']}"):
                        st.session_state.painkiller_doses.remove(dose)
                        st.rerun()
                
                # Show curve details in expandable section
                with st.expander(f"Curve details for {dose['name']}"):
                    onset_hours = dose['onset_min'] / 60.0
                    peak_time_hours = dose['peak_time_min'] / 60.0
                    duration_hours = dose['duration_min'] / 60.0
                    
                    st.write(f"**Onset**: {format_duration_hours_minutes(onset_hours)} → **Tmax**: {format_duration_hours_minutes(peak_time_hours)} → **Duration**: {format_duration_hours_minutes(duration_hours)}")
                    st.write(f"**Peak Intensity**: {dose['intensity_peak']}/10")
                    st.write(f"**Average Intensity**: {dose['intensity_avg']}/10")
                    
                            # Calculate actual curve phases using correct Tmax interpretation
                    onset_time = onset_hours
                    tmax_time = peak_time_hours  # Time to maximum effect
                    plateau_duration = dose['peak_duration_min'] / 60.0  # Duration of therapeutic plateau
                    duration = duration_hours
                    
                    # Calculate phase durations correctly
                    rise_duration = tmax_time  # Time from dose to peak
                    plateau_duration = dose['peak_duration_min'] / 60.0  # Duration of therapeutic plateau
                    
                    # Calculate fall duration - this should be the wear-off duration
                    fall_duration = dose['wear_off_duration_min'] / 60.0
                    
                    # Validate that phases add up to total duration
                    calculated_total = rise_duration + plateau_duration + fall_duration
                    if abs(calculated_total - duration) > 0.1:  # Allow small rounding differences
                        st.warning(f"⚠️ **Data Inconsistency**: Phases don't add up to total duration. Check JSON data.")
                        st.write(f"Calculated: {rise_duration:.1f}h + {plateau_duration:.1f}h + {fall_duration:.1f}h = {calculated_total:.1f}h")
                        st.write(f"Expected: {duration:.1f}h")
                    
                    st.write(f"**Rise Phase**: 0h → {format_duration_hours_minutes(tmax_time)} ({format_duration_hours_minutes(rise_duration)})")
                    st.write(f"**Plateau Phase**: {format_duration_hours_minutes(tmax_time)} → {format_duration_hours_minutes(tmax_time + plateau_duration)} ({format_duration_hours_minutes(plateau_duration)})")
                    st.write(f"**Fall Phase**: {format_duration_hours_minutes(tmax_time + plateau_duration)} → {format_duration_hours_minutes(duration)} ({format_duration_hours_minutes(fall_duration)})")
                    
                    # Show timing relative to dose time
                    dose_time_str = dose['time_str']
                    onset_time_str = format_time_hours_minutes(dose['time'] + onset_time)
                    tmax_time_str = format_time_hours_minutes(dose['time'] + tmax_time)
                    plateau_end_str = format_time_hours_minutes(dose['time'] + tmax_time + plateau_duration)
                    end_time_str = format_time_hours_minutes(dose['time'] + duration)
                    
                    st.write(f"**Timeline**: Dose at {dose_time_str} → Onset at {onset_time_str} → Tmax at {tmax_time_str} → Plateau ends at {plateau_end_str} → Ends at {end_time_str}")
        
        if st.session_state.painkiller_doses and st.button("🗑️ Clear All Painkillers"):
            st.session_state.painkiller_doses.clear()
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
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
    time_points = np.arange(0, 24.1, 0.1)  # 24 hours in 0.1 hour intervals
    pain_level = np.zeros_like(time_points)
    
    for dose in st.session_state.painkiller_doses:
        dose_time = dose['time']
        onset_hours = dose['onset_min'] / 60.0
        tmax_hours = dose['peak_time_min'] / 60.0  # Time to maximum effect (Tmax)
        duration_hours = dose['duration_min'] / 60.0
        peak_duration_hours = dose['peak_duration_min'] / 60.0  # Duration of peak effect
        
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
        
        adjusted_intensity = dose['intensity_peak'] * intensity_multiplier
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
                wear_off_duration = dose['wear_off_duration_min'] / 60.0 * duration_multiplier
                
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
        dose_time = dose['time']
        onset_hours = dose['onset_min'] / 60.0
        tmax_hours = dose['peak_time_min'] / 60.0  # Time to maximum effect (Tmax)
        duration_hours = dose['duration_min'] / 60.0
        peak_duration_hours = dose['peak_duration_min'] / 60.0  # Duration of peak effect
        
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
                effect = dose['intensity_peak'] * progress
            elif time_since_dose < tmax_hours + peak_duration_hours:
                # Peak phase (Tmax to end of peak duration)
                effect = dose['intensity_peak']
            elif time_since_dose < duration_hours:
                # Falling phase (end of peak to end of duration)
                fall_duration = duration_hours - (tmax_hours + peak_duration_hours)
                fall_progress = (time_since_dose - (tmax_hours + peak_duration_hours)) / fall_duration
                effect = dose['intensity_peak'] * (1 - fall_progress)
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
            x=dose['time'],
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
    
    # Create custom x-axis tick labels in HH:MM format
    tick_hours = list(range(0, 25, 3))
    tick_labels = [format_time_hours_minutes(hour) for hour in tick_hours]
    
    fig.update_xaxes(
        title_text="Time (24h)", 
        range=[0, 24], 
        tickmode='array',
        tickvals=tick_hours,
        ticktext=tick_labels,
        row=1, col=1
    )
    fig.update_yaxes(title_text="Pain Relief Level (/10)", range=[0, max_relief], row=1, col=1)
    
    fig.update_xaxes(
        title_text="Time (24h)", 
        range=[0, 24], 
        tickmode='array',
        tickvals=tick_hours,
        ticktext=tick_labels,
        row=2, col=1
    )
    fig.update_yaxes(title_text="Individual Relief", row=2, col=1)
    
    # Update hover template
    for trace in fig.data:
        if trace.x is not None and len(trace.x) > 0:
            hover_x = [format_time_hours_minutes(x) for x in trace.x]
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
        title_text="24-Hour Pain Relief Timeline",
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
