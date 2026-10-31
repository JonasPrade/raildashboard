from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Any, Optional, List
from dashboard_backend.schemas.projects.project_schema import ProjectListItem
from dashboard_backend.schemas.projects.progress_schema import SkippablePhaseLiteral

class ProjectGroupSchema(BaseModel):
    id: Optional[int] = None
    name: str
    short_name: str
    description: Optional[str] = None
    public: bool = False
    color: str = "#6E50FA"
    plot_only_superior_projects: bool = True
    is_visible: bool = True
    is_default_selected: bool = False
    skipped_phases: List[SkippablePhaseLiteral] = Field(
        default_factory=list,
        description="Planning phases this group's projects usually skip; hidden in the "
        "progress view and forecast when all of a project's groups skip them",
    )
    assumed_build_months: Optional[int] = Field(
        default=None,
        ge=1,
        le=120,
        description="Assumed construction period (months) for projects without a published "
        "closure period; the forecast derives the commissioning as ASSUMED (HLK: 6)",
    )
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
    color: str = "#6E50FA"
    plot_only_superior_projects: bool = True
    is_visible: bool = True
    is_default_selected: bool = False
    skipped_phases: List[SkippablePhaseLiteral] = Field(default_factory=list)
    assumed_build_months: Optional[int] = Field(default=None, ge=1, le=120)


class MapLaneSchema(BaseModel):
    """Stored lane of a project and the projects it shares a track with.

    The map recolours only the projects it shows, preferring the stored lane
    (docs/features/feature-map-overlapping-geometries.md → B1).
    """

    lane: int = 0
    overlaps: List[int] = Field(default_factory=list)


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
    lanes: dict[int, MapLaneSchema] = Field(
        default_factory=dict,
        description="Projects with a lane above 0 or overlap partners; all others are on lane 0",
    )


class ProjectGroupUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    public: Optional[bool] = None
    color: Optional[str] = None
    plot_only_superior_projects: Optional[bool] = None
    is_visible: Optional[bool] = None
    is_default_selected: Optional[bool] = None
    skipped_phases: Optional[list[SkippablePhaseLiteral]] = None
    # Explicit null clears the build period.
    assumed_build_months: Optional[int] = Field(default=None, ge=1, le=120)
