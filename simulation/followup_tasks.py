"""Additional Q8 maneuvers and contact-based evaluation for their held-out replays."""
import numpy as np

NAMES = ("lift_FR", "lift_RL", "lift_RR", "roll_step_v2", "two_stage_step_v2", "controlled_descent")
TAGS = (6, 7, 8, 9, 10, 11)
LIFT_BOUNDS = [(-12, 12), (.60, 1.0), (18, 27), (-7, 7), (-4, 4), (-4, 4)]
BOUNDS = np.array([LIFT_BOUNDS] * 3 + [
    [(.24,.48), (13,29), (.04,.18), (.04,.18), (-.06,.06), (-10,10)],
    [(.23,.52), (.025,.15), (.025,.15), (.045,.17), (.045,.19), (10,22)],
    [(.25,.47), (0,18), (-.045,.08), (.04,.18), (-3,3), (0,.50)]], dtype=float)

def seeds(prior):
    roll = prior["roll_step"]
    speed, lead, _, peak, duration, _ = prior["two_stage_step"]
    return np.clip(np.array([prior["lift_FL"]] * 3 + [
        [roll[0], roll[1], roll[2], roll[2], roll[4], roll[5]],
        [speed, lead, lead, duration, duration, peak],
        [.35,7,.025,.10,.5,.20]]), BOUNDS[:,:,0], BOUNDS[:,:,1])

def assess(trace, tag, height, base_assess):
    if tag in (6, 7, 8):
        corner = tag - 5
        order = np.arange(32)
        for offset in (0, 4, 8, 13, 17):
            order[offset:offset+4] = offset + (np.arange(4) ^ corner)
        stats = base_assess(trace[:,order], 1, height)
        stats["target_wheel"] = ("FL", "FR", "RL", "RR")[corner]
        stats["held_wheel_clearance_mm"] = stats.pop("hold_FL_clearance_mm")
        return stats
    if tag in (9, 10):
        stats = base_assess(trace, 3 if tag == 9 else 5, height)
        if tag == 9:
            x, z = trace[:,17:21], trace[:,13:17]
            unloaded = (trace[:,:4] + trace[:,4:8] + trace[:,8:12]) < 1.
            near = (x > .335) & (x <= .381) & unloaded
            margins = np.where(near, z - 1000*height, -1000.).max(axis=0)
            stats["unloaded_edge_margin_mm"] = [None if m <= -999 else float(m) for m in margins]
            bounded = np.clip(margins, -12, 6)
            stats["score"] += float(.75*bounded.min() + .45*bounded.mean())
        stats["score"] -= 22*max(0., stats["closure_mm"]-.50) + .035*stats["peak_tyre_riser_contact_N"]
        return stats

    # While moving down, simultaneous loss of two axles is unacceptable.
    t = np.arange(len(trace)) * .002
    active, last = t >= .20, t >= 3.65
    top, floor = trace[:,4:8], trace[:,:4]
    support = top + floor
    started = float(np.all(top[(t >= .14) & (t < .19)] > 1, axis=1).mean())
    ended = float(np.all(floor[last] > 1, axis=1).mean())
    min_supports = int(((support[active] > 1).sum(axis=1)).min())
    peak = float(support[active].max())
    hull, gap, tilt = (float(trace[active,i].max()) for i in (12,26,21))
    speed = float(np.linalg.norm(trace[last][:,[23,30,31]], axis=1).max())
    stable = speed < .10 and trace[last,21].max() <= 5 and np.ptp(trace[last,21]) < 1.
    rear = float(trace[last,19:21].min())
    passed = started > .95 and ended > .95 and min_supports >= 2 and rear >= .43 and stable and gap < .8 and hull < 2 and tilt <= 8
    score = (25*ended + 15*started + 5*min_supports + 42*np.clip(rear-.38,-.5,.12)
             - .20*peak - 22*max(gap-.5,0) - max(tilt-4,0) - hull - 16*speed)
    return dict(passed=bool(passed), score=float(score+30*passed), step_height_mm=height*1000,
                start_four_on_top_fraction=started, end_four_on_floor_fraction=ended,
                min_supporting_wheels=min_supports, peak_single_wheel_normal_N=peak,
                peak_structure_contact_N=hull, closure_mm=gap, max_tilt_deg=tilt,
                end_speed_mps=speed, end_stable=bool(stable), minimum_final_rear_x_m=rear,
                hip_peak_Nm=float(trace[active,25].max()))
