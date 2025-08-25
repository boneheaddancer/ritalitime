from typing import List, Optional
import math

def hill_emax(total_c: float, emax: float = 1.0, ec50: float = 0.5, h: float = 1.5) -> float:
    """Hill (Emax) model: nonlinear saturation of concentration-effect relationship."""
    return emax * (total_c**h) / (ec50**h + total_c**h)

def combine_and_cap(
    component_curves: List[List[float]],
    doses: Optional[List[float]] = None,
    normalized: bool = False,
    emax: float = 1.0,
    ec50: float = 0.5,
    h: float = 1.5
) -> List[float]:
    """
    Combine multiple component concentration curves and apply saturation.
    
    Args:
        component_curves: list of curves (each curve = list of floats)
        doses: optional list of dose multipliers (only used if normalized=True)
        normalized: if True, curves are assumed normalized (peak=1) and will be scaled by doses.
                    if False, curves are assumed absolute concentrations already.
        emax, ec50, h: Hill parameters.
    """
    if normalized:
        if doses is None or len(doses) != len(component_curves):
            raise ValueError("When normalized=True, you must provide a matching 'doses' list.")
        # scale normalized curves by dose
        scaled_curves = [[y * d for y in curve] for curve, d in zip(component_curves, doses)]
    else:
        # already absolute concentrations
        scaled_curves = component_curves
    
    # sum across all curves
    totals = [sum(cs) for cs in zip(*scaled_curves)]
    
    # apply Hill saturation
    capped = [hill_emax(c, emax, ec50, h) for c in totals]
    return capped
