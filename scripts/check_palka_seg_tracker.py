"""Assert-based self-check for palka_seg_tracker."""
from src.utils.palka_seg_tracker import (
    PalkaSegTracker,
    ang_diff_abs,
    roi_from_stick,
    point_in_roi,
)
import numpy as np


def _main() -> None:
    assert abs(ang_diff_abs(10, 350) - 20) < 1e-6
    poly = np.array([[10.0, 10.0], [30.0, 10.0], [30.0, 110.0], [10.0, 110.0]], dtype=np.float32)
    roi = roi_from_stick(poly, 200, 200, pad=0.0)
    assert len(roi) == 4
    assert point_in_roi(20, 60, 200, 200, roi)

    tr = PalkaSegTracker(hold_need_sec=0.3, ang_need_sec=0.3, ang_thresh_deg=6.0)
    # resting stick
    contour = [(20.0, 20.0), (40.0, 20.0), (40.0, 120.0), (20.0, 120.0)]
    u1 = tr.update(contour, 200, 200, 0.1)
    assert u1 is not None and u1.roi is not None and len(u1.roi) >= 3
    assert u1.e_in_roi is True
    # move E far outside for long enough
    pressed = [(120.0, 20.0), (140.0, 20.0), (140.0, 120.0), (120.0, 120.0)]
    fired = False
    for _ in range(10):
        u = tr.update(pressed, 200, 200, 0.1)
        assert u is not None
        if u.event_e:
            fired = True
            break
    assert fired, "E-out event should fire after hold"
    print("palka_seg_tracker ok")


if __name__ == "__main__":
    _main()
