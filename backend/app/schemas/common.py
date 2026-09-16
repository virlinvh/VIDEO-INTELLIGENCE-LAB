from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class HealthCheckResponse(BaseSchema):
    status: str
    app_name: str
    version: str
    environment: str
    database_connected: bool
    storage_directories_ready: bool
