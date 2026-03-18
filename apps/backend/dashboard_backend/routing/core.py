from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from dashboard_backend.models.railway_infrastructure import OperationalPoint, SectionOfLine

# Konfigurieren des Loggings
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static SQL constants — defined at module level to make clear that no
# user-controlled data is ever interpolated into the query string.
# All dynamic values (:start_op_id, :end_op_id) are passed as bound params.
# ---------------------------------------------------------------------------
_SQL_NODES = (
    "SELECT op_id, ROW_NUMBER() OVER () AS node_id FROM operational_point"
)

_SQL_EDGES = (
    "SELECT sol.id, n_start.node_id AS source, n_end.node_id AS target,"
    " sol.sol_length AS cost"
    " FROM section_of_line sol"
    " JOIN (" + _SQL_NODES + ") n_start ON sol.sol_op_start = n_start.op_id"
    " JOIN (" + _SQL_NODES + ") n_end ON sol.sol_op_end = n_end.op_id"
)

_SQL_ROUTE_QUERY = text(
    "WITH nodes AS (" + _SQL_NODES + "),"
    " start_node AS (SELECT node_id FROM nodes WHERE op_id = :start_op_id),"
    " end_node AS (SELECT node_id FROM nodes WHERE op_id = :end_op_id)"
    " SELECT sol.id AS section_of_line_id"
    " FROM pgr_dijkstra("
    "   $$ " + _SQL_EDGES + " $$,"
    "   (SELECT node_id FROM start_node),"
    "   (SELECT node_id FROM end_node),"
    "   directed := false"
    " ) AS di"
    " JOIN section_of_line sol ON di.edge = sol.id"
    " ORDER BY di.path_seq"
)


def find_route_section_of_lines(db: Session, start_op_id: str, end_op_id: str) -> list[int]:
    """
    Findet die kürzeste Route zwischen zwei Betriebspunkten mithilfe von pgRouting (pgr_dijkstra).
    Die Funktion baut die Graphentopologie zur Laufzeit aus den Tabellen 'operational_point' und 'section_of_line' auf.

    :param db: Die SQLAlchemy-Datenbanksitzung.
    :param start_op_id: Die RINF OP-ID des Startpunkts.
    :param end_op_id: Die RINF OP-ID des Endpunkts.
    :return: Eine Liste von Geometrien (als GeoJSON-Strings), die die Route bilden.
    """

    start_exists = db.query(OperationalPoint).filter_by(op_id=start_op_id).scalar()
    if not start_exists:
        raise ValueError(f"Startbetriebspunkt {start_op_id} existiert nicht.")

    end_exists = db.query(OperationalPoint).filter_by(op_id=end_op_id).scalar()
    if not end_exists:
        raise ValueError(f"Zielbetriebspunkt {end_op_id} existiert nicht.")

    logger.debug(f"Searche route from {start_op_id} to {end_op_id}")
    result = db.execute(_SQL_ROUTE_QUERY, {"start_op_id": start_op_id, "end_op_id": end_op_id})
    section_ids = [row[0] for row in result.fetchall()]

    if not section_ids:
        logger.debug(f"Keine Route zwischen {start_op_id} und {end_op_id} gefunden.")
        return []

    logger.debug(f"Route mit {len(section_ids)} Segmenten gefunden.")
    return section_ids
