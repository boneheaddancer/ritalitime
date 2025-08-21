import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from medication_simulator import MedicationSimulator
import json
from datetime import datetime, time
import io

# Page configuration
st.set_page_config(
    page_title="ADHD Medication Timeline Simulator",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'simulator' not in st.session_state:
    st.session_state.simulator = MedicationSimulator()
if 'medications' not in st.session_state:
    st.session_state.medications = []

def main():
    st.title("💊 ADHD Medication Timeline Simulator")
    st.markdown("Simulate and visualize your medication effects throughout the day")
    
    # Sidebar for medication management
    with st.sidebar:
        st.header("📋 Medication Management")
        
        # Add new medication
        st.subheader("Add New Dose")
        
        col1, col2 = st.columns(2)
        with col1:
            dose_time = st.time_input("Dose Time", value=time(8, 0))
        with col2:
            dosage = st.number_input("Dosage (mg)", min_value=1.0, max_value=100.0, value=20.0, step=1.0)
        
        # Advanced parameters
        with st.expander("Advanced Parameters"):
            onset_time = st.slider("Onset Time (hours)", 0.5, 3.0, 1.0, 0.1)
            peak_time = st.slider("Peak Time (hours)", 1.0, 6.0, 2.0, 0.1)
            duration = st.slider("Duration (hours)", 4.0, 16.0, 8.0, 0.5)
            peak_effect = st.slider("Peak Effect", 0.1, 2.0, 1.0, 0.1)
        
        if st.button("➕ Add Dose", type="primary"):
            time_str = dose_time.strftime("%H:%M")
            st.session_state.simulator.add_medication(
                time_str, dosage, onset_time, peak_time, duration, peak_effect
            )
            st.success(f"Added {dosage}mg dose at {time_str}")
            st.rerun()
        
        st.divider()
        
        # Current medications
        st.subheader("Current Doses")
        medications = st.session_state.simulator.get_medication_summary()
        
        if not medications:
            st.info("No medications added yet")
        else:
            for med in medications:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{med['dosage']}mg** at {med['time']:.1f}h")
                with col2:
                    st.write(f"Duration: {med['duration']}h")
                with col3:
                    if st.button("🗑️", key=f"del_{med['id']}"):
                        st.session_state.simulator.remove_medication(med['id'])
                        st.rerun()
                
                # Show curve details in expandable section
                with st.expander(f"Curve details for {med['dosage']}mg dose"):
                    st.write(f"**Onset**: {med['onset_time']}h → **Peak**: {med['peak_time']}h → **Duration**: {med['duration']}h")
                    
                    # Calculate actual curve phases
                    rise_time = med['onset_time']
                    peak_time = med['peak_time']
                    available_time = med['duration'] - rise_time
                    min_plateau = 1.0
                    min_fall = 1.0
                    
                    if available_time >= (min_plateau + min_fall):
                        fall_start = rise_time + min_plateau
                        plateau_duration = min_plateau
                    else:
                        fall_start = med['duration'] - min_fall
                        if fall_start <= rise_time:
                            fall_start = rise_time + 0.5
                            plateau_duration = 0.5
                        else:
                            plateau_duration = fall_start - rise_time
                    
                    fall_duration = med['duration'] - fall_start
                    
                    st.write(f"**Rise Phase**: 0h → {rise_time}h ({rise_time}h)")
                    st.write(f"**Plateau Phase**: {rise_time}h → {rise_time + plateau_duration:.1f}h ({plateau_duration:.1f}h)")
                    st.write(f"**Fall Phase**: {rise_time + plateau_duration:.1f}h → {med['duration']}h ({fall_duration:.1f}h)")
        
        if medications and st.button("🗑️ Clear All"):
            st.session_state.simulator.clear_medications()
            st.rerun()
        
        st.divider()
        
        # Sleep threshold
        st.subheader("Sleep Settings")
        sleep_threshold = st.slider(
            "Sleep Threshold", 
            0.1, 2.0,  # Increased max to handle additive effects
            st.session_state.simulator.sleep_threshold, 
            0.05,
            help="Effect level below which sleep is suitable"
        )
        st.session_state.simulator.sleep_threshold = sleep_threshold
        
        # Effect scale info
        if len(medications) > 1:
            st.info("📏 **Effect Scale**: Multiple doses can create effects > 1.0 when overlapping")
        
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
                    st.session_state.simulator.import_schedule(io.StringIO(content.decode()))
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
        fig = create_timeline_plot(time_points, effect_level, medications)
        st.plotly_chart(fig, use_container_width=True)
        
        # Sleep windows
        sleep_windows = st.session_state.simulator.find_sleep_windows(effect_level)
        if sleep_windows:
            st.subheader("😴 Sleep Windows")
            for start, end in sleep_windows:
                start_str = f"{int(start):02d}:{int((start % 1) * 60):02d}"
                end_str = f"{int(end):02d}:{int((end % 1) * 60):02d}"
                st.info(f"**{start_str}** to **{end_str}** (Duration: {end-start:.1f}h)")
        else:
            st.warning("⚠️ No suitable sleep windows found with current threshold")
    
    with col2:
        # Statistics and insights
        st.subheader("📊 Daily Statistics")
        
        if effect_level.max() > 0:
            max_effect_time = time_points[np.argmax(effect_level)]
            max_effect_str = f"{int(max_effect_time):02d}:{int((max_effect_time % 1) * 60):02d}"
            
            st.metric("Peak Effect Time", max_effect_str)
            st.metric("Peak Effect Level", f"{effect_level.max():.2f}")
            st.metric("Average Effect", f"{effect_level.mean():.2f}")
            
            # Show additive effect indicator
            if effect_level.max() > 1.0:
                st.success(f"🚀 **Additive Effects Detected!** Multiple doses are overlapping to create enhanced effects (max: {effect_level.max():.2f})")
            elif len(medications) > 1:
                st.info(f"📊 **Multiple Doses**: {len(medications)} doses with combined peak effect of {effect_level.max():.2f}")
            
            # Effect distribution
            st.subheader("📈 Effect Distribution")
            effect_df = pd.DataFrame({
                'Time': [f"{int(t):02d}:{int((t % 1) * 60):02d}" for t in time_points],
                'Effect': effect_level
            })
            
            # Create histogram
            hist_fig = px.histogram(
                effect_df, 
                x='Effect', 
                nbins=20,
                title="Effect Level Distribution"
            )
            hist_fig.update_layout(height=300)
            st.plotly_chart(hist_fig, use_container_width=True)
        else:
            st.info("Add medications to see statistics")
        
        # Quick profiles
        st.subheader("⚡ Quick Profiles")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌅 Day Shift"):
                st.session_state.simulator.clear_medications()
                st.session_state.simulator.add_medication("08:00", 20.0, 1.0, 2.0, 8.0)
                st.session_state.simulator.add_medication("16:00", 10.0, 1.0, 2.0, 6.0)
                st.rerun()
        
        with col2:
            if st.button("🌙 Night Shift"):
                st.session_state.simulator.clear_medications()
                st.session_state.simulator.add_medication("20:00", 20.0, 1.0, 2.0, 8.0)
                st.session_state.simulator.add_medication("04:00", 15.0, 1.0, 2.0, 6.0)
                st.rerun()
        
        if st.button("🧘 Total Zen"):
            st.session_state.simulator.clear_medications()
            st.rerun()

def create_timeline_plot(time_points, effect_level, medications):
    """Create the main timeline visualization"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Medication Effect Timeline", "Individual Doses"),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3]
    )
    
    # Main effect curve
    fig.add_trace(
        go.Scatter(
            x=time_points,
            y=effect_level,
            mode='lines',
            name='Combined Effect',
            line=dict(color='#1f77b4', width=3),
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
    
    # Individual medication curves
    for med in medications:
        individual_effect = st.session_state.simulator.generate_effect_curve(med)
        fig.add_trace(
            go.Scatter(
                x=time_points,
                y=individual_effect,
                mode='lines',
                name=f"{med['dosage']}mg at {med['time']:.1f}h",
                line=dict(width=1, dash='dot'),
                opacity=0.6
            ),
            row=2, col=1
        )
    
    # Dose markers
    for med in medications:
        fig.add_vline(
            x=med['time'],
            line_width=2,
            line_color="orange",
            annotation_text=f"{med['dosage']}mg",
            row=1, col=1
        )
    
    # Update layout - allow effect levels to exceed 1.0 for multiple doses
    max_effect = max(1.1, effect_level.max() * 1.1) if len(effect_level) > 0 else 1.1
    fig.update_xaxes(title_text="Time (24h)", range=[0, 24], row=1, col=1)
    fig.update_yaxes(title_text="Effect Level", range=[0, max_effect], row=1, col=1)
    fig.update_xaxes(title_text="Time (24h)", range=[0, 24], row=2, col=1)
    fig.update_yaxes(title_text="Individual Effects", row=2, col=1)
    
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="24-Hour Medication Effect Timeline",
        hovermode='x unified'
    )
    
    return fig

if __name__ == "__main__":
    main()
