from datetime import datetime

from pydantic import BaseModel


class ExecutionRecordRead(BaseModel):
    id: int
    task_id: int
    task_name: str
    status: str
    trigger_type: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    exit_code: int | None
    error_message: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class ExecutionLogRead(BaseModel):
    id: int
    execution_id: int
    stdout: str
    stderr: str

    model_config = {"from_attributes": True}
