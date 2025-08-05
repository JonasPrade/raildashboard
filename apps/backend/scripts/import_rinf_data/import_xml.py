"""
This script imports RINF (Register of Infrastructure) data from an XML file into the database.

Usage:
    python import_xml.py <country_code> [--clear]

Arguments:
    <country_code>: The two-letter country code for which to import data (e.g., 'DE').
                    The script expects a corresponding file 'rinf_<country_code>.xml'
                    in the 'output/xml_countries' directory.

Options:
    --clear: If specified, all existing data in the relevant database tables
             (OperationalPoint, SectionOfLine, SOLTrack, SOLTrackParameter)
             will be deleted before the new data is imported.

Example (import for Germany without clearing tables):
    python import_xml.py DE

Example (import for Austria, clearing tables first):
    python import_xml.py AT --clear
"""

import os
import sys
import logging
import argparse
from xml.etree import ElementTree as ET
from .rinf_xml_parser import parse_rinf_operational_points_to_object, parse_rinf_sections_of_line_to_object

from .config import OUTPUT_DIR
from dashboard_backend.database import Session
from dashboard_backend.models.railway_infrastructure import OperationalPoint, SectionOfLine, SOLTrackParameter, SOLTrack

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

print(f"Aktuelles Arbeitsverzeichnis: {os.getcwd()}")
print(f"Python-Suchpfad: {sys.path}")

def import_xml(xml_file_path: str) -> ET.ElementTree:
    try:
        logger.info(f"Starting to parse XML file: {xml_file_path}")
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file {xml_file_path}: {e}")
        raise
    return root


def import_xml_country(country_string: str, clear_tables: bool = False, output_dir: str = OUTPUT_DIR) -> None:
    # read the XML file
    xml_file_path = os.path.abspath(f'{output_dir}/xml_countries/rinf_{country_string}.xml')
    if not os.path.exists(xml_file_path):
        logger.error(f"XML file for country {country_string} does not exist at {xml_file_path}")
        raise FileNotFoundError(f"XML file for country {country_string} does not exist at {xml_file_path}")

    logger.info(f"Importing data for country: {country_string}")
    root = import_xml(xml_file_path)

    logger.info("Parsing operational points...")
    operational_lines = parse_rinf_operational_points_to_object(root)
    logger.info(f"Parsed {len(operational_lines)} operational points.")

    logger.info("Parsing sections of line...")
    section_of_lines = parse_rinf_sections_of_line_to_object(root)
    logger.info(f"Parsed {len(section_of_lines)} sections of line.")

    # save operational points and sections of line to the database
    session = Session()
    try:
        if clear_tables:
            logger.info("Clearing database tables before import...")
            # This will also delete related SOLTrack and SOLTrackParameter due to cascade
            session.query(SectionOfLine).delete()
            session.query(OperationalPoint).delete()
            session.query(SOLTrack).delete()
            session.query(SOLTrackParameter).delete()
            logger.info("Tables cleared.")

        logger.info("Saving objects to the database...")
        session.add_all(operational_lines)
        session.add_all(section_of_lines)
        session.commit()
        logger.info("Data successfully written to the database.")
    except Exception as e:
        logger.error(f"Error writing to the database: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        logger.info("Session closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import RINF XML data for a specific country.")
    parser.add_argument("country_code", type=str, help="The country code to import (e.g., 'DE').")
    parser.add_argument("--clear", action="store_true", help="Clear the relevant database tables before importing.")
    args = parser.parse_args()

    try:
        import_xml_country(args.country_code, args.clear)
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)
