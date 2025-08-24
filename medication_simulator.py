import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple, Optional
import json
from pk_models import concentration_curve
from saturation import combine_and_cap
# import streamlit as st  # Not needed for Dash app

# Test if concentration_curve is available
print(f"DEBUG: concentration_curve imported successfully: {concentration_curve}")

class MedicationSimulator:
    """ADHD Medication Timeline Simulator with PK-based curves and saturation"""
    
    def __init__(self):
        self.medications = []
        self.stimulants = []
        self.time_points = np.array([])  # Will be set dynamically
        self.sleep_threshold = 0.3  # Effect level below which sleep is suitable
        # Saturation parameters for combined effects
        self.emax = 1.0  # Maximum combined effect (ceiling)
        self.ec50 = 0.5  # Concentration for 50% of max effect
        self.hill_coefficient = 1.5  # Hill coefficient for saturation curve
        # Track failed doses from last timeline generation
        self.last_failed_doses = []
        # Unique ID counter for all doses
        self._next_dose_id = 0
    
    def _calculate_dynamic_window(self) -> Tuple[float, float]:
        """Calculate dynamic time window based on medication timing and effects"""
        all_doses = self.medications + self.stimulants
        
        if not all_doses:
            # Default to 24 hours if no doses
            return 0.0, 24.0
        
        # Find earliest dose time and latest effect end time
        earliest_time = float('inf')
        latest_effect_end = 0.0
        
        for dose in all_doses:
            dose_time_hours = dose['time'] / 60.0  # Convert minutes to hours
            duration_hours = dose.get('duration_min', 480) / 60.0  # Convert minutes to hours
            effect_end = dose_time_hours + duration_hours
            
            earliest_time = min(earliest_time, dose_time_hours)
            latest_effect_end = max(latest_effect_end, effect_end)
        
        # Add buffer time (2 hours before/after)
        buffer_hours = 2.0
        window_start = max(0.0, earliest_time - buffer_hours)
        window_end = latest_effect_end + buffer_hours
        
        # Ensure minimum 24h window for context
        if window_end - window_start < 24.0:
            window_end = window_start + 24.0
        
        return window_start, window_end
    
    def _update_time_points(self):
        """Update time points based on dynamic window calculation"""
        start_hour, end_hour = self._calculate_dynamic_window()
        # Create time points with 0.1 hour (6 minute) intervals
        self.time_points = np.arange(start_hour, end_hour + 0.1, 0.1)
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM time string to minutes since midnight (0-1439)"""
        hour, minute = map(int, time_str.split(':'))
        return (hour * 60 + minute) % 1440
    
    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes since midnight to HH:MM format"""
        minutes = minutes % 1440
        hour = minutes // 60
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"
    
    def _minutes_to_decimal_hours(self, minutes: int) -> float:
        """Convert minutes since midnight to decimal hours (0-24)"""
        minutes = minutes % 1440
        return minutes / 60.0
    
    def _decimal_hours_to_minutes(self, decimal_hours: float) -> int:
        """Convert decimal hours to minutes since midnight"""
        minutes = int(decimal_hours * 60)
        return minutes % 1440
    
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
        effect = np.zeros_like(self.time_points)
        
        # Debug: print dose structure
        print(f"Generating PK curve for dose: {dose}")
        
        # Get PK parameters from dose - use the stored minute values
        onset_min = dose.get('onset_min', 60)  # Already in minutes
        t_peak_min = dose.get('t_peak_min', 120)  # Already in minutes
        duration_min = dose.get('duration_min', 480)  # Already in minutes
        
        # Convert to hours for debug output
        onset_time = onset_min / 60.0
        peak_time = t_peak_min / 60.0
        duration = duration_min / 60.0
        
        print(f"PK parameters: onset={onset_time}h ({onset_min}min), peak={peak_time}h ({t_peak_min}min), duration={duration}h ({duration_min}min)")
        
        # Generate PK curve using the concentration_curve function
        try:
            print(f"Calling concentration_curve with: onset_min={onset_min}, t_peak_min={t_peak_min}, duration_min={duration_min}")
            pk_curve = concentration_curve(
                dose=1.0,  # Normalized dose (curve will be normalized to peak=1.0)
                onset_min=onset_min,
                t_peak_min=t_peak_min,
                duration_min=duration_min,
                minutes=1440,  # 24 hours
                step=6  # 6-minute intervals to match our time grid
            )
            print(f"concentration_curve returned: {len(pk_curve)} points")
            
            # Extract time points and concentrations
            pk_times = [t/60.0 for t, _ in pk_curve]  # Convert minutes to hours
            pk_concentrations = [c for _, c in pk_curve]
            
            # Scale by dose intensity
            if dose['type'] == 'medication':
                # For medications, use the calculated peak_effect from add_medication
                dose_intensity = dose.get('peak_effect', dose['dosage'] / 20.0)  # Fallback to standard calculation
            else:
                # For stimulants, use the stored peak_effect
                dose_intensity = dose.get('peak_effect', 1.0)
            
            # Debug output
            print(f"PK curve generated: {len(pk_times)} points, max concentration: {max(pk_concentrations) if pk_concentrations else 0}")
            print(f"Dose intensity: {dose_intensity}")
            print(f"Time points: {len(self.time_points)}, from {self.time_points[0]}h to {self.time_points[-1]}h")
            print(f"Dose time: {dose['time']} minutes ({dose['time']/60:.1f}h)")
            
            # Interpolate PK curve to our time grid and apply dose intensity
            print(f"Starting effect calculation loop for {len(self.time_points)} time points")
            effect_points_calculated = 0
            
            for i, t in enumerate(self.time_points):
                # Calculate time since dose
                # t is in hours (0-24), dose['time'] is in minutes (0-1439)
                # Convert t to minutes for comparison
                current_time_minutes = int(t * 60)
                
                # Calculate time since dose without midnight wrapping - allow effects to extend naturally
                if current_time_minutes >= dose['time']:
                    # Same day: time since dose
                    time_since_dose = current_time_minutes - dose['time']
                else:
                    # Next day: continue linearly instead of wrapping
                    time_since_dose = current_time_minutes + (1440 - dose['time'])
                
                # Process if time since dose is valid (allows effects to continue naturally)
                if time_since_dose >= 0:
                    # Convert to minutes for comparison with PK curve
                    time_since_dose_minutes = time_since_dose
                    
                    # Find the closest PK time point
                    # pk_curve returns (minutes, concentration) pairs
                    # Find the closest time match
                    closest_index = 0
                    min_diff = float('inf')
                    
                    for j, (pk_time_min, pk_conc) in enumerate(pk_curve):
                        diff = abs(pk_time_min - time_since_dose_minutes)
                        if diff < min_diff:
                            min_diff = diff
                            closest_index = j
                    
                    # Apply the concentration at the closest time point
                    if closest_index < len(pk_concentrations):
                        effect[i] = pk_concentrations[closest_index] * dose_intensity
                        effect_points_calculated += 1
            
            print(f"Effect calculation complete: {effect_points_calculated} points calculated")
            
            # Debug: check what effect values were generated
            max_effect = np.max(effect)
            non_zero_count = np.count_nonzero(effect)
            print(f"Generated effect curve: max={max_effect:.6f}, non-zero points={non_zero_count}/{len(effect)}")
            
            # Return the generated effect curve
            return effect
            
        except Exception as e:
            # Log the specific error for debugging
            print(f"PK curve generation failed for dose {dose.get('id', 'unknown')}: {e}")
            print(f"Dose data: {dose}")
            
            # Return zero effect instead of misleading fallback data
            # This ensures users see when something is wrong rather than fake curves
            print(f"Returning zero effect for failed dose {dose.get('id', 'unknown')}")
            return np.zeros_like(self.time_points)
    
    def _generate_fallback_curve(self, dose: Dict) -> np.ndarray:
        """Fallback curve generation if PK models fail"""
        effect = np.zeros_like(self.time_points)
        
        # Simple trapezoid curve as fallback
        onset_time = dose.get('onset_min', 60) / 60.0  # Convert minutes to hours
        peak_time = dose.get('t_peak_min', 120) / 60.0  # Convert minutes to hours
        duration = dose.get('duration_min', 480) / 60.0  # Convert minutes to hours
        peak_duration = dose.get('peak_duration_min', 60) / 60.0  # Convert minutes to hours
        
        if dose['type'] == 'medication':
            peak_effect = dose['dosage'] / 20.0
        else:
            peak_effect = dose.get('peak_effect', 1.0)
        
        fall_start = peak_time + peak_duration
        
        for i, t in enumerate(self.time_points):
            # Calculate time since dose with midnight wrapping
            dose_time_minutes = dose['time']  # Already in minutes
            current_time_minutes = self._decimal_hours_to_minutes(t)
            
            if current_time_minutes >= dose_time_minutes:
                time_since_dose = current_time_minutes - dose_time_minutes
            else:
                # Continue linearly instead of wrapping around midnight
                time_since_dose = current_time_minutes + (1440 - dose_time_minutes)
            
            # Convert to hours for comparison
            time_since_dose_hours = time_since_dose / 60.0
            
            if time_since_dose_hours >= 0:
                if time_since_dose_hours < peak_time:
                    effect[i] = (time_since_dose_hours / peak_time) * peak_effect
                elif time_since_dose_hours < fall_start:
                    effect[i] = peak_effect
                else:
                    # Allow effect to continue beyond duration with natural decay
                    if time_since_dose_hours < duration:
                        # Within original duration - use normal falloff
                        fall_progress = (time_since_dose_hours - fall_start) / (duration - fall_start)
                        fall_progress = max(0, min(1, fall_progress))
                        effect[i] = peak_effect * (1 - fall_progress)
                    else:
                        # Beyond duration - continue with natural decay
                        extended_duration = duration + (time_since_dose_hours - duration) * 0.5  # Slower decay
                        fall_progress = (time_since_dose_hours - fall_start) / (extended_duration - fall_start)
                        fall_progress = max(0, min(1, fall_progress))
                        effect[i] = peak_effect * (1 - fall_progress)
        
        return effect
    
    def generate_daily_timeline(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate combined daily effect timeline from all doses using PK curves and saturation"""
        if not self.medications and not self.stimulants:
            return self.time_points, np.zeros_like(self.time_points)
        
        # Generate individual PK curves for all doses
        individual_curves = []
        failed_doses = []
        
        for dose in self.get_all_doses():
            try:
                curve = self.generate_pk_curve(dose)

                
                if np.any(curve > 0):  # Check if curve has any effect
                    individual_curves.append(curve)
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
        
        # Combine curves using saturation model
        if len(individual_curves) == 1:
            combined_effect = individual_curves[0]
        else:
            # Convert numpy arrays to lists for saturation function
            curve_lists = [curve.tolist() for curve in individual_curves]
            combined_effect = np.array(combine_and_cap(
                curve_lists, 
                emax=self.emax, 
                ec50=self.ec50, 
                h=self.hill_coefficient
            ))
        
        print(f"Combined effect: max = {np.max(combined_effect) if len(combined_effect) > 0 else 0}")
        return self.time_points, combined_effect
    
    def get_individual_curves(self) -> List[Tuple[str, np.ndarray]]:
        """Get individual PK curves for plotting"""
        curves = []
        for dose in self.get_all_doses():
            try:
                curve = self.generate_pk_curve(dose)
                if np.any(curve > 0):  # Only include curves with actual effect
                    if dose['type'] == 'medication':
                        label = f"{dose['dosage']}mg {dose.get('medication_name', 'medication')}"
                    else:
                        label = f"{dose['quantity']}x {dose['stimulant_name']}"
                        if dose.get('component_name'):
                            label += f" ({dose['component_name']})"
                    curves.append((label, curve))
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
                # Use standard_dose_mg if available, otherwise fall back to reasonable defaults
                standard_dose_mg = medication_data.get('standard_dose_mg')
                if standard_dose_mg:
                    peak_effect = dosage / standard_dose_mg
                else:
                    # Fallback: use a reasonable default based on typical therapeutic ranges
                    # This is a temporary solution until standard_dose_mg fields are added to the data
                    peak_effect = dosage / 20.0  # Generic assumption
                
                # Store additional parameters for curve generation
                peak_duration = medication_data['peak_duration_min']
                wear_off_duration = medication_data['wear_off_min']
                
                # Get half-life data if available
                half_life_min = medication_data.get('half_life_min')
                
                # Debug: print loaded medication data
                print(f"Loaded medication data for {medication_name}: onset={onset_time:.2f}h ({medication_data['onset_min']}min), peak={peak_time:.2f}h ({medication_data['t_peak_min']}min), duration={duration:.2f}h ({medication_data['duration_min']}min), peak_effect={peak_effect:.3f}")
            else:
                raise ValueError(f"Unknown medication: {medication_name}")
        else:
            peak_duration = 1.0  # Default peak duration
            wear_off_duration = 1.0  # Default wear-off duration
        
        # Override with custom parameters if provided
        if custom_params:
            if 'onset_time_min' in custom_params:
                onset_time = custom_params['onset_time_min'] / 60.0
            if 'peak_time_min' in custom_params:
                peak_time = custom_params['peak_time_min'] / 60.0
            if 'duration_min' in custom_params:
                duration = custom_params['duration_min'] / 60.0
            if 'peak_effect' in custom_params:
                peak_effect = custom_params['peak_effect']
            # Note: peak_duration and wear_off_duration are not overridden by custom params
            # They come from the medication data to maintain consistency
        
        # Validate parameters
        if peak_time < onset_time:
            raise ValueError("peak_time must be >= onset_time")
        if duration < peak_time:
            raise ValueError("duration must be >= peak_time")
        
        medication = {
            'time': dose_minutes,  # Store as minutes since midnight
            'dosage': dosage,
            'medication_name': medication_name,
            'half_life_min': half_life_min,
            'peak_effect': peak_effect,  # Store the calculated peak effect
            # Store standardized minute values for PK curve generation
            'onset_min': int(onset_time * 60),
            't_peak_min': int(peak_time * 60),
            'duration_min': int(duration * 60),
            'peak_duration_min': int(peak_duration),
            'wear_off_min': int(wear_off_duration),
            'type': 'medication',
            'id': self._next_dose_id
        }
        
        # Increment the unique ID counter
        self._next_dose_id += 1
        
        self.medications.append(medication)
        self._update_time_points()
    
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
        
        # Use minutes directly
        onset_time = stimulant_data['onset_min'] / 60.0
        peak_time = stimulant_data['t_peak_min'] / 60.0
        duration = stimulant_data['duration_min'] / 60.0
        # peak_effect should be based on quantity, not duration
        peak_effect = quantity  # Base effect on quantity consumed
        
        # Store additional parameters for curve generation
        peak_duration = stimulant_data['peak_duration_min']
        wear_off_duration = stimulant_data['wear_off_min']
        
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
            'id': self._next_dose_id
        }
        
        # Increment the unique ID counter
        self._next_dose_id += 1
        
        self.stimulants.append(stimulant)
        self._update_time_points()
    
    def get_next_dose_id(self) -> int:
        """Get the next unique dose ID and increment the counter"""
        current_id = self._next_dose_id
        self._next_dose_id += 1
        return current_id
    
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
        # Reset the ID counter when clearing all doses
        self._next_dose_id = 0
    
    def clear_all_painkillers(self):
        """Clear all painkillers"""
        if hasattr(self, 'painkillers'):
            self.painkillers = []
        # Note: We don't reset the ID counter here as it's shared with medications/stimulants
    
    def remove_dose(self, dose_id: int):
        """Remove a dose by ID"""
        import traceback
        print(f"DEBUG: remove_dose called with dose_id: {dose_id}")
        print(f"DEBUG: Stack trace:")
        traceback.print_stack()
        
        # Check medications first
        self.medications = [med for med in self.medications if med['id'] != dose_id]
        # Check stimulants
        self.stimulants = [stim for stim in self.stimulants if stim['id'] != dose_id]
        # Note: We don't reassign IDs to maintain consistency with the timeline generation
        # The ID counter will continue to increment for new doses
    
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
                start_time = self.time_points[i]
            elif effect > threshold and in_sleep_zone:
                in_sleep_zone = False
                if start_time is not None:
                    sleep_windows.append((start_time, self.time_points[i]))
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
        
        # Update the ID counter to be higher than any existing ID
        if self.medications or self.stimulants:
            max_id = max(
                max((med.get('id', 0) for med in self.medications), default=0),
                max((stim.get('id', 0) for stim in self.stimulants), default=0)
            )
            self._next_dose_id = max_id + 1
        else:
            self._next_dose_id = 0
