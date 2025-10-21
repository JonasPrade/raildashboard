from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from dashboard_backend.models.railway_infrastructure import OperationalPoint, SectionOfLine

# Konfigurieren des Loggings
logger = logging.getLogger(__name__)

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

    # Diese Abfrage ist komplexer, da sie die für pgRouting benötigte Struktur zur Laufzeit erstellt:
    # 1. 'nodes': Erstellt eine temporäre Zuordnung von 'op_id' (String) zu einer eindeutigen 'node_id' (Integer).
    # 2. 'edges': Erstellt die Kantentabelle für pgRouting, indem 'sol_op_start'/'sol_op_end' durch die Integer 'node_id' ersetzt werden.
    # 3. 'pgr_dijkstra': Führt die Routenberechnung auf dem dynamisch erstellten Graphen durch.
    # 4. Das Endergebnis verbindet die gefundenen Routensegmente (Kanten) wieder mit den Betriebspunkten,
    #    um die Liniengeometrie zwischen den jeweiligen Start- und Endpunkten zu erstellen.
    sql_nodes = """
                SELECT op_id, ROW_NUMBER() OVER () AS node_id \
                FROM operational_point \
                """
    sql_edges = """
        SELECT
            sol.id,
            n_start.node_id AS source,
            n_end.node_id AS target,
            sol.sol_length AS cost
        FROM section_of_line sol
        JOIN (""" + sql_nodes + """) n_start ON sol.sol_op_start = n_start.op_id
        JOIN (""" + sql_nodes + """) n_end ON sol.sol_op_end = n_end.op_id
    """
    sql_query = text(f"""
        WITH nodes AS ({sql_nodes}),
        start_node AS (SELECT node_id FROM nodes WHERE op_id = :start_op_id),
        end_node AS (SELECT node_id FROM nodes WHERE op_id = :end_op_id)
        SELECT sol.id AS section_of_line_id
        FROM pgr_dijkstra(
            $$ {sql_edges} $$,
            (SELECT node_id FROM start_node),
            (SELECT node_id FROM end_node),
            directed := false
        ) AS di
        JOIN section_of_line sol ON di.edge = sol.id
        ORDER BY di.path_seq;
    """)

    logger.debug(f"Searche route from {start_op_id} to {end_op_id}")
    result = db.execute(sql_query, {"start_op_id": start_op_id, "end_op_id": end_op_id})
    section_ids = [row[0] for row in result.fetchall()]

    if not section_ids:
        logger.debug(f"Keine Route zwischen {start_op_id} und {end_op_id} gefunden.")
        return []

    logger.debug(f"Route mit {len(section_ids)} Segmenten gefunden.")
    return section_ids
