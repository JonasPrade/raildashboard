from rdflib import Graph, RDF, RDFS, OWL
from rdflib.namespace import Namespace

SKIP_ANNOTATIONS = ["deprecated", "retired", "obsolete"]

def is_deprecated(graph, subject) -> bool:
    for val in graph.objects(subject, OWL.deprecated):
        if str(val).lower() == "true":
            return True
    for c in graph.objects(subject, RDFS.comment):
        if any(kw in str(c).lower() for kw in SKIP_ANNOTATIONS):
            return True
    return False

def extract_classes(graph: Graph):
    for s in graph.subjects(RDF.type, OWL.Class):
        label = next(graph.objects(s, RDFS.label), None)
        if not label or is_deprecated(graph, s):
            continue
        yield str(label), s
