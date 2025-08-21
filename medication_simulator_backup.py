import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple, Optional
import json

class MedicationSimulator:
    """ADHD Medication Timeline Simulator"""
    
    def __init__(self):
        self.medications = []
        self.time_points = np.arange(0, 24, 0.1)  # 10-minute intervals
        self.sleep_threshold = 0.3  # Effect level below which sleep is suitable
        
    def add_medication(self, dose_time: str, dosage: float, 
                       onset_time: float = 1.0, peak_time: float = 2.0, 
                       duration: float = 8.0, peak_effect: float = 1.0):
        """
        Add a medication dose to the simulation
        
        Args:
            dose_time: Time in HH:MM format
            dosage: Dose in mg
            onset_time: Time to onset in hours
            peak_time: Time to peak effect in hours
            duration: Total duration in hours
            peak_effect: Peak effect level (0-1)
        """
        # Parse time string
        hour, minute = map(int, dose_time.split(':'))
        dose_hour = hour + minute / 60.0
        
        medication = {
            'time': dose_hour,
            'dosage': dosage,
            'onset_time': onset_time,
            'peak_time': peak_time,
            'duration': duration,
            'peak_effect': peak_effect,
            'id': len(self.medications)
        }
        
        self.medications.append(medication)
        
    def generate_effect_curve(self, medication: Dict) -> np.ndarray:
        """Generate a bell-shaped effect curve for a single medication dose"""
        effect = np.zeros_like(self.time_points)
        
        # Create trapezoid curve: rise → plateau → fall
        rise_time = medication['onset_time']
        peak_time = medication['peak_time']
        
        # Ensure proper curve distribution
        # Plateau should be at least 1 hour, fall phase should be at least 1 hour
        min_plateau = 1.0
        min_fall = 1.0
        
        # Calculate available time for plateau and fall
        available_time = medication['duration'] - rise_time
        
        if available_time >= (min_plateau + min_fall):
            # We have enough time for proper distribution
            fall_start = rise_time + min_plateau
            fall_end = medication['duration']
        else:
            # Not enough time, adjust fall start to ensure minimum fall duration
            fall_start = medication['duration'] - min_fall
            if fall_start <= rise_time:
                fall_start = rise_time + 0.5  # At least 30 min plateau
                fall_end = medication['duration']
            else:
                fall_end = medication['duration']
        
        # Calculate time since dose for each time point
        for i, t in enumerate(self.time_points):
            # Calculate time since dose, handling midnight wrapping
            if t >= medication['time']:
                # Same day
                time_since_dose = t - medication['time']
            else:
                # Next day (wrapped around midnight)
                time_since_dose = (24 - medication['time']) + t
            
            # Only apply effect within duration window (with small tolerance for rounding)
            if 0 <= time_since_dose < (medication['duration'] + 0.1):
                if time_since_dose < rise_time:
                    # Rise phase (0 to peak)
                    effect[i] = (time_since_dose / rise_time) * medication['peak_effect']
                elif time_since_dose < fall_start:
                    # Plateau phase
                    effect[i] = medication['peak_effect']
                else:
                    # Fall phase (peak to 0)
                    fall_progress = (time_since_dose - fall_start) / (fall_end - fall_start)
                    # Clamp fall progress to prevent negative values
                    fall_progress = max(0, min(1, fall_progress))
                    effect[i] = medication['peak_effect'] * (1 - fall_progress)
        
        # Apply dosage scaling - make it more proportional
        # Base effect is 1.0 for 20mg, but can scale up/down
        dosage_factor = medication['dosage'] / 20.0
        effect *= dosage_factor
        
        return effect
    
    def generate_daily_timeline(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate combined daily effect timeline from all medications"""
        if not self.medications:
            return self.time_points, np.zeros_like(self.time_points)
        
        # Generate individual curves
        individual_curves = []
        for med in self.medications:
            curve = self.generate_effect_curve(med)
            individual_curves.append(curve)
        
        # Combine curves (additive effect)
        combined_effect = np.sum(individual_curves, axis=0)
        
        # Don't normalize - keep actual effect levels
        # This allows multiple doses to show true additive effects
        # The effect can exceed 1.0 when multiple doses overlap
        
        return self.time_points, combined_effect
    
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
    
    def remove_medication(self, medication_id: int):
        """Remove a medication by ID"""
        self.medications = [med for med in self.medications if med['id'] != medication_id]
        # Reassign IDs
        for i, med in enumerate(self.medications):
            med['id'] = i
    
    def clear_medications(self):
        """Clear all medications"""
        self.medications = []
    
    def export_schedule(self, filename: str = None) -> str:
        """Export medication schedule to JSON"""
        if filename is None:
            filename = f"medication_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'medications': self.medications,
            'sleep_threshold': self.sleep_threshold
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        return filename
    
    def import_schedule(self, filename: str):
        """Import medication schedule from JSON"""
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.medications = data.get('medications', [])
        self.sleep_threshold = data.get('sleep_threshold', 0.3)
        
        # Reassign IDs
        for i, med in enumerate(self.medications):
            med['id'] = i
