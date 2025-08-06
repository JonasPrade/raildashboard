import pandas as pd
from pydantic import ValidationError

from dashboard_backend.database import Session
from dashboard_backend.models.projects import ProjectGroup
from dashboard_backend.schemas.projects import ProjectGroupSchema

def import_project_group(filepath_csv: str, session: Session, clear_db: bool = False):
    df = pd.read_csv(filepath_csv)
    if clear_db:
        session.query(ProjectGroup).delete()

    for _, row in df.iterrows():
        try:
            data = ProjectGroupSchema(**row.to_dict())
            project_group = ProjectGroup(**data.model_dump(exclude_unset=True))
            session.add(project_group)
        except ValidationError as e:
            print(f"Validation error for row {row.to_dict()}: {e}")

    session.commit()

if __name__ == "__main__":
    filepath_csv = '../../data/old_db_import/project_groups.csv'
    session = Session()
    import_project_group(filepath_csv, session, clear_db=True)
