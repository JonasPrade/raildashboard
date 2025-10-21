from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from dashboard_backend.schemas.projects import ProjectSchema

class ProjectGroupSchema(BaseModel):
    id: Optional[int] = None
    name: str
    short_name: str
    description: Optional[str] = None
    public: bool = False
    color: str = "#FF0000"
    plot_only_superior_projects: bool = True
    id_old: Optional[int] = None

    # relationships
    projects: List[ProjectSchema] = Field(default_factory=list, description="List of projects associated with this project group")

    model_config = ConfigDict(from_attributes=True)
