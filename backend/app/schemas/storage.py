from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.app.schemas.common import BaseSchema

class StorageCategoryInfo(BaseSchema):
    category: str
    relative_path: str
    absolute_path: str
    size_bytes: int
    size_human: str
    file_count: int
    is_regeneratable: bool

class StorageOverviewResponse(BaseSchema):
    total_size_bytes: int
    total_size_human: str
    categories: List[StorageCategoryInfo]
    saved_video_library: StorageCategoryInfo
