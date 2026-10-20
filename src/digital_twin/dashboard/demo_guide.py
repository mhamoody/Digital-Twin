"""Display-only walkthrough of the known v2 synthetic generator, never model input.

Names/IDs are fictional. These are design intentions, not expected risk scores,
ground truth labels or claims that any saved model analysis succeeded.
"""
from __future__ import annotations

from typing import Any


def demo_examples(course: dict[str, Any]) -> list[dict[str, Any]]:
    courses = {f"synthetic:{code}:2026A:v2": index
               for index, code in enumerate(("CS110", "DS210", "ED220"), 1)}
    course_id = course.get("presentation_id")
    if course.get("data_origin") != "synthetic" or course_id not in courses:
        return []
    weeks = course.get("checkpoints") or range(1, int(course.get("weeks", 0)) + 1)
    practice_title, practice_check = (
        ("Practice is not a summative grade",
         "Open Academic progress. Practice/formative marks stay separate from "
         "assessed grades; optional practice resources are not overdue required work.")
        if course_id == "synthetic:DS210:2026A:v2"
        else
        ("Optional practice is not required work",
         "Open Academic progress and compare required resources with optional practice. "
         "Optional practice is not overdue required work. This course has no marked "
         "practice quizzes; for that comparison use Applied Data Project, updated "
         "demo v2, learner synthetic:learner:2:0001 at week 6.")
    )
    examples = [
        ("Quiet activity, strong assessed grades", 3, 6,
         "Compare activity with published assessed grades and required work. "
         "If login monitoring is disabled, quiet activity must not become either "
         "a concern or reassurance. Other academic concerns can still apply."),
        (practice_title, 1, 6, practice_check),
        ("Approved extension", 6, 4,
         "Inspect the approved extension and the checkpoint cutoff. An extended "
         "assessment is not missed before its effective deadline. This does not "
         "excuse unrelated overdue work or guarantee a low risk score."),
        ("Support and later progress", 8, 8,
         "Open Support history and compare academic evidence before and after "
         "the recorded support. Keep planned/completed actions distinct. Later "
         "improvement does not prove that the intervention caused it."),
    ]
    return [dict(title=title, learner_id=f"synthetic:learner:{courses[course_id]}:{number:04d}",
                 week=week, check=check)
            for title, number, week, check in examples if week in weeks]
