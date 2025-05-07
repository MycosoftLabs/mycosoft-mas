from enum import Enum

class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"
    SCHEDULED = "scheduled"
    OVERDUE = "overdue" 