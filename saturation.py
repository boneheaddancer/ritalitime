# saturation.py
from typing import List
import math

def hill_emax(total_c: float, emax: float = 1.0, ec50: float = 0.5, h: float = 1.5) -> float:
    return emax * (total_c**h) / (ec50**h + total_c**h)

def combine_and_cap(component_curves: List[List[float]], emax=1.0, ec50=0.5, h=1.5) -> List[float]:
    # assume each component curve is normalized (peak=1 for its own dose)
    # sum concentrations first, then cap:
    totals = [sum(cs) for cs in zip(*component_curves)]
    capped = [hill_emax(c, emax, ec50, h) for c in totals]
    return capped
