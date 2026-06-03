"""
recommendations.py  —  Rule-based intervention recommendations
"""

PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

# ─────────────────────────────────────────────────────────────
# RULE DEFINITIONS
# ─────────────────────────────────────────────────────────────
def generate(student: dict, scheme: dict) -> dict:
    """
    Given a student record and the active grading scheme,
    return a dict:
      {
        "priority":        "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE",
        "recommendations": [ { "priority", "title", "detail" }, ... ]
      }
    """
    pass_mark  = scheme.get("pass_mark", 45)
    recs       = []

    exam   = student.get("exam_score",    0)
    att    = student.get("attendance",    0)
    at     = student.get("avg_test",      0)
    aa     = student.get("avg_assignment",0)
    score  = student.get("final_score",   0)
    risk   = student.get("at_risk", "No") == "Yes"

    if not risk:
        return {"priority": "NONE", "recommendations": []}

    # ── Individual rules ──────────────────────────────────
    if exam < 40:
        recs.append({
            "priority": "HIGH",
            "title":    "Critical Exam Performance",
            "detail":   (
                "The student's exam score is critically low. Schedule a one-on-one "
                "review session, provide past exam papers for practice, and assess "
                "whether there are underlying comprehension gaps in core topics."
            )
        })
    elif exam < pass_mark:
        recs.append({
            "priority": "MEDIUM",
            "title":    "Below-Pass Exam Score",
            "detail":   (
                "Exam score is below the pass mark. Targeted revision of key topics "
                "and timed practice tests are recommended before the next assessment."
            )
        })

    if att < 70:
        recs.append({
            "priority": "HIGH",
            "title":    "Attendance Below Minimum Threshold",
            "detail":   (
                "Attendance is below the 70% minimum requirement. Issue a formal "
                "attendance warning letter and notify the student's department. "
                "Consider escalating to the academic office if the pattern continues."
            )
        })
    elif att < 80:
        recs.append({
            "priority": "LOW",
            "title":    "Attendance Approaching Minimum",
            "detail":   (
                "Attendance is declining towards the minimum threshold. "
                "An informal verbal reminder and monitoring over the next two weeks "
                "is advised."
            )
        })

    if at < 40:
        recs.append({
            "priority": "MEDIUM",
            "title":    "Consistently Poor Test Performance",
            "detail":   (
                "Average test score indicates consistent difficulty with in-semester "
                "assessments. Recommend weekly progress check-ins and supplementary "
                "study materials targeted at frequently tested concepts."
            )
        })

    if aa < 40:
        recs.append({
            "priority": "LOW",
            "title":    "Low Assignment Scores",
            "detail":   (
                "Assignment quality and scores are below expectation. Schedule a "
                "coursework consultation to identify understanding gaps. Check whether "
                "submission deadlines are being met consistently."
            )
        })

    if score < pass_mark and exam >= 40:
        recs.append({
            "priority": "MEDIUM",
            "title":    "Borderline Overall Score",
            "detail":   (
                "The student's overall predicted score is just below the pass mark "
                "but the exam result shows some competency. Focused improvement in "
                "continuous assessment components (tests and assignments) may be "
                "sufficient to achieve a passing grade."
            )
        })

    # ── Multi-factor critical flag ────────────────────────
    if len(recs) >= 3:
        recs.insert(0, {
            "priority": "CRITICAL",
            "title":    "Multiple Risk Factors — Immediate Action Required",
            "detail":   (
                "This student has been flagged for multiple simultaneous risk factors. "
                "An immediate referral to the academic support unit is strongly advised. "
                "A structured intervention plan involving the student, lecturer, and "
                "academic advisor should be initiated without delay."
            )
        })

    # ── Determine overall priority ────────────────────────
    if not recs:
        overall = "LOW"
    else:
        overall = min(recs, key=lambda r: PRIORITY_ORDER.get(r["priority"], 99))["priority"]

    return {"priority": overall, "recommendations": recs}


def priority_badge_style(priority: str) -> dict:
    """Return CSS colour tokens for a given priority level."""
    styles = {
        "CRITICAL": {"bg": "#fef2f2", "text": "#dc2626", "border": "#fecaca"},
        "HIGH":     {"bg": "#fff7ed", "text": "#ea580c", "border": "#fed7aa"},
        "MEDIUM":   {"bg": "#fefce8", "text": "#ca8a04", "border": "#fde68a"},
        "LOW":      {"bg": "#eff6ff", "text": "#2563eb", "border": "#bfdbfe"},
        "NONE":     {"bg": "#f0fdf4", "text": "#16a34a", "border": "#bbf7d0"},
    }
    return styles.get(priority, styles["NONE"])