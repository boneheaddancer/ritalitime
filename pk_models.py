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
    xs, ys = [], []
    for m in range(0, minutes+1, step):
        c = pk_one_compartment(dose, ka, ke, m/60.0)
        # Hard onset gate so the curve doesn't pretend to act before onset:
        c = 0.0 if m < onset_min else c
        xs.append(m); ys.append(c)
    # Normalize so single-dose peak = 1.0 (makes visualization simple)
    peak = max(ys) or 1.0
    ys = [y/peak for y in ys]
    return list(zip(xs, ys))
