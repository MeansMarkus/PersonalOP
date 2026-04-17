from __future__ import annotations

from app.schemas.task import TaskIntake, TaskPlanStep


def _pick_task_type(goal: str) -> tuple[str, str, list[str], str]:
    lowered_goal = goal.lower()

    task_types = (
        (
            "internship-search",
            "Internship search",
            ["internship", "internships", "job", "role", "application"],
            "Start by identifying target companies and filters.",
        ),
        (
            "networking",
            "Networking",
            ["network", "networking", "reach out", "message", "connect"],
            "List target people and draft a short outreach message.",
        ),
        (
            "interview-prep",
            "Interview prep",
            ["interview", "prep", "behavioral", "mock", "leetcode"],
            "Turn the prompt into interview topics and practice sessions.",
        ),
        (
            "skills-sprint",
            "Skills sprint",
            ["learn", "practice", "build", "study", "skill"],
            "Break the goal into a short practice roadmap.",
        ),
    )

    for task_type, focus_area, keywords, next_best_action in task_types:
        matched_keywords = [keyword for keyword in keywords if keyword in lowered_goal]
        if matched_keywords:
            return task_type, focus_area, matched_keywords, next_best_action

    return (
        "general-task",
        "General planning",
        [],
        "Clarify the outcome, deadline, and any constraints before execution.",
    )


def build_task_intake(goal: str) -> TaskIntake:
    task_type, focus_area, keywords, next_best_action = _pick_task_type(goal)
    return TaskIntake(
        task_type=task_type,
        focus_area=focus_area,
        keywords=keywords,
        next_best_action=next_best_action,
    )


def plan_goal(goal: str) -> list[TaskPlanStep]:
    # This is intentionally deterministic for MVP testing.
    return [
        TaskPlanStep(id=1, description=f"Understand goal: {goal}"),
        TaskPlanStep(id=2, description="Find relevant internships"),
        TaskPlanStep(id=3, description="Store top matches in tracker"),
        TaskPlanStep(id=4, description="Generate execution summary"),
    ]
