from pydantic import BaseModel
from typing import Optional

class AvailabilityUpdate(BaseModel):
    is_online: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_status: Optional[str] = None
    custom_status_message: Optional[str] = None
