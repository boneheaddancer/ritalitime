import math
from pk_models import concentration_curve

def approx_equal(a,b,tol=0.15):
    return abs(a-b) <= tol*max(1.0,abs(b))

def find_peak(xs_ys):
    xs, ys = zip(*xs_ys)
    i = max(range(len(ys)), key=lambda k: ys[k])
    return xs[i], ys[i]

def test_paracetamol_ir_shape():
    xs_ys = concentration_curve(dose=1, onset_min=20, t_peak_min=60, duration_min=300)
    tpk, peak = find_peak(xs_ys)
    assert 45 <= tpk <= 90
    assert math.isclose(peak, 1.0, rel_tol=1e-6)

def test_panodil_mr_is_flatter_and_later():
    mr = concentration_curve(dose=1, onset_min=45, t_peak_min=240, duration_min=480)
    ir = concentration_curve(dose=1, onset_min=20, t_peak_min=60, duration_min=300)
    # MR peaks later:
    tpk_mr, _ = find_peak(mr)
    tpk_ir, _  = find_peak(ir)
    assert tpk_mr > tpk_ir + 90
    # MR has broader half-peak window:
    def width_at_half(curve):
        _, ys = zip(*curve)
        half = 0.5
        idx = [i for i, y in enumerate(ys) if y >= half]
        return (idx[-1] - idx[0])  # in steps, not minutes
    assert width_at_half(mr) > width_at_half(ir)
