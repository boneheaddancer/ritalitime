                # Show curve details in expandable section
                with st.expander(f"Curve details for {med['dosage']}mg dose"):
                    st.write(f"**Onset**: {med['onset_time']}h → **Peak**: {med['peak_time']}h → **Duration**: {med['duration']}h")
                    
                    # Calculate actual curve phases based on new implementation
                    onset_time = med['onset_time']      # Time from dose to onset
                    peak_time = med['peak_time']        # Time from dose to peak effect
                    duration = med['duration']          # Total duration
                    
                    # Calculate fall start (ensuring minimum fall duration)
                    min_fall_duration = 1.0
                    fall_start = max(peak_time, duration - min_fall_duration)
                    
                    # Calculate phase durations
                    rise_duration = onset_time
                    plateau_duration = fall_start - onset_time
                    fall_duration = duration - fall_start
                    
                    st.write(f"**Rise Phase**: 0h → {onset_time}h ({rise_duration:.1f}h)")
                    st.write(f"**Plateau Phase**: {onset_time}h → {fall_start:.1f}h ({plateau_duration:.1f}h)")
                    st.write(f"**Fall Phase**: {fall_start:.1f}h → {duration}h ({fall_duration:.1f}h)")
                    
                    # Show timing relative to dose time
                    dose_time_str = f"{int(med['time']):02d}:{int((med['time'] % 1) * 60):02d}"
                    onset_time_str = f"{int(med['time'] + onset_time):02d}:{int(((med['time'] + onset_time) % 1) * 60):02d}"
                    peak_time_str = f"{int(med['time'] + peak_time):02d}:{int(((med['time'] + peak_time) % 1) * 60):02d}"
                    end_time_str = f"{int(med['time'] + duration):02d}:{int(((med['time'] + duration) % 1) * 60):02d}"
                    
                    st.write(f"**Timeline**: Dose at {dose_time_str} → Onset at {onset_time_str} → Peak at {peak_time_str} → Ends at {end_time_str}")
