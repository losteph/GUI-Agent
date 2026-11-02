
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class TaskStep:
    id: int
    action: str
    description: str
    parameters: dict = field(default_factory=dict)
    status: str = "pending"
    result: Optional[str] = None


@dataclass
class TaskState:
    task_id: str
    original_instruction: str
    goal: str

    steps: list[TaskStep] = field(default_factory=list)

    current_step: int = 0
    status: str = "planning"

    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    completed_at: Optional[str] = None
    error: Optional[str] = None

    def get_current_step(self):
        if self.current_step >= len(self.steps):
            return None

        return self.steps[self.current_step]

    def advance(self):
        if self.current_step < len(self.steps):
            self.steps[self.current_step].status = "completed"
            self.current_step += 1

    def is_completed(self):
        return (
            self.current_step >= len(self.steps)
            and self.status == "completed"
        )
