import numpy as np
import pandas as pd

from dashboard_backend.database import Session
from dashboard_backend.models.associations import ProjectToProjectGroup
from dashboard_backend.models.projects import Project, ProjectGroup

def connect_project_to_group(filepath_csv: str, session: Session, clear_db: bool = False):
    df = pd.read_csv(filepath_csv)
    if clear_db:
        session.query(ProjectToProjectGroup).delete()

    for _, row in df.iterrows():
        # the csv contains the old project id and the old group id
        project_id_old = int(row['projectcontent_id'])
        projectgroup_id_old = int(row['projectgroup_id'])

        # find the new project id and group id based on the old ids
        project = session.query(Project).filter_by(old_id=project_id_old).scalar()
        project_group = session.query(ProjectGroup).filter_by(id_old=projectgroup_id_old).scalar()

        if project and project_group:
            # add the association
            project.project_groups.append(project_group)
            session.add(project)
        else:
            raise ValueError(
                f"Project or ProjectGroup not found for old ids: "
                f"project_id_old={project_id_old}, projectgroup_id_old={projectgroup_id_old}"
            )

    session.commit()


if __name__ == "__main__":
    filepath_csv = '../../data/old_db_import/projectcontent_to_group.csv'
    session = Session()
    connect_project_to_group(filepath_csv, session, clear_db=True)



