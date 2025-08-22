# pk_models.py
import math
from typing import Sequence, Tuple

def pk_one_compartment(dose: float, ka_per_min: float, ke_per_min: float, t_min: float, V: float = 1.0) -> float:
    """Concentration at time t_min (minutes) for oral dose with first-order absorption (ka_per_min) and elimination (ke_per_min) in per-minute units."""
    if abs(ka_per_min - ke_per_min) < 1e-9:
        # limit case ka ~ ke
        return dose / V * (ka_per_min * t_min) * math.exp(-ke_per_min * t_min)
    return (dose / V) * (ka_per_min / (ka_per_min - ke_per_min)) * (math.exp(-ke_per_min * t_min) - math.exp(-ka_per_min * t_min))

def fit_ka_ke_from_timings(onset_min: float, t_peak_min: float, duration_min: float) -> Tuple[float, float]:
    """
    Calculate ka and ke to give realistic wear-off curve.
    All time units are in minutes, returns ka and ke in per-minute units.
    """
    # Calculate ke to give realistic wear-off (15% of peak at end of duration)
    target_end_conc_ratio = 0.15
    time_from_peak = duration_min - t_peak_min
    if time_from_peak > 0:
        ke_per_min = -math.log(target_end_conc_ratio) / time_from_peak
    else:
        ke_per_min = 0.1 / 60.0  # fallback, per min

    ke = ke_per_min * 60  # convert to per hour

    # crude ka guess to hit peak near t_peak
    ka = max(ke * 3.0, 0.2)  # Ensure ka is at least 3x ke
    for _ in range(40):
        tpk = math.log(ka/ke) / (ka - ke)
        err = tpk - (t_peak_min / 60.0)
        ka -= 0.5 * err
        ka = max(ke * 2.5, 0.05)  # Ensure ka is always at least 2.5x ke

    # Convert back to per-minute units for consistency with rest of code
    ka_per_min = ka / 60
    
    # Final safety check - ensure ka is significantly larger than ke
    if ka_per_min <= ke_per_min * 1.5:
        ka_per_min = ke_per_min * 2.0
    
    return ka_per_min, ke_per_min

def suggest_lag_model(onset_min: float, medication_type: str = None) -> str:
    """
    Suggest appropriate lag time model based on drug characteristics.
    
    Args:
        onset_min: Onset time in minutes
        medication_type: Type of medication (e.g., "immediate_release", "extended_release", "sublingual")
    
    Returns:
        Suggested lag model: "sigmoid", "linear", or "exponential"
    """
    if medication_type:
        medication_type = medication_type.lower()
        
        if "sublingual" in medication_type or "buccal" in medication_type:
            return "exponential"  # Very rapid onset, exponential transition
        elif "immediate" in medication_type or "ir" in medication_type:
            return "sigmoid"  # Standard immediate release, smooth transition
        elif "extended" in medication_type or "xr" in medication_type or "er" in medication_type:
            return "linear"  # Extended release, gradual linear transition
        elif "transdermal" in medication_type or "patch" in medication_type:
            return "exponential"  # Very gradual onset, exponential transition
    
    # Default based on onset time
    if onset_min < 15.0:
        return "exponential"  # Very fast onset
    elif onset_min < 30.0:
        return "sigmoid"  # Fast onset
    elif onset_min < 60.0:
        return "linear"  # Moderate onset
    else:
        return "exponential"  # Slow onset, gradual transition

def concentration_curve(dose: float, onset_min: float, t_peak_min: float, duration_min: float, minutes=1440, step=5, lag_model="sigmoid", start_time_min=0) -> Sequence[Tuple[float,float]]:
    """
    Generate concentration curve with all time units in minutes.
    
    Args:
        dose: Dose amount
        onset_min: Onset time in minutes (lag time before absorption begins)
        t_peak_min: Time to peak in minutes  
        duration_min: Total duration in minutes
        minutes: Total simulation time in minutes (default 1440 = 24 hours)
        step: Time step in minutes (default 5)
        lag_model: Lag time model type ("sigmoid", "linear", "exponential")
        start_time_min: Start time in minutes (default 0, useful for aligning with dose time)
    
    Returns:
        List of (time_minutes, concentration) tuples with actual concentration values
        (not normalized to peak=1.0, preserving dose-response relationships)
    """
    ka_per_min, ke_per_min = fit_ka_ke_from_timings(onset_min, t_peak_min, duration_min)
    
    # Debug output
    print(f"PK parameters: ka={ka_per_min:.6f}/min, ke={ke_per_min:.6f}/min, onset={onset_min:.1f}min, t_peak={t_peak_min:.1f}min, duration={duration_min:.1f}min")
    
    # Calculate appropriate lag transition width based on drug characteristics
    # Faster-acting drugs (shorter onset) should have narrower transitions
    if onset_min < 15.0:  # Very fast onset (e.g., sublingual)
        lag_transition_width = 5.0
    elif onset_min < 30.0:  # Fast onset (e.g., immediate release)
        lag_transition_width = 10.0
    elif onset_min < 60.0:  # Moderate onset (e.g., some XR formulations)
        lag_transition_width = 15.0
    else:  # Slow onset (e.g., some extended release)
        lag_transition_width = 20.0
    
    # Extend simulation time to show natural decay beyond duration
    # This prevents artificial cutoff and shows realistic wear-off
    extended_minutes = max(minutes, start_time_min + onset_min + duration_min + 240)  # Add 4 hours beyond duration
    
    xs, ys = [], []
    for m in range(start_time_min, extended_minutes + 1, step):
        # Calculate time since onset (lag time)
        time_since_onset = max(0, m - start_time_min - onset_min)
        
        if time_since_onset > 0:
            # Apply smooth lag time model instead of hard cutoff
            # This better reflects real PK behavior where absorption gradually increases
            
            # Calculate lag factor based on chosen model
            if lag_model == "sigmoid":
                # Smooth sigmoid transition (most realistic for most drugs)
                if time_since_onset < lag_transition_width:
                    lag_factor = 0.5 * (1 + math.tanh((time_since_onset - lag_transition_width/2) / (lag_transition_width/6)))
                else:
                    lag_factor = 1.0
                    
            elif lag_model == "linear":
                # Linear transition (simpler, good for some formulations)
                if time_since_onset < lag_transition_width:
                    lag_factor = time_since_onset / lag_transition_width
                else:
                    lag_factor = 1.0
                    
            elif lag_model == "exponential":
                # Exponential transition (good for drugs with gradual absorption onset)
                if time_since_onset < lag_transition_width:
                    lag_factor = 1 - math.exp(-3 * time_since_onset / lag_transition_width)
                else:
                    lag_factor = 1.0
                    
            else:
                # Default to sigmoid
                if time_since_onset < lag_transition_width:
                    lag_factor = 0.5 * (1 + math.tanh((time_since_onset - lag_transition_width/2) / (lag_transition_width/6)))
                else:
                    lag_factor = 1.0
            
            # Calculate concentration with lag factor applied
            # Let the PK model naturally decay - no artificial cutoff
            c = pk_one_compartment(dose, ka_per_min, ke_per_min, time_since_onset) * lag_factor
        else:
            # Before onset: no absorption
            c = 0.0
        
        xs.append(m); ys.append(c)
    
    # Debug output
    max_c = max(ys) if ys else 0
    print(f"Generated {len(ys)} points, max concentration: {max_c:.6f}")
    print(f"Lag model: {lag_model}, transition width: {lag_transition_width:.1f} minutes")
    print(f"Time range: {start_time_min:.1f} to {extended_minutes:.1f} minutes")
    
    # Return actual concentration values - let dose-response scaling handle effect levels
    # This preserves the dose-response relationship for proper PK modeling
    return list(zip(xs, ys))
