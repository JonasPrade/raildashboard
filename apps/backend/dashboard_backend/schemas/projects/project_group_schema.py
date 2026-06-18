from pydantic import BaseModel, Field, ConfigDict, field_validator
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
    is_visible: bool = True
    is_default_selected: bool = False
    id_old: Optional[int] = None

    # relationships
    projects: List[ProjectSchema] = Field(default_factory=list, description="List of projects associated with this project group")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("projects", mode="after")
    @classmethod
    def exclude_draft_projects(cls, value: List[ProjectSchema]) -> List[ProjectSchema]:
        """Drafts are hidden from the public map/group views."""
        return [p for p in value if not p.is_draft]


class ProjectGroupCreate(BaseModel):
    name: str
    short_name: str
    description: Optional[str] = None
    public: bool = False
    color: str = "#FF0000"
    plot_only_superior_projects: bool = True
    is_visible: bool = True
    is_default_selected: bool = False
