from pydantic import BaseModel, Field
from typing import Optional, List

class ProjectGroupSchema(BaseModel):
    id: Optional[int] = None
    name: str
    short_name: str
    description: Optional[str] = None
    public: bool = False
    color: str = "#FF0000"
    plot_only_superior_projects: bool = True
    id_old: Optional[int] = None

    class Config:
        from_attributes = True