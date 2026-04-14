from app.schemas.task import TaskPlanStep


def plan_goal(goal: str) -> list[TaskPlanStep]:
    # This is intentionally deterministic for MVP testing.
    return [
        TaskPlanStep(id=1, description=f"Understand goal: {goal}"),
        TaskPlanStep(id=2, description="Find relevant internships"),
        TaskPlanStep(id=3, description="Store top matches in tracker"),
        TaskPlanStep(id=4, description="Generate execution summary"),
    ]
