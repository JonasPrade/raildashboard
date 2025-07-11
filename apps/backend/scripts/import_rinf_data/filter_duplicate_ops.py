import logging
from typing import List, Dict
from dashboard_backend.schemas.railway_infrastructure.operational_point import OperationalPointSchema
from dashboard_backend.models.railway_infrastructure import OperationalPoint
# Configure logging, e.g., at the beginning of your file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def filter_duplicate_ops(op_points: List[OperationalPoint]) -> List[OperationalPoint]:
    """
    Removes duplicate Operational Points based on op_id from a list.
    A log entry is created for each removed duplicate, detailing the differences.

    :param op_points: A list of OperationalPoint objects.
    :return: A new list without duplicates.
    """
    unique_points: Dict[str, OperationalPoint] = {}

    for point in op_points:
        # Skip entries where op_id is None if they are not relevant
        if point.op_id is None:
            continue

        if point.op_id not in unique_points:
            unique_points[point.op_id] = point
        else:
            original_point = unique_points[point.op_id]

            # Decide which point to keep based on validity_date_end
            # The one with the more recent validity_date_end is kept.
            if (point.validity_date_end is not None and
                (original_point.validity_date_end is None or point.validity_date_end > original_point.validity_date_end)):
                # New point is more recent, replace the old one.
                unique_points[point.op_id] = point
                point_to_discard = original_point
                logging.info(f"Replacing duplicate Operational Point for op_id='{point.op_id}' with a more recent one.")
            else:
                # Original point is more recent or they are the same, discard the new one.
                point_to_discard = point

            # Convert ORM objects to Pydantic schemas to use model_dump() for detailed comparison
            original_schema = OperationalPointSchema.from_orm(unique_points[point.op_id])
            duplicate_schema = OperationalPointSchema.from_orm(point_to_discard)

            original_dict = original_schema.model_dump()
            duplicate_dict = duplicate_schema.model_dump()
            differences = []
            for key, original_value in original_dict.items():
                duplicate_value = duplicate_dict.get(key)
                if original_value != duplicate_value:
                    differences.append(f"{key}: '{original_value}' (kept) vs '{duplicate_value}' (discarded)")

            if differences:
                logging.info(f"Discarding duplicate Operational Point: op_id='{point.op_id}'. Differences: {'; '.join(differences)}")
            else:
                logging.info(f"Discarding identical duplicate Operational Point: op_id='{point.op_id}'")

    return list(unique_points.values())
