import pytest
from unittest.mock import MagicMock, ANY
from dashboard_backend.routing.core import find_route_in_db
from dashboard_backend.models.railway_infrastructure import OperationalPoint, SectionOfLine

def test_load_infra(db_session):
    operational_points = db_session.query(OperationalPoint).all()
    section_of_lines = db_session.query(SectionOfLine).all()

    assert len(operational_points) > 0
    assert len(section_of_lines) > 0

def test_find_route_in_db(db_session):
    """
    Tests if a route could be found between two operational points.
    Does not test for plausibility of the route, just that it exists.
    :param db_session:
    :return:
    """
    start_op = "ATWs"
    end_op = "ATSb"

    result = find_route_in_db(db_session, start_op, end_op)

    assert isinstance(result, list)
    assert len(result) > 0

def test_false_start_operational_point(db_session):
    """
    Tests if an exception is raised when the start operational point does not exist.
    :param db_session:
    :return:
    """
    with pytest.raises(ValueError):
        find_route_in_db(db_session, "NON_EXISTENT_OP", "ATSb")

