import json
from datetime import datetime
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import RDFS, XSD
from tqdm import tqdm
import re

# Load the ontology from git folder
ontology_path = '../../../ontology/btp-ontology.ttl'
btp = Graph()
btp.parse(ontology_path, format='turtle')

g = Graph()

# Define namespaces
BASE = Namespace("http://www.dei.unipd.it/~gdb/ontology/btp/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
btp.bind("", BASE)
g.bind("", BASE)
g.bind("owl", OWL)

# Add Ontology definition
g.add((BASE["asserted"], RDF.type, OWL.Ontology))

# Load the JSON file from git folder
json_file_path = '../../../datasets/json/rifter_arcstra_li.json'
with open(json_file_path, 'r') as f:
    json_data = json.load(f)

def get_first_word_lower(s):
    return s.split()[0].lower() if s else ''


def to_camel_case(s):
    s = re.sub(r'[-/]', '', s)
    s = re.sub(r'[^a-zA-Z0-9]', ' ', s).title().replace(' ', '')
    return s[0].lower() + s[1:] if s else ''

# Create a hashmap for nomevia to codvia
road_map = {entry['nomevia']: entry['codvia'] for entry in json_data}

print(f"Processing JSON data from: {ontology_path} ... ")
p_bar = tqdm(total=len(json_data))

# Add all Object properties
g.add((BASE.hasRoadType, RDF.type, OWL.ObjectProperty))
g.add((BASE.hasNode, RDF.type, OWL.ObjectProperty))
g.add((BASE.hasDistrict, RDF.type, OWL.ObjectProperty))
g.add((BASE.hasDeploymentDate, RDF.type, OWL.ObjectProperty))
g.add((BASE.isArchFromRoad, RDF.type, OWL.ObjectProperty))
g.add((BASE.isArchToRoad, RDF.type, OWL.ObjectProperty))

# Add all Data properties
g.add((BASE.hasCalendarDate, RDF.type, OWL.DatatypeProperty))
g.add((BASE.length, RDF.type, OWL.DatatypeProperty))

# Process each JSON entry
for entry in json_data:
    # Create URIs for Roads, RoadArch, Districts, and RoadNodes
    road_uri = BASE[f"road_{entry['codvia']}"]
    roadarch_uri = BASE[f"roadarch_{entry['codarco']}"]
    district_uri = BASE[to_camel_case(entry['nomequart'])]
    date_uri = BASE[f"date_{entry['data_istit']}"]
    node_1_uri = BASE[f"roadnode_{entry['cod_nodo1']}"]
    node_2_uri = BASE[f"roadnode_{entry['cod_nodo2']}"]
    roadtype_uri = BASE[f"roadtype_{get_first_word_lower(entry['nomevia'])}"]

    # Add Node class
    g.add((node_1_uri, RDF.type, BASE.RoadNode))
    g.add((node_2_uri, RDF.type, BASE.RoadNode))

    # Add Road class and its properties
    g.add((road_uri, RDF.type, BASE.Road))
    g.add((road_uri, RDFS.label, Literal(entry['nomevia'], lang='it')))
    if(roadtype_uri, RDF.type, BASE.RoadType) in btp:
        g.add((road_uri, BASE.hasRoadType, roadtype_uri));
    else:
        g.add((road_uri, BASE.hasRoadType, BASE["roadtype_undefined"]));


    # Add RoadArch class and link to Road
    g.add((roadarch_uri, RDF.type, BASE.RoadArch))
    g.add((roadarch_uri, BASE.hasNode, node_1_uri))
    g.add((roadarch_uri, BASE.hasNode, node_2_uri))
    g.add((roadarch_uri, BASE.length, Literal(entry['lunghez'], datatype=XSD.decimal)))
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

    # Update progress bar
    p_bar.update(1)

p_bar.close()

# Serialize the updated graph back to a file
output_path = 'rdf/injested_roads.ttl'
print(f"Saving graph to {output_path}")

g.serialize(destination=output_path, format='turtle')

print(f"Ontology updated and saved to {output_path}")
