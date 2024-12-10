import json
from datetime import datetime
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import RDFS, XSD
import re

# Load the ontology from git folder
ontology_path = '../../../ontology/btp-ontology.ttl'
g = Graph()
g.parse(ontology_path, format='turtle')

# Define namespaces
BASE = Namespace("http://www.dei.unipd.it/~gdb/ontology/btp/")
g.bind("base", BASE)

# Load the JSON file from git folder
json_file_path = '../../../datasets/json/rifter_arcstra_li.json'
with open(json_file_path, 'r') as f:
    json_data = json.load(f)


def to_camel_case(s):
    s = re.sub(r'[-/]', '', s)
    s = re.sub(r'[^a-zA-Z0-9]', ' ', s).title().replace(' ', '')
    return s[0].lower() + s[1:] if s else ''

# Create a hashmap for nomevia to codvia
road_map = {entry['nomevia']: entry['codvia'] for entry in json_data}

# Process each JSON entry
for entry in json_data:
    # Create URIs for Roads, RoadArch, Districts, and RoadNodes
    road_uri = BASE[f"road_{entry['codvia']}"]
    roadarch_uri = BASE[f"roadarch_{entry['codarco']}"]
    district_uri = BASE[to_camel_case(entry['nomequart'])]
    date_uri = BASE[f"date_{entry['data_istit']}"]
    node_1_uri = BASE[f"roadnode_{entry['cod_nodo1']}"]
    node_2_uri = BASE[f"roadnode_{entry['cod_nodo2']}"]

    # Add Node class
    g.add((node_1_uri, RDF.type, BASE.RoadNode))
    g.add((node_2_uri, RDF.type, BASE.RoadNode))

    # Add Road class and its properties
    g.add((road_uri, RDF.type, BASE.Road))
    g.add((road_uri, RDFS.label, Literal(entry['nomevia'], lang='en')))

    # Add RoadArch class and link to Road
    g.add((roadarch_uri, RDF.type, BASE.RoadArch))
    g.add((roadarch_uri, BASE.hasNode, node_1_uri))
    g.add((roadarch_uri, BASE.hasNode, node_2_uri))
    if(entry['da'] in road_map and entry['a'] in road_map):
        from_uri = BASE[f"road_{road_map[entry['da']]}"]
        to_uri = BASE[f"road_{road_map[entry['a']]}"]
        g.add((roadarch_uri, BASE.isArchFromRoad, from_uri))
        g.add((roadarch_uri, BASE.isArchToRoad, to_uri))


    # Add Date class
    g.add((date_uri, RDF.type, BASE.Date))
    g.add((roadarch_uri, BASE.hasDeploymentDate, date_uri))
    formatted_date = datetime.strptime(entry['data_istit'], "%Y-%m-%d").isoformat()
    g.add((date_uri, BASE.hasCalendarDate, Literal(formatted_date, datatype=XSD.dateTime)))

    # Link Road to District
    g.add((road_uri, BASE.hasDistrict, district_uri))

    # Handle additional properties
    if 'lunghez' in entry:
        g.add((roadarch_uri, BASE.length, Literal(entry['lunghez'], datatype=XSD.decimal)))

# Serialize the updated graph back to a file
output_path = 'rdf/injested_roads.ttl'
filtered_g = Graph()
filtered_g += g
filtered_g.serialize(destination=output_path, format='turtle')

print(f"Ontology updated and saved to {output_path}")
