import json
import logging
import math
from collections import defaultdict

from dashboard_backend.database import Session
from dashboard_backend.models.projects import Project
from dashboard_backend.models.railway_infrastructure import OperationalPoint, SectionOfLine

from dashboard_backend.routing.core import find_route_section_of_lines

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Erdradius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_route_between_operational_points(session: Session, start_point: list, end_point: list, operational_points_dict: dict) -> list[int]:
    # Use precomputed operational_points_dict for faster lookup
    nearest_start_op = min(
        operational_points_dict.values(),
        key=lambda op: haversine(start_point[1], start_point[0], op.latitude, op.longitude)
    )
    nearest_end_op = min(
        operational_points_dict.values(),
        key=lambda op: haversine(end_point[1], end_point[0], op.latitude, op.longitude)
    )
    if nearest_start_op and nearest_end_op:
        section_of_line_ids = find_route_section_of_lines(
            session,
            nearest_start_op.op_id,
            nearest_end_op.op_id
        )
        return section_of_line_ids
    return []

def reallocate_project_to_section_of_line(session: Session, clear_existing: bool = True):
    projects = session.query(Project).all()
    operational_points = session.query(OperationalPoint).all()
    operational_points_dict = {op.id: op for op in operational_points}

    # Preload SectionOfLine objects for fast lookup
    section_of_line_objs = {sol.id: sol for sol in session.query(SectionOfLine).all()}

    for idx, project in enumerate(projects):
        if clear_existing:
            project.sections_of_lines.clear()
            project.operational_points.clear()

        section_of_line_ids_set = set()
        geojson_str = project.geojson_representation
        if not geojson_str:
            logging.warning(f"Project {project.id} has no geojson representation.")
            continue
        geojson = json.loads(geojson_str)
        for feature in geojson.get("features", []):
            geom_type = feature["geometry"]["type"]
            if geom_type == "LineString":
                start_point = feature["geometry"]["coordinates"][0]
                end_point = feature["geometry"]["coordinates"][-1]
                section_of_line_ids_new = find_route_between_operational_points(
                    session, start_point, end_point, operational_points_dict
                )
                section_of_line_ids_set.update(section_of_line_ids_new)
            elif geom_type == "Point":
                coordinates = feature["geometry"]["coordinates"]
                nearest_op = min(
                    operational_points_dict.values(),
                    key=lambda op: haversine(coordinates[1], coordinates[0], op.latitude, op.longitude)
                )
                if nearest_op not in project.operational_points:
                    project.operational_points.append(nearest_op)
            else:
                logging.warning(f"Unsupported geometry type {geom_type} for project {project.id}.")
                continue

        # Add the section of line objects to the project
        if section_of_line_ids_set:
            project.sections_of_lines = [section_of_line_objs[sol_id] for sol_id in section_of_line_ids_set if sol_id in section_of_line_objs]

        if idx % 50 == 0:
            logging.info(f"Processed {idx+1}/{len(projects)} projects...")

    session.commit()
    logging.info("Reallocation finished.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    session = Session()
    reallocate_project_to_section_of_line(session)
