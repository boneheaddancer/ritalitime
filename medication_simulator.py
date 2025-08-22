import numpy as np
import pandas as pd
import math
from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple, Optional
import json
from pk_models import concentration_curve, suggest_lag_model
from saturation import combine_and_cap
import streamlit as st

# Test if concentration_curve is available
print(f"DEBUG: concentration_curve imported successfully: {concentration_curve}")
print(f"DEBUG: suggest_lag_model imported successfully: {suggest_lag_model}")

class MedicationSimulator:
    """ADHD Medication Timeline Simulator with PK-based curves and saturation"""
    
    def __init__(self):
        self.medications = []
        self.stimulants = []
        # Initialize with base 24 hours, will be extended dynamically if needed
        self.base_time_points_minutes = np.arange(0, 1440, 6)  # 0 to 1434 minutes in 6-min steps
        self.time_points_minutes = self.base_time_points_minutes.copy()
        self.time_points = self.time_points_minutes / 60.0  # Convert to hours for plotting/labels only
        self.sleep_threshold = 0.3  # Effect level below which sleep is suitable
        # Saturation parameters for combined effects
        self.emax = 1.0  # Maximum combined effect (ceiling)
        self.ec50 = 0.5  # Concentration for 50% of max effect
        self.hill_coefficient = 1.5  # Hill coefficient for saturation curve
        # Track failed doses from last timeline generation
        self.last_failed_doses = []
        # Dose-response model parameters (transparent and parametric)
        # Using simple linear concentration-to-effect model for transparency
        # Effect = concentration × dose × response_factor
        # This avoids pretending we have precise EC50/Hill values without citations
        self.default_medication_response_factor = 0.1   # Effect per mg (allows dose scaling)
        self.default_stimulant_response_factor = 0.5    # Effect per unit (allows dose scaling)
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM time string to minutes since midnight (0-1439)"""
        hour, minute = map(int, time_str.split(':'))
        return (hour * 60 + minute) % 1440
    
    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes since midnight to HH:MM format (supports extended timelines)"""
        if minutes < 1440:
            # Within first 24 hours
            hour = minutes // 60
            minute = minutes % 60
            return f"{hour:02d}:{minute:02d}"
        else:
            # Beyond 24 hours - show as Day 2, Day 3, etc.
            day = (minutes // 1440) + 1
            remaining_minutes = minutes % 1440
            hour = remaining_minutes // 60
            minute = remaining_minutes % 60
            return f"Day {day}: {hour:02d}:{minute:02d}"
    
    def _minutes_to_decimal_hours(self, minutes: int) -> float:
        """Convert minutes since midnight to decimal hours (can exceed 24 for extended timelines)"""
        return minutes / 60.0
    
    def _decimal_hours_to_minutes(self, decimal_hours: float) -> int:
        """Convert decimal hours to minutes since midnight (supports extended timelines)"""
        minutes = int(decimal_hours * 60)
        return minutes  # No more wrapping - allow extended timelines
    
    def _load_medications_data(self) -> Dict:
        """Load unified medications data"""
        try:
            with open('medications.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading medications.json: {e}")
            return {}
    
    def apply_saturation(self, total_concentration: np.ndarray) -> np.ndarray:
        """
        Apply Hill saturation curve to total concentration
        This prevents unlimited additive effects while preserving individual dose timing
        """
        from saturation import hill_emax
        return hill_emax(total_concentration, self.emax, self.ec50, self.hill_coefficient)
    
    def generate_pk_curve(self, dose: Dict) -> np.ndarray:
        """Generate PK-based concentration curve for a single dose using pk_models.py"""
        print(f"=== generate_pk_curve CALLED ===")
        print(f"DEBUG: Method entered successfully")
        
        # Validate dose parameters before proceeding
        try:
            self._validate_dose_parameters(dose)
        except ValueError as e:
            print(f"Validation failed for dose {dose.get('id', 'unknown')}: {e}")
            raise
        
        effect = np.zeros_like(self.time_points_minutes, dtype=float)
        

        
        # Debug: print dose structure
        print(f"Generating PK curve for dose: {dose}")
        
        # Get PK parameters from dose - use the stored minute values
        onset_min = dose.get('onset_min')  # Already validated
        t_peak_min = dose.get('t_peak_min')  # Already validated
        duration_min = dose.get('duration_min')  # Already validated
        
        # Debug output - all parameters are now in minutes
        print(f"PK parameters: onset={onset_min}min, peak={t_peak_min}min, duration={duration_min}min")
        
        # Generate PK curve using the concentration_curve function
        try:
            # Suggest appropriate lag model based on drug characteristics
            medication_type = dose.get('medication_name', '')
            suggested_lag_model = suggest_lag_model(onset_min, medication_type)
            
            print(f"Calling concentration_curve with: onset_min={onset_min}, t_peak_min={t_peak_min}, duration_min={duration_min}")
            print(f"Suggested lag_model: {suggested_lag_model} for {medication_type or 'unknown medication'}")
            
            # Generate PK curve for the full extended timeline period
            # Use the extended timeline length instead of fixed 24 hours
            timeline_minutes = len(self.time_points_minutes) * 6  # Convert back to total minutes
            pk_curve = concentration_curve(
                dose=1.0,  # Unit dose - actual concentration values will be returned
                onset_min=onset_min,
                t_peak_min=t_peak_min,
                duration_min=duration_min,
                minutes=timeline_minutes,  # Use extended timeline length
                step=6,  # 6-minute intervals to match our time grid
                lag_model=suggested_lag_model,
                start_time_min=dose['time']  # Start from dose time for proper alignment
            )
            print(f"concentration_curve returned: {len(pk_curve)} points")
            
            # Extract time points and concentrations
            pk_times = [t for t, _ in pk_curve]  # Keep in minutes
            pk_concentrations = [c for _, c in pk_curve]
            
            # Debug output
            print(f"PK curve generated: {len(pk_times)} points, max concentration: {max(pk_concentrations) if pk_concentrations else 0}")
            print(f"Time points: {len(self.time_points_minutes)}, from {self.time_points_minutes[0]}min to {self.time_points_minutes[-1]}min")
            print(f"Dose time: {dose['time']} minutes ({dose['time']/60:.1f}h)")
            
            # Use linear interpolation for smooth PK curves
            print(f"Starting smooth interpolation for {len(self.time_points_minutes)} time points")
            effect_points_calculated = 0
            
            # Extract time points and concentrations from PK curve for interpolation
            pk_times_minutes = [t for t, _ in pk_curve]  # Time points in minutes
            pk_concentrations = [c for _, c in pk_curve]  # Concentration values
            
            # Ensure we have valid data for interpolation
            if len(pk_times_minutes) < 2 or len(pk_concentrations) < 2:
                print(f"Warning: Insufficient PK curve data for interpolation. Points: {len(pk_times_minutes)}")
                return np.zeros_like(self.time_points_minutes)
            
            # Validate that time points are monotonically increasing
            if not all(pk_times_minutes[i] <= pk_times_minutes[i+1] for i in range(len(pk_times_minutes)-1)):
                print(f"Warning: PK curve time points are not monotonically increasing. Sorting...")
                # Sort by time if needed
                sorted_indices = np.argsort(pk_times_minutes)
                pk_times_minutes = [pk_times_minutes[i] for i in sorted_indices]
                pk_concentrations = [pk_concentrations[i] for i in sorted_indices]
            
            # Convert PK times to numpy array for interpolation
            pk_times_array = np.array(pk_times_minutes)
            pk_concentrations_array = np.array(pk_concentrations)
            

            
            for i, t in enumerate(self.time_points_minutes):
                # Calculate time since dose
                # With extended timeline, no need for midnight wrapping
                current_time_minutes = int(t)
                
                # Calculate time since dose (can be negative if before dose time)
                time_since_dose = current_time_minutes - dose['time']
                
                # Process if within duration or during natural decay (allows effects to cross midnight)
                # Remove artificial cutoff to show realistic wear-off
                if time_since_dose >= 0:
                    # Use numpy.interp for smooth linear interpolation
                    # This provides smooth transitions between PK curve points instead of step functions
                    # Benefits:
                    # - Accurate Tmax timing (no shifting due to nearest-neighbor)
                    # - Smooth curves (no artificial plateaus)
                    # - Better representation of continuous PK processes
                    try:
                        # Map time_since_dose to the actual PK curve time
                        # time_since_dose = 0 corresponds to dose time, so we need to look at dose time in PK curve
                        pk_curve_time = dose['time'] + time_since_dose
                        
                        interpolated_concentration = np.interp(
                            pk_curve_time,  # Query time in PK curve (minutes)
                            pk_times_array,   # Known time points (minutes)
                            pk_concentrations_array,  # Known concentration values
                            left=0.0,   # Value for times before first PK point
                            right=0.0    # Value for times after last PK point
                        )
                        
                        
                            

                            
                    except Exception as e:
                        print(f"Interpolation failed at time {time_since_dose:.1f} min: {e}")
                        interpolated_concentration = 0.0
                    
                    # Store normalized concentration (0-1) - intensity and saturation will be applied later
                    # Store concentration values
                    effect[i] = interpolated_concentration
                    effect_points_calculated += 1
            
            print(f"Smooth interpolation complete: {effect_points_calculated} points calculated")
            
            # Debug: check what effect values were generated
            max_effect = np.max(effect)
            non_zero_count = np.count_nonzero(effect)
            print(f"Generated effect curve: max={max_effect:.6f}, non-zero points={non_zero_count}/{len(effect)}")
            
            # Validate interpolation quality (without dose_intensity since we're using new PK model)
            self._validate_interpolation_quality(effect, pk_times_array, pk_concentrations_array)
            
            # Return the generated effect curve
            return effect
            
        except Exception as e:
            # Log the specific error for debugging
            print(f"PK curve generation failed for dose {dose.get('id', 'unknown')}: {e}")
            print(f"Dose data: {dose}")
            
            # Return zero effect instead of misleading fallback data
            # This ensures users see when something is wrong rather than fake curves
            print(f"Returning zero effect for failed dose {dose.get('id', 'unknown')}")
            return np.zeros_like(self.time_points_minutes)
    
    def _validate_dose_parameters(self, dose: Dict) -> None:
        """Validate that dose has all required parameters for PK curve generation"""
        required_fields = ['onset_min', 't_peak_min', 'duration_min']
        missing_fields = [field for field in required_fields if dose.get(field) is None]
        
        if missing_fields:
            raise ValueError(f"Dose {dose.get('id', 'unknown')} missing required fields: {missing_fields}")
        
        # Validate parameter values
        if dose.get('onset_min', 0) <= 0:
            raise ValueError(f"Invalid onset_min for dose {dose.get('id', 'unknown')}: {dose.get('onset_min')}")
        if dose.get('t_peak_min', 0) <= 0:
            raise ValueError(f"Invalid t_peak_min for dose {dose.get('id', 'unknown')}: {dose.get('t_peak_min')}")
        if dose.get('duration_min', 0) <= 0:
            raise ValueError(f"Invalid duration_min for dose {dose.get('id', 'unknown')}: {dose.get('duration_min')}")
        
        # Validate logical relationships
        if dose.get('t_peak_min', 0) <= dose.get('onset_min', 0):
            raise ValueError(f"t_peak_min must be greater than onset_min for dose {dose.get('id', 'unknown')}")
        if dose.get('duration_min', 0) <= dose.get('t_peak_min', 0):
            raise ValueError(f"duration_min must be greater than t_peak_min for dose {dose.get('id', 'unknown')}")
    
    def _validate_interpolation_quality(self, effect: np.ndarray, pk_times: np.ndarray, 
                                      pk_concentrations: np.ndarray) -> None:
        """Validate the quality of the interpolation and provide debugging information"""
        try:
            # Check for expected peak timing
            if len(pk_times) > 0 and len(pk_concentrations) > 0:
                expected_peak_time = pk_times[np.argmax(pk_concentrations)]
                expected_peak_concentration = np.max(pk_concentrations)
                
                # Find actual peak in interpolated effect
                actual_peak_idx = np.argmax(effect)
                actual_peak_time = self.time_points_minutes[actual_peak_idx]  # Already in minutes
                
                # Calculate timing difference
                timing_diff = abs(actual_peak_time - expected_peak_time)
                
                if timing_diff > 10:  # More than 10 minutes difference
                    print(f"Warning: Peak timing shifted by {timing_diff:.1f} minutes")
                    print(f"  Expected: {expected_peak_time:.1f} min, Actual: {actual_peak_time:.1f} min")
                
                # Peak effect scaling is now handled by dose-response model, not arbitrary scaling
                # The effect curve is normalized concentration (0-1) and will be scaled later
                
                # Check for smoothness (no sudden jumps)
                effect_diff = np.diff(effect)
                max_jump = np.max(np.abs(effect_diff))
                if max_jump > 0.1:  # Large jumps might indicate interpolation issues
                    print(f"Warning: Large effect jump detected: {max_jump:.6f}")
                    
        except Exception as e:
            print(f"Interpolation quality validation failed: {e}")
    
    def _extend_timeline_if_needed(self):
        """Create dynamic timeline that starts before first dose and extends beyond last dose"""
        all_doses = self.get_all_doses()
        if not all_doses:
            return
        
        # Find the earliest and latest times we need to cover
        min_time_needed = float('inf')
        max_time_needed = 0
        
        for dose in all_doses:
            dose_time = dose['time']
            duration_min = dose.get('duration_min', 480)  # Default 8 hours
            end_time = dose_time + duration_min
            
            min_time_needed = min(min_time_needed, dose_time)
            max_time_needed = max(max_time_needed, end_time)
            print(f"DEBUG: Dose at {dose_time}min ({dose_time/60:.1f}h) + {duration_min}min duration = {end_time}min ({end_time/60:.1f}h)")
        
        print(f"DEBUG: Time range needed: {min_time_needed}min to {max_time_needed}min ({min_time_needed/60:.1f}h to {max_time_needed/60:.1f}h)")
        
        # Add buffer time before first dose and after last dose
        buffer_before = 60  # 1 hour before first dose
        buffer_after = 120  # 2 hours after last dose ends
        
        # Calculate timeline boundaries
        start_time = max(0, min_time_needed - buffer_before)
        end_time = max_time_needed + buffer_after
        
        # Ensure minimum timeline length (at least 8 hours)
        min_timeline_length = 8 * 60  # 8 hours in minutes
        if end_time - start_time < min_timeline_length:
            # Center the timeline around the doses
            center_time = (min_time_needed + max_time_needed) / 2
            half_length = min_timeline_length / 2
            start_time = max(0, center_time - half_length)
            end_time = center_time + half_length
        
        # Round to nearest 6-minute boundary for clean intervals
        start_time = (start_time // 6) * 6
        end_time = ((end_time + 5) // 6) * 6
        
        # Create dynamic timeline
        timeline_minutes = np.arange(start_time, end_time + 1, 6)
        self.time_points_minutes = timeline_minutes
        self.time_points = timeline_minutes / 60.0
        
        print(f"Dynamic timeline: {len(timeline_minutes)} points, from {start_time/60:.1f}h to {end_time/60:.1f}h")
        
        # Check if this extends beyond 24 hours
        if end_time > 1440:
            print(f"Timeline extends beyond 24h: {end_time/60:.1f} hours total")

    def generate_daily_timeline(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate combined daily effect timeline from all doses using PK curves and saturation"""
        if not self.medications and not self.stimulants:
            return self.time_points, np.zeros_like(self.time_points_minutes)
        
        # Extend timeline if needed for doses beyond 24 hours
        self._extend_timeline_if_needed()
        
        # Generate individual PK curves for all doses (normalized to peak=1)
        individual_curves = []
        dose_metadata = []  # Store dose info for intensity scaling
        failed_doses = []
        
        for dose in self.get_all_doses():
            try:
                curve = self.generate_pk_curve(dose)
                
                if np.any(curve > 0):  # Check if curve has any effect
                    individual_curves.append(curve)
                    dose_metadata.append(dose)
                    print(f"Generated curve for dose {dose.get('id', 'unknown')}: max effect = {np.max(curve)}")
                else:
                    failed_doses.append(dose)
                    print(f"Warning: Dose {dose.get('id', 'unknown')} generated zero effect curve")

            except Exception as e:
                failed_doses.append(dose)
                print(f"Error generating curve for dose {dose.get('id', 'unknown')}: {e}")
        
        # Store failed doses for later access
        self.last_failed_doses = failed_doses
        
        # Report any failed doses
        if failed_doses:
            print(f"Warning: {len(failed_doses)} doses failed to generate curves")
            for dose in failed_doses:
                print(f"  - Failed dose: {dose}")
        
        # Apply dose-response scaling to each curve before combining
        scaled_curves = []
        for i, (curve, dose) in enumerate(zip(individual_curves, dose_metadata)):
            # Apply simple linear dose-response model to convert concentration to effect
            # Effect = concentration × dose × response_factor (transparent and parametric)
            scaled_curve = self._apply_dose_response_scaling(curve, dose)
            scaled_curves.append(scaled_curve)
            print(f"Scaled curve {i}: max concentration = {np.max(curve):.3f}, max effect = {np.max(scaled_curve):.3f}")
        
        # Combine scaled curves using saturation model
        if len(scaled_curves) == 1:
            combined_effect = scaled_curves[0]
        else:
            # Convert numpy arrays to lists for saturation function
            curve_lists = [curve.tolist() for curve in scaled_curves]
            combined_effect = np.array(combine_and_cap(
                curve_lists, 
                emax=self.emax, 
                ec50=self.ec50, 
                h=self.hill_coefficient
            ))
        
        print(f"Combined effect: max = {np.max(combined_effect) if len(combined_effect) > 0 else 0}")
        # Return time points in hours for plotting/labels, but effect curve uses minute-based grid
        return self.time_points, combined_effect
    
    def get_individual_curves(self) -> List[Tuple[str, np.ndarray]]:
        """Get individual effect curves for plotting (with dose-response scaling applied)"""
        curves = []
        for dose in self.get_all_doses():
            try:
                # Generate normalized concentration curve
                concentration_curve = self.generate_pk_curve(dose)
                if np.any(concentration_curve > 0):  # Only include curves with actual effect
                    # Apply dose-response scaling to convert concentration to effect
                    effect_curve = self._apply_dose_response_scaling(concentration_curve, dose)
                    
                    if dose['type'] == 'medication':
                        label = f"{dose['dosage']}mg {dose.get('medication_name', 'medication')}"
                    else:
                        label = f"{dose['quantity']}x {dose['stimulant_name']}"
                        if dose.get('component_name'):
                            label += f" ({dose['component_name']})"
                    curves.append((label, effect_curve))
            except Exception as e:
                print(f"Skipping failed dose {dose.get('id', 'unknown')} in individual curves: {e}")
        return curves
    
    def add_medication(self, dose_time: str, dosage: float, 
                       onset_time: float = 1.0, peak_time: float = 2.0, 
                       duration: float = 8.0, peak_effect: float = 1.0,
                       medication_name: str = None, custom_params: Dict = None):
        """
        Add a medication dose to the simulation
        
        Args:
            dose_time: Time in HH:MM format
            dosage: Dose in mg
            onset_time: Time from dose to onset (hours) - overridden if medication_name is provided
            peak_time: Time from dose to peak effect (hours) - overridden if medication_name is provided
            duration: Total duration from dose to complete wear-off (hours) - overridden if medication_name is provided
            peak_effect: Peak effect level (0-1) - overridden if medication_name is provided
            medication_name: Name of prescription medication (e.g., 'ritalin_IR', 'adderall_XR')
            custom_params: Override default parameters if provided
        """
        # Convert time to minutes since midnight
        dose_minutes = self._time_to_minutes(dose_time)
        
        # If medication_name is provided, load from unified medications database
        if medication_name:
            medication_data = self._get_prescription_data(medication_name)
            if medication_data:
                # Convert minutes to hours
                onset_time = medication_data['onset_min'] / 60.0
                peak_time = medication_data['t_peak_min'] / 60.0
                duration = medication_data['duration_min'] / 60.0
                # Calculate peak effect based on dosage
                # Store the actual dosage for PK-based dose-response calculation
                # peak_effect is no longer used - effect is calculated from concentration using Emax model
                # Keep peak_effect for backward compatibility but it's not used in PK calculations
                peak_effect = 1.0  # Default value, not used in new PK model
                
                # Store additional parameters for curve generation
                peak_duration = medication_data['peak_duration_min'] / 60.0
                wear_off_duration = medication_data['wear_off_min'] / 60.0
                
                # Get half-life data if available
                half_life_hours = medication_data.get('half_life_hours')
                
                # Debug: print loaded medication data
                print(f"Loaded medication data for {medication_name}: onset={onset_time:.2f}h, peak={peak_time:.2f}h, duration={duration:.2f}h, peak_effect={peak_effect:.3f}")
            else:
                raise ValueError(f"Unknown medication: {medication_name}")
        else:
            peak_duration = 1.0  # Default peak duration
            wear_off_duration = 1.0  # Default wear-off duration
        
        # Override with custom parameters if provided
        if custom_params:
            if 'onset_time' in custom_params:
                onset_time = custom_params['onset_time']
            if 'peak_time' in custom_params:
                peak_time = custom_params['peak_time']
            if 'duration' in custom_params:
                duration = custom_params['duration']
            if 'peak_effect' in custom_params:
                peak_effect = custom_params['peak_effect']
            # Note: peak_duration and wear_off_duration are not overridden by custom params
            # They come from the medication data to maintain consistency
        
        # Validate parameters
        if peak_time < onset_time:
            raise ValueError("peak_time must be >= onset_time")
        if duration < peak_time:
            raise ValueError("duration must be >= peak_time")
        
        # Ensure all required parameters are set
        if onset_time <= 0 or peak_time <= 0 or duration <= 0 or peak_effect <= 0:
            raise ValueError("All parameters must be positive values")
        
        medication = {
            'time': dose_minutes,  # Store as minutes since midnight
            'dosage': dosage,
            'medication_name': medication_name,
            'half_life_hours': half_life_hours,
            'peak_effect': peak_effect,  # Store the calculated peak effect
            # Store standardized minute values for PK curve generation
            'onset_min': int(onset_time * 60),
            't_peak_min': int(peak_time * 60),
            'duration_min': int(duration * 60),
            'peak_duration_min': int(peak_duration * 60),
            'wear_off_min': int(wear_off_duration * 60),
            'type': 'medication',
            'id': len(self.medications) + len(self.stimulants)
        }
        
        self.medications.append(medication)
    
    def add_stimulant(self, dose_time: str, stimulant_name: str, component_name: str = None, 
                       quantity: float = 1.0, custom_params: Dict = None):
        """
        Add a stimulant dose to the simulation
        
        Args:
            dose_time: Time in HH:MM format
            stimulant_name: Name of the stimulant (e.g., 'coffee', 'redbull')
            component_name: Specific component (e.g., 'caffeine', 'taurine') - optional for simple stimulants
            quantity: Quantity consumed (e.g., cups of coffee, cans of energy drink)
            custom_params: Override default parameters if provided
        """
        # Convert time to minutes since midnight
        dose_minutes = self._time_to_minutes(dose_time)
        
        # Load stimulant data from unified database
        stimulant_data = self._get_stimulant_data(stimulant_name, component_name)
        
        if not stimulant_data:
            raise ValueError(f"Unknown stimulant: {stimulant_name}" + (f" component: {component_name}" if component_name else ""))
        
        # Convert minutes to hours
        onset_time = stimulant_data['onset_min'] / 60.0
        peak_time = stimulant_data['t_peak_min'] / 60.0  # Fixed field name
        duration = stimulant_data['duration_min'] / 60.0
        # peak_effect is no longer used - effect is calculated from concentration using Emax model
        # Keep peak_effect for backward compatibility but it's not used in PK calculations
        peak_effect = 1.0  # Default value, not used in new PK model
        
        # Store additional parameters for curve generation
        peak_duration = stimulant_data['peak_duration_min'] / 60.0
        wear_off_duration = stimulant_data['wear_off_min'] / 60.0  # Fixed field name
        
        # Override with custom parameters if provided
        if custom_params:
            if 'onset_time' in custom_params:
                onset_time = custom_params['onset_time']
            if 'peak_time' in custom_params:
                peak_time = custom_params['peak_time']
            if 'duration' in custom_params:
                duration = custom_params['duration']
            if 'peak_effect' in custom_params:
                peak_effect = custom_params['peak_effect']
            # Note: peak_duration and wear_off_duration are not overridden by custom params
            # They come from the stimulant data to maintain consistency
        
        # Validate parameters
        if onset_time <= 0 or peak_time <= 0 or duration <= 0 or peak_effect <= 0:
            raise ValueError("All parameters must be positive values")
        if peak_time < onset_time:
            raise ValueError("peak_time must be >= onset_time")
        if duration < peak_time:
            raise ValueError("duration must be >= peak_time")
        
        # Scale effect by quantity
        peak_effect *= quantity
        
        stimulant = {
            'time': dose_minutes,  # Store as minutes since midnight
            'stimulant_name': stimulant_name,
            'component_name': component_name,
            'quantity': quantity,
            'peak_effect': peak_effect,
            # Store standardized minute values for PK curve generation
            'onset_min': stimulant_data['onset_min'],
            't_peak_min': stimulant_data['t_peak_min'],
            'duration_min': stimulant_data['duration_min'],
            'peak_duration_min': stimulant_data['peak_duration_min'],
            'wear_off_min': stimulant_data['wear_off_min'],
            'type': 'stimulant',
            'id': len(self.medications) + len(self.stimulants)
        }
        
        self.stimulants.append(stimulant)
    
    def _apply_dose_response_scaling(self, concentration_curve: np.ndarray, dose: Dict) -> np.ndarray:
        """
        Apply dose-response scaling to convert concentration to effect using simple linear model
        
        Args:
            concentration_curve: Actual concentration curve (not normalized, preserving dose-response relationships)
            dose: Dose dictionary containing dosage and type information
            
        Returns:
            Effect curve (0-1) based on dose-response relationship
            
        Note: This uses a simplified linear model for transparency. The effect is
        proportional to concentration × dose, avoiding claims of precision without citations.
        The concentration curve now contains actual PK-derived values, not normalized ones.
        """
        # Get dose-response parameter for this medication/stimulant
        if dose['type'] == 'medication':
            response_factor = self._get_dose_response_params(medication_name=dose.get('medication_name'))
        else:
            response_factor = self._get_dose_response_params(stimulant_name=dose.get('stimulant_name'))
        
        # Get actual dose amount
        actual_dosage = dose.get('dosage', dose.get('quantity', 1.0))
        
        # Apply simple linear dose-response model: Effect = concentration × dose × response_factor
        # This is transparent and parametric, avoiding false precision
        # concentration_curve now contains actual PK values, so this gives proper dose-response scaling
        effect_curve = concentration_curve * actual_dosage * response_factor
        
        # Cap at maximum effect (1.0) to prevent unrealistic values
        effect_curve = np.minimum(effect_curve, 1.0)
        
        return effect_curve
    
    def _calculate_dose_intensity(self, concentration: float, response_factor: float, max_effect: float = 1.0) -> float:
        """
        Calculate dose intensity using simple linear concentration-to-effect model
        
        Args:
            concentration: Drug concentration (normalized 0-1)
            response_factor: Effect per unit concentration (transparent parameter)
            max_effect: Maximum possible effect (default 1.0)
            
        Returns:
            Effect intensity (0 to max_effect)
            
        Note: This is a simplified model for transparency. Real dose-response 
        relationships may be more complex, but we avoid claiming precision without citations.
        """
        if concentration <= 0:
            return 0.0
        
        # Simple linear model: Effect = concentration × response_factor
        effect = concentration * response_factor
        return min(effect, max_effect)  # Cap at maximum effect
    
    def _get_dose_response_params(self, medication_name: str = None, stimulant_name: str = None) -> float:
        """
        Get dose-response parameter (response_factor) for a medication or stimulant
        
        Args:
            medication_name: Name of medication (if applicable)
            stimulant_name: Name of stimulant (if applicable)
            
        Returns:
            Response factor (effect per unit concentration)
            
        Note: This uses a simple linear model for transparency. Real dose-response
        relationships may be more complex, but we avoid claiming precision without citations.
        """
        # For now, use default response factors
        # In the future, these could be calibrated from published data if available
        if medication_name:
            return self.default_medication_response_factor
        else:
            return self.default_stimulant_response_factor
    
    def _get_stimulant_data(self, stimulant_name: str, component_name: str = None) -> Optional[Dict]:
        """Get stimulant data from the unified medications.json file"""
        try:
            data = self._load_medications_data()
            
            stimulants = data.get('stimulants', {}).get('common_stimulants', {})
            
            if stimulant_name not in stimulants:
                return None
            
            stimulant = stimulants[stimulant_name]
            
            # If it's a simple stimulant (like coffee)
            if 'onset_min' in stimulant:
                return stimulant
            
            # If it's a complex stimulant with components (like redbull)
            if component_name and component_name in stimulant:
                return stimulant[component_name]
            
            # Return first component if no specific component specified
            if not component_name and stimulant:
                first_component = list(stimulant.values())[0]
                if isinstance(first_component, dict) and 'onset_min' in first_component:
                    return first_component
            
            # No valid stimulant data found
            return None
            
        except Exception as e:
            print(f"Error loading stimulant data: {e}")
            return None
    
    def _get_prescription_data(self, medication_name: str) -> Optional[Dict]:
        """Get prescription medication data from the unified medications.json file"""
        try:
            data = self._load_medications_data()
            
            # Debug: print what we're looking for
            print(f"Looking for medication: {medication_name}")
            print(f"Available prescription stimulants: {list(data.get('stimulants', {}).get('prescription_stimulants', {}).keys())}")
            print(f"Available painkillers: {list(data.get('painkillers', {}).keys())}")
            
            # Check prescription stimulants first
            medications = data.get('stimulants', {}).get('prescription_stimulants', {})
            
            if medication_name in medications:
                print(f"Found {medication_name} in prescription stimulants")
                return medications[medication_name]
            
            # Check painkillers
            painkillers = data.get('painkillers', {})
            
            if medication_name in painkillers:
                print(f"Found {medication_name} in painkillers")
                return painkillers[medication_name]
            
            print(f"Medication {medication_name} not found in any category")
            return None
            
        except Exception as e:
            print(f"Error loading prescription data: {e}")
            return None
    
    def get_all_doses(self) -> List[Dict]:
        """Get all doses (medications + stimulants)"""
        return self.medications + self.stimulants
    
    def clear_all_doses(self):
        """Clear all medications and stimulants"""
        self.medications = []
        self.stimulants = []
    
    def remove_dose(self, dose_id: int):
        """Remove a dose by ID"""
        # Check medications first
        self.medications = [med for med in self.medications if med['id'] != dose_id]
        # Check stimulants
        self.stimulants = [stim for stim in self.stimulants if stim['id'] != dose_id]
        # Reassign IDs
        all_doses = self.get_all_doses()
        for i, dose in enumerate(all_doses):
            dose['id'] = i
    
    def find_sleep_windows(self, effect_level: np.ndarray, threshold: float = None) -> List[Tuple[float, float]]:
        """Find time windows suitable for sleep (effect below threshold)"""
        if threshold is None:
            threshold = self.sleep_threshold
            
        sleep_windows = []
        in_sleep_zone = False
        start_time = None
        
        for i, effect in enumerate(effect_level):
            if effect <= threshold and not in_sleep_zone:
                in_sleep_zone = True
                start_time = self.time_points[i]  # Convert to hours for user-friendly output
            elif effect > threshold and in_sleep_zone:
                in_sleep_zone = False
                if start_time is not None:
                    sleep_windows.append((start_time, self.time_points[i]))  # Convert to hours for user-friendly output
                    start_time = None
        
        # Handle case where sleep zone extends to end of day
        if in_sleep_zone and start_time is not None:
            sleep_windows.append((start_time, 24.0))
            
        return sleep_windows
    
    def get_medication_summary(self) -> List[Dict]:
        """Get summary of all medications"""
        return self.medications.copy()
    
    def get_stimulant_summary(self) -> List[Dict]:
        """Get summary of all stimulants"""
        return self.stimulants.copy()
    
    def get_failed_doses(self) -> List[Dict]:
        """Get list of doses that failed to generate curves from last timeline generation"""
        return self.last_failed_doses.copy()
    
    def export_schedule(self, filename: str = None) -> str:
        """Export medication schedule to JSON"""
        if filename is None:
            filename = f"medication_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'medications': self.medications,
            'stimulants': self.stimulants,
            'sleep_threshold': self.sleep_threshold
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        return filename
    
    def import_schedule(self, data_or_filename):
        """Import medication schedule from JSON data or filename"""
        if isinstance(data_or_filename, str):
            # Handle filename
            with open(data_or_filename, 'r') as f:
                data = json.load(f)
        else:
            # Handle JSON data directly
            data = data_or_filename
            
        self.medications = data.get('medications', [])
        self.stimulants = data.get('stimulants', [])
        self.sleep_threshold = data.get('sleep_threshold', 0.3)
        
        # Reassign IDs
        all_doses = self.get_all_doses()
        for i, dose in enumerate(all_doses):
            dose['id'] = i
