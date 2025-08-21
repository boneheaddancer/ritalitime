import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple, Optional
import json

class MedicationSimulator:
    """ADHD Medication Timeline Simulator with Emax/Hill pharmacodynamic model"""
    
    def __init__(self):
        self.medications = []
        self.stimulants = []
        self.time_points = np.arange(0, 24, 0.1)  # 10-minute intervals
        self.sleep_threshold = 0.3  # Effect level below which sleep is suitable
        # Generic Hill saturation parameters for combined effects
        self.emax = 1.0  # Maximum combined effect (ceiling)
        self.hill_coefficient = 1.0  # Hill coefficient for saturation curve
        self.saturation_threshold = 0.8  # Effect level where saturation begins
    
    def apply_hill_saturation(self, combined_effect: np.ndarray) -> np.ndarray:
        """
        Apply Hill saturation curve to combined effects
        This prevents unlimited additive effects while preserving individual dose timing
        """
        # Normalize to saturation threshold, then apply Hill curve
        normalized_effect = combined_effect / self.saturation_threshold
        
        # Apply Hill saturation: E = Emax * C^h / (1 + C^h)
        # This flattens the curve as effects approach the ceiling
        effect_h = normalized_effect ** self.hill_coefficient
        saturated_effect = self.emax * effect_h / (1 + effect_h)
        
        return saturated_effect
    

    
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
        # Parse time string
        hour, minute = map(int, dose_time.split(':'))
        dose_hour = hour + minute / 60.0
        
        # If medication_name is provided, load from prescription database
        if medication_name:
            medication_data = self._get_prescription_data(medication_name)
            if medication_data:
                # Convert minutes to hours
                onset_time = medication_data['onset_min'] / 60.0
                peak_time = medication_data['peak_time_min'] / 60.0
                duration = medication_data['duration_min'] / 60.0
                peak_effect = medication_data['peak_duration_min'] / 60.0  # Use peak_duration as effect level
                
                # Store additional parameters for curve generation
                peak_duration = medication_data['peak_duration_min'] / 60.0
                wear_off_duration = medication_data['wear_off_duration_min'] / 60.0
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
            if 'peak_duration' in custom_params:
                peak_duration = custom_params['peak_duration']
            if 'wear_off_duration' in custom_params:
                wear_off_duration = custom_params['wear_off_duration']
        
        # Validate parameters
        if peak_time < onset_time:
            raise ValueError("peak_time must be >= onset_time")
        if duration < peak_time:
            raise ValueError("duration must be >= peak_time")
        
        medication = {
            'time': dose_hour,
            'dosage': dosage,
            'medication_name': medication_name,
            'onset_time': onset_time,
            'peak_time': peak_time,
            'duration': duration,
            'peak_effect': peak_effect,
            'peak_duration': peak_duration,
            'wear_off_duration': wear_off_duration,
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
        # Parse time string
        hour, minute = map(int, dose_time.split(':'))
        dose_hour = hour + minute / 60.0
        
        # Load stimulant data
        stimulant_data = self._get_stimulant_data(stimulant_name, component_name)
        
        if not stimulant_data:
            raise ValueError(f"Unknown stimulant: {stimulant_name}" + (f" component: {component_name}" if component_name else ""))
        
        # Convert minutes to hours
        onset_time = stimulant_data['onset_min'] / 60.0
        peak_time = stimulant_data['peak_time_min'] / 60.0
        duration = stimulant_data['duration_min'] / 60.0
        peak_effect = stimulant_data['peak_duration_min'] / 60.0  # Use peak_duration as effect level
        
        # Store additional parameters for curve generation
        peak_duration = stimulant_data['peak_duration_min'] / 60.0
        wear_off_duration = stimulant_data['wear_off_duration_min'] / 60.0
        
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
            if 'peak_duration' in custom_params:
                peak_duration = custom_params['peak_duration']
            if 'wear_off_duration' in custom_params:
                wear_off_duration = custom_params['wear_off_duration']
        
        # Scale effect by quantity
        peak_effect *= quantity
        
        stimulant = {
            'time': dose_hour,
            'stimulant_name': stimulant_name,
            'component_name': component_name,
            'quantity': quantity,
            'onset_time': onset_time,
            'peak_time': peak_time,
            'duration': duration,
            'peak_effect': peak_effect,
            'peak_duration': peak_duration,
            'wear_off_duration': wear_off_duration,
            'type': 'stimulant',
            'id': len(self.medications) + len(self.stimulants)
        }
        
        self.stimulants.append(stimulant)
    
    def _get_stimulant_data(self, stimulant_name: str, component_name: str = None) -> Optional[Dict]:
        """Get stimulant data from the JSON file"""
        try:
            with open('meds_stimulants.json', 'r') as f:
                data = json.load(f)
            
            stimulants = data.get('common_stimulants', {})
            
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
            
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def _get_prescription_data(self, medication_name: str) -> Optional[Dict]:
        """Get prescription medication data from the JSON file"""
        try:
            with open('meds_stimulants.json', 'r') as f:
                data = json.load(f)
            
            medications = data.get('prescription_stimulants', {})
            
            if medication_name not in medications:
                return None
            
            return medications[medication_name]
            
        except (FileNotFoundError, json.JSONDecodeError):
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
    
    def generate_effect_curve(self, dose: Dict) -> np.ndarray:
        """Generate a bell-shaped effect curve for a single dose"""
        effect = np.zeros_like(self.time_points)
        
        # Create trapezoid curve: rise → plateau → fall
        onset_time = dose['onset_time']      # Time from dose to onset
        peak_time = dose['peak_time']        # Time from dose to peak effect
        duration = dose['duration']          # Total duration
        
        # Calculate curve phases using correct parameters
        # Rise phase: 0 to peak_time (linear increase)
        # Plateau phase: peak_time to (peak_time + peak_duration) (maintain peak effect)
        # Fall phase: (peak_time + peak_duration) to duration (linear decrease)
        
        # Calculate fall start based on peak duration (starts at peak_time, not onset_time)
        fall_start = peak_time + dose.get('peak_duration', 1.0)  # Default to 1 hour if not specified
        
        # Normalize effect per dose (1.0 = full effect of that dose)
        if dose['type'] == 'medication':
            # For medications, normalize to dosage (20mg = 1.0 effect)
            peak_effect = dose['dosage'] / 20.0
        else:
            # For stimulants, use the stored peak_effect (already scaled by quantity)
            peak_effect = dose['peak_effect']
        
        # Calculate time since dose for each time point
        for i, t in enumerate(self.time_points):
            # Calculate time since dose, handling midnight wrapping
            if t >= dose['time']:
                # Same day
                time_since_dose = t - dose['time']
            else:
                # Next day (wrapped around midnight)
                time_since_dose = (24 - dose['time']) + t
            
            # Only apply effect within duration window (with small tolerance for rounding)
            if 0 <= time_since_dose < (duration + 0.1):
                if time_since_dose < peak_time:
                    # Rise phase (0 to peak): linear increase from 0 to peak_effect
                    effect[i] = (time_since_dose / peak_time) * peak_effect
                elif time_since_dose < fall_start:
                    # Plateau phase: maintain peak effect
                    effect[i] = peak_effect
                else:
                    # Fall phase (peak to 0): linear decrease from peak_effect to 0
                    fall_progress = (time_since_dose - fall_start) / (duration - fall_start)
                    # Clamp fall progress to prevent negative values
                    fall_progress = max(0, min(1, fall_progress))
                    effect[i] = peak_effect * (1 - fall_progress)
        
        return effect
    
    def generate_daily_timeline(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate combined daily effect timeline from all doses"""
        if not self.medications and not self.stimulants:
            return self.time_points, np.zeros_like(self.time_points)
        
        # Generate individual curves for all doses
        individual_curves = []
        for dose in self.get_all_doses():
            curve = self.generate_effect_curve(dose)
            individual_curves.append(curve)
        
        # Combine curves (additive effect)
        combined_effect = np.sum(individual_curves, axis=0)
        
        # Apply Hill saturation to prevent unlimited additive effects
        combined_effect = self.apply_hill_saturation(combined_effect)
        
        return self.time_points, combined_effect
    
    def get_individual_curves(self) -> List[Tuple[str, np.ndarray]]:
        """Get individual effect curves for plotting"""
        curves = []
        for dose in self.get_all_doses():
            curve = self.generate_effect_curve(dose)
            if dose['type'] == 'medication':
                label = f"{dose['dosage']}mg {dose.get('medication_name', 'medication')}"
            else:
                label = f"{dose['quantity']}x {dose['stimulant_name']}"
                if dose.get('component_name'):
                    label += f" ({dose['component_name']})"
            curves.append((label, curve))
        return curves
    
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
