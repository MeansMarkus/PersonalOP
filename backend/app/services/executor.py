from app.schemas.task import TaskPlanStep


def execute_steps(steps: list[TaskPlanStep]) -> list[TaskPlanStep]:
    updated_steps: list[TaskPlanStep] = []
    for step in steps:
        updated_steps.append(TaskPlanStep(id=step.id, description=step.description, status="done"))
    return updated_steps
