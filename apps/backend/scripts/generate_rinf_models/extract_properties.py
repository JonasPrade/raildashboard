from rdflib import Graph, RDFS
from rdflib.namespace import XSD, SH
from pathlib import Path
import re

from .extract_classes import extract_classes

def extract_properties(graph: Graph, class_uri):
    props = []
    for prop in graph.subjects(RDFS.domain, class_uri):
        label = next(graph.objects(prop, RDFS.label), None)
        range_ = next(graph.objects(prop, RDFS.range), None)

        for sh_shape in graph.subjects(SH.path, prop):
            datatype = next(graph.objects(sh_shape, SH.datatype), None)
            if datatype:
                range_ = datatype
                break

        props.append((str(label), range_))
    return props


def clean_ttl_file_content(ttl_path: Path) -> str:
    """
    Loads TTL file and returns a cleaned version as string.
    Specifically removes/cleans malformed URIs (e.g. trailing spaces).
    """
    raw = ttl_path.read_text(encoding='utf-8')

    # Beispiel: Entferne Leerzeichen aus URIs in spitzen Klammern
    cleaned = re.sub(r'<([^>]+?)\s+>', lambda m: f'<{m.group(1).strip()}>', raw)

    return cleaned

def extract_all_properties(ttl_path):
    g = Graph()
    cleaned_data = clean_ttl_file_content(ttl_path)
    g.parse(data=cleaned_data, format="turtle")

    classes = {}
    for class_name, class_uri in extract_classes(g):
        label = next(g.objects(class_uri, RDFS.label), None)
        comment = next(g.objects(class_uri, RDFS.comment), None)
        superclass = next(g.objects(class_uri, RDFS.subClassOf), None)
        props = extract_properties(g, class_uri)
        classes[class_name] = {
            "uri": str(class_uri),
            "label": str(label) if label else None,
            "comment": str(comment) if comment else None,
            "superclass": str(superclass) if superclass else None,
            "properties": [(p, str(r) if r else None) for p, r in props],
        }

    return classes
