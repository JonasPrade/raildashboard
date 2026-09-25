from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Any, Optional, List
from dashboard_backend.schemas.projects.project_schema import ProjectListItem

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
    # Slim items without geometry — see ProjectListItem and the
    # /{id}/geometries endpoint.
    projects: List[ProjectListItem] = Field(default_factory=list, description="List of projects associated with this project group")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("projects", mode="after")
    @classmethod
    def exclude_draft_projects(cls, value: List[ProjectListItem]) -> List[ProjectListItem]:
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


class ProjectGroupGeometriesSchema(BaseModel):
    """Simplified map geometries of one group's projects, keyed by project id.

    Each value is a GeoJSON FeatureCollection with at most one MultiLineString
    and one MultiPoint feature. Lines are simplified for the overview map; the
    exact geometry stays available on ``GET /projects/{id}``.
    """

    group_id: int
    only_superior: bool
    tolerance: float = Field(description="Simplification tolerance in degrees")
    geometries: dict[int, Any]
