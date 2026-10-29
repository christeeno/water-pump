from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field

CommandType = Literal["PUMP_ON", "PUMP_OFF", "SET_MODE_AUTO", "SET_MODE_MANUAL"]


class PumpCommandCreate(BaseModel):
    command_type: CommandType
    issued_by: Optional[str] = "frontend"


class PumpCommandAck(BaseModel):
    device_reported_state: Optional[str] = Field(None, max_length=64)


class PumpCommandResponse(BaseModel):
    id: int
    command_id: str
    device_id: str
    command_type: str
    issued_at: datetime
    expires_at: datetime
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    device_reported_state: Optional[str] = None
    issued_by: str

    model_config = ConfigDict(from_attributes=True)
