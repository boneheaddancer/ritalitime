# pk_models.py
import math
from typing import Sequence, Tuple

def pk_one_compartment(dose: float, ka: float, ke: float, t: float, V: float = 1.0) -> float:
    """Concentration at time t for oral dose with first-order absorption (ka) and elimination (ke)."""
    if abs(ka - ke) < 1e-9:
        # limit case ka ~ ke
        return dose / V * (ka * t) * math.exp(-ke * t)
    return (dose / V) * (ka / (ka - ke)) * (math.exp(-ke * t) - math.exp(-ka * t))

def fit_ka_ke_from_timings(onset_min: float, t_peak_min: float, duration_min: float) -> Tuple[float, float]:
    """
    Heuristic: pick ke from total duration, then choose ka so t_peak ~ target.
    - ke ~ ln(100) / duration (go ~two-log decay to near-zero)
    - solve for ka s.t. dC/dt=0 peak near t_peak  -> peak ~ ln(ka/ke)/(ka-ke)
    We'll iterate a tiny bit to get a decent ka.
    """
    # elimination rate: about two decades drop across duration
    ke = math.log(100.0) / (duration_min / 60.0)  # per hour
    target_t_peak_h = t_peak_min / 60.0
    ka = max(ke * 1.2, 0.2)  # start > ke
    for _ in range(40):
        # peak time for this model:
        tpk = math.log(ka/ke) / (ka - ke)
        err = tpk - target_t_peak_h
        ka -= 0.5 * err  # crude newton-ish step; good enough for UI
        ka = max(ke * 1.05, 0.05)
    return ka, ke

def concentration_curve(dose: float, onset_min: float, t_peak_min: float, duration_min: float, minutes=1440, step=5) -> Sequence[Tuple[float,float]]:
    ka, ke = fit_ka_ke_from_timings(onset_min, t_peak_min, duration_min)
    
    # Debug output
    print(f"PK parameters: ka={ka:.4f}, ke={ke:.4f}, onset={onset_min:.1f}min, t_peak={t_peak_min:.1f}min, duration={duration_min:.1f}min")
    
    xs, ys = [], []
    for m in range(0, minutes+1, step):
        c = pk_one_compartment(dose, ka, ke, m/60.0)
        # Smooth onset transition instead of hard cutoff
        if m < onset_min:
            # Use a smoother sigmoid-like ramp to avoid sharp edges
            # This creates a more gradual, natural transition
            ramp_factor = m / onset_min if onset_min > 0 else 1.0
            # Apply sigmoid-like smoothing: 3x^2 - 2x^3 for smoother transition
            smooth_ramp = 3 * ramp_factor**2 - 2 * ramp_factor**3
            c = c * smooth_ramp
        xs.append(m); ys.append(c)
    
    # Debug output
    max_c = max(ys) if ys else 0
    print(f"Generated {len(ys)} points, max concentration: {max_c:.6f}")
    
    # Normalize so single-dose peak = 1.0 (makes visualization simple)
    peak = max_c or 1.0
    ys = [y/peak for y in ys]
    return list(zip(xs, ys))
