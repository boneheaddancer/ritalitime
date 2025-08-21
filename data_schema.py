# data_schema.py
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import json

@dataclass
class MedPK:
    name: str
    # Semantics:
    # onset_min: first noticeable effect
    # t_peak_min: time *until* peak (Tmax)
    # peak_duration_min: how long the top "flat" region roughly lasts
    # duration_min: total therapeutic window from onset to near-zero
    # wear_off_min: time from end of peak until effect ~0
    onset_min: int
    t_peak_min: int
    peak_duration_min: int
    duration_min: int
    wear_off_min: int
    # Optional visualization knobs
    intensity_peak: Optional[float] = None
    intensity_avg: Optional[float] = None
    # Formulation hint
    formulation: Optional[str] = None  # "IR", "XR", "MR"

REQUIRED = {"onset_min","t_peak_min","peak_duration_min","duration_min","wear_off_min"}

def validate_entry(name: str, d: Dict[str, Any]) -> MedPK:
    missing = REQUIRED.difference(d)
    if missing:
        raise ValueError(f"{name}: missing fields: {sorted(missing)}")
    # Basic sanity checks
    if d["t_peak_min"] <= 0 or d["duration_min"] <= 0:
        raise ValueError(f"{name}: t_peak_min and duration_min must be > 0")
    if d["t_peak_min"] > d["duration_min"]:
        raise ValueError(f"{name}: t_peak_min cannot exceed duration_min")
    return MedPK(
        name=name,
        onset_min=int(d["onset_min"]),
        t_peak_min=int(d["t_peak_min"]),
        peak_duration_min=int(d["peak_duration_min"]),
        duration_min=int(d["duration_min"]),
        wear_off_min=int(d["wear_off_min"]),
        intensity_peak=d.get("intensity_peak"),
        intensity_avg=d.get("intensity_avg"),
        formulation=d.get("formulation"),
    )

def load_med_file(path: str) -> List[MedPK]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    meds = []
    for name, d in raw.items():
        meds.append(validate_entry(name, d))
    return meds
