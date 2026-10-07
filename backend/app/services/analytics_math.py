from math import ceil


def recovery_plan(attended: int, conducted: int, target_percentage: float) -> dict:
    if attended < 0 or conducted < 0 or attended > conducted:
        raise ValueError("Attendance counts are invalid")
    if not 0 <= target_percentage <= 100:
        raise ValueError("Target must be between 0 and 100")
    target = target_percentage / 100
    current = attended / conducted if conducted else 0.0
    if conducted == 0 and target > 0:
        required, achievable = 1, True
    elif current >= target:
        required, achievable = 0, True
    elif target >= 1:
        required, achievable = 0, False
    else:
        required = ceil((target * conducted - attended) / (1 - target))
        achievable = True
    projected = (attended + required) / (conducted + required) if conducted + required else 0.0
    return {
        "attended_lectures": attended,
        "conducted_lectures": conducted,
        "current_percentage": round(current * 100, 2),
        "target_percentage": target_percentage,
        "required_lectures": required,
        "projected_percentage": round(projected * 100, 2),
        "achievable": achievable,
    }


def projected_attendance(
    attended: int, conducted: int, potential_absences: int, threshold: float
) -> dict:
    if attended < 0 or conducted < attended or potential_absences < 0:
        raise ValueError("Attendance counts are invalid")
    if not 0 <= threshold <= 100:
        raise ValueError("Threshold must be between 0 and 100")
    projected_count = conducted + potential_absences
    percentage = attended / projected_count * 100 if projected_count else 0.0
    return {
        "current_percentage": round(attended / conducted * 100, 2) if conducted else 0.0,
        "projected_percentage": round(percentage, 2),
        "potential_absences": potential_absences,
        "threshold_percentage": threshold,
        "at_risk": percentage < threshold,
    }
