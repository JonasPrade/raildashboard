# iterate through the table projects
# it will connect the project with superior_project id
# therefore it will search the superior project by the superior_project_old_id
# and set the superior_project_id in the project table to the id of the superior project

import logging

from dashboard_backend.database import Session
from dashboard_backend.models.projects import Project

def reallocate_superior_project_id(session: Session, overwrite: bool = False):
    projects = session.query(Project).all()

    for project in projects:
        if project.superior_project_id is not None and not overwrite:
            logging.info(f"Project {project.id} already has a superior project ID {project.superior_project_id}, skipping.")
            continue
        if project.superior_project_old_id is not None:
            superior_project = session.query(Project).filter(
                Project.old_id == project.superior_project_old_id
            ).first()

            if superior_project:
                project.superior_project_id = superior_project.id
                logging.info(f"Project {project.id} linked to superior project {superior_project.id}")
            else:
                raise ValueError(f"No superior project found for project {project.id} for superior project old id {project.superior_project_old_id}")

    session.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    session = Session()
    reallocate_superior_project_id(session)
