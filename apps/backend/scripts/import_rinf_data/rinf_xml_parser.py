from xml.etree import ElementTree as ET
from typing import List
from dashboard_backend.schemas.railway_infrastructure import SOLTrackSchema, OperationalPointSchema, SectionOfLineSchema, SOLTrackParameterSchema
from dashboard_backend.models.railway_infrastructure import OperationalPoint, SectionOfLine, SOLTrack, SOLTrackParameter
from .filter_duplicate_ops import filter_duplicate_ops

def parse_rinf_operational_points_to_object(root: ET.Element) -> List[OperationalPointSchema]:
    operational_points = []
    for op in root.findall('.//OperationalPoint'):
        op_info = {
            'op_id': op.find('UniqueOPID').get('Value'),
            'name': op.find('OPName').get('Value'),
            'type': op.find('OPType').get('Value'),
            'country_code': op.find('UniqueOPID').get('Value')[0:2],
            'latitude': float(op.find('OPGeographicLocation').get("Latitude")) if op.find('OPGeographicLocation') is not None else None,
            'longitude': float(op.find('OPGeographicLocation').get("Longitude")) if op.find('OPGeographicLocation') is not None else None,
            'validity_date_start': op.get('ValidityDateStart'),
            'validity_date_end': op.get('ValidityDateEnd'),
            'railway_location': op.find("OPRailwayLocation").get("NationalIdentNum") if op.find("OPRailwayLocation") is not None else None,
            'railway_location_km': op.find("OPRailwayLocation").get("Kilometer") if op.find("OPRailwayLocation") is not None else None,
        }
        operational_point_pydantic = OperationalPointSchema(**op_info)
        operational_point_sql = OperationalPoint(**operational_point_pydantic.model_dump())
        operational_points.append(operational_point_sql)

    operational_points_unique = filter_duplicate_ops(operational_points)

    return operational_points_unique

def parse_rinf_sections_of_line_to_object(root: ET.Element) -> List[SectionOfLine]:
    sections_of_line_pydantic_objects = []
    for section in root.findall('.//SectionOfLine'):
        section_info = {
            'validity_date_start': section.get('ValidityDateStart'),
            'validity_date_end': section.get('ValidityDateEnd'),
            'solim_code': section.find('SOLIMCode').get('Value'),
            'sol_line_identification': section.find('SOLLineIdentification').get('Value'),
            'sol_op_start': section.find('SOLOPStart').get('Value'),
            'sol_op_end': section.find('SOLOPEnd').get('Value'),
            'sol_length': float(section.find('SOLLength').get('Value')),
            'sol_nature': section.find('SOLNature').get('Value')
        }

        tracks = parse_rinf_sol_track_to_object(section)
        section_info['tracks'] = tracks if tracks else []

        sections_of_line_pydantic_objects.append(SectionOfLineSchema(**section_info))

    sections_of_line_sql = [SectionOfLine(**obj.model_dump()) for obj in sections_of_line_pydantic_objects]

    return sections_of_line_sql

def parse_rinf_sol_track_to_object(section: ET.Element) -> List[SOLTrack]:
    tracks = []
    for track in section.findall('.//SOLTrack'):
        track_info = {
            'track_validity_date_start': track.get('ValidityDateStart'),
            'track_validity_date_end': track.get('ValidityDateEnd'),
            'sol_track_identification': track.find('SOLTrackIdentification').get('Value'),
            'sol_track_direction': track.find('SOLTrackDirection').get('Value'),
            'parameters': []
        }

        for param in track.findall('.//SOLTrackParameter'):
            param_info = {
                'parameter_id': param.get('ID'),
                'is_applicable': param.get('IsApplicable'),
                'value': param.get('Value'),
                'optional_value': param.get('OptionalValue')
            }
            param_pydantic = SOLTrackParameterSchema(**param_info)
            param_sql = SOLTrackParameter(**param_pydantic.model_dump())
            track_info['parameters'].append(param_sql)

        # Create SOLTrack object via pydantic schema
        track_pydantic = SOLTrackSchema(**track_info)
        track_sql = SOLTrack(**track_pydantic.model_dump())

        tracks.append(track_sql)

    return tracks
