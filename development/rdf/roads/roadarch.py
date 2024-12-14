import json
from datetime import datetime
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import RDFS, XSD
from tqdm import tqdm
# For geography
from shapely import intersection, LineString, Point, Polygon, MultiPolygon
import numpy
import unicodedata
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
roads_file_path = '../../../datasets/json/rifter_arcstra_li.json'
speed_file_path = '../../../datasets/json/velocita-citta-30.json'
projects_file_path = '../../../datasets/json/progetti-citta-30.json'

with open(roads_file_path, 'r') as f:
    roads_data = json.load(f)

with open(speed_file_path, 'r') as f:
    speed_data = json.load(f)

with open(projects_file_path, 'r') as f:
    projects_data = json.load(f)

def get_first_word_lower(s):
    return s.split()[0].lower() if s else ''


def to_camel_case(s):
    s = s.replace('/', ' ')
    s = s.replace('-', ' ')
    # Remove accents
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[-/]', '', s)
    s = re.sub(r'[^a-zA-Z0-9]', ' ', s).title().replace(' ', '')
    return s[0].lower() + s[1:] if s else ''

# Create a hashmap for nomevia to codvia
road_map = {entry['nomevia']: entry['codvia'] for entry in roads_data}


def process_roads(roads_data):

    print(f"Processing road JSON data from: {roads_file_path} ... ")
    p_bar = tqdm(total=len(roads_data))
    
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

    # Process each Road JSON entry
    for entry in roads_data:
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
        # Use hashmap in order to map road codes from names
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

def process_speed(speed_data):

    print(f"Processing speed JSON data from: {speed_file_path} ... ")
    # Add Object Property
    g.add((BASE.isSpeedLimit, RDF.type, OWL.ObjectProperty))
    pbar = tqdm(total=len(speed_data))
    for entry  in speed_data:
        # PDF: Apparently datainiz is not about the speed limit like the dataset would imply 
        #      It's about the inauguration date of the road arch, so ImpositionDate is useless
        roadarch_uri = BASE[f"roadarch_{entry['arcstra_id']}"]
        speedlimit_uri = BASE[f"speed{int(entry['vel2024'])}"]
        # Roadarch and speedlimit are already instantiated on the graph (at least the complete one)
        g.add((speedlimit_uri, BASE.isSpeedLimit, roadarch_uri))
        pbar.update(1)

# There are multiple shapes for project
def do_shapes_intersect(proj, arc):
    geometry = proj['geo_shape']['geometry']
    if geometry['type'] == 'Point':
        proj_shape = Point(geometry['coordinates'][:2])
    elif geometry['type'] == 'LineString':
        proj_shape = (LineString(geometry['coordinates']))
    elif geometry['type'] == 'Polygon':
        proj_shape = (Polygon(geometry['coordinates'][0]))
    elif geometry['type'] == 'MultiPolygon':
        proj_shape = MultiPolygon([Polygon(polygon[0]) for polygon in geometry['coordinates']])
    else:
      return False

    geometry = arc['geo_shape']['geometry']
    if geometry['type'] == 'LineString':
        arc_shape = (LineString(geometry['coordinates']))
    elif geometry['type'] == 'Polygon':
        arc_shape = (Polygon(geometry['coordinates'][0]))
    else:
        arc_shape = (Point(geometry['coordinates']))
    return proj_shape.intersects(arc_shape)


def process_projects(projects_data):

    type_entries = []
    zone_entries = []
    for item in projects_data:
        if  'zona' in item and item['zona']:
            zone_entries.append(item['zona'])
        if 'tema_prima' in item and item['tema_prima']:
            type_entries.append(item['tema_prima'])
        if 'tema_secon' in item and item['tema_secon']:
            type_entries.append(item['tema_secon'])
        if 'filone_sec' in item and item['filone_sec']:
            type_entries.append(item['filone_sec'])

    # Create hashmap to parse SKOS
    type_hashmap = {entry: to_camel_case(entry) for entry in set(type_entries)}
    zone_hashmap = {entry: to_camel_case(entry) for entry in set(zone_entries)}

    # Manual fixes for typo
    type_hashmap["Accessibiltà"] = "accessibilita"

    print(f"Processing project JSON data from: {projects_file_path} ... ")
    # Print hashmap
    print(json.dumps(zone_hashmap, indent=4, ensure_ascii=False))
    # Define the properties
    g.add((BASE.isProject, RDF.type, OWL.ObjectProperty))
    g.add((BASE.hasStartYear, RDF.type, OWL.ObjectProperty))
    g.add((BASE.hasProjectType, RDF.type, OWL.ObjectProperty))
    g.add((BASE.hasEndYear, RDF.type, OWL.ObjectProperty))
    g.add((BASE.hasYear, RDF.type, OWL.DatatypeProperty))
    g.add((BASE.hasDescription, RDF.type, OWL.DatatypeProperty))
    g.add((BASE.hasProximityArea, RDF.type, OWL.ObjectProperty))
    g.add((BASE.hasStatus, RDF.type, OWL.DatatypeProperty))

    pbar = tqdm(total=len(projects_data))

    #undefined_code = 0;

    for entry in projects_data:
        project_uri = BASE[f"project_{entry["id"]}"]

        # Some projects can not have an initial date or end
        if entry['inizio_lav']:
            startyear_uri = BASE[f"year_{int(entry['inizio_lav'])}"]
        if entry['fine_lavor']:
            startyear_uri = BASE[f"year_{int(entry['fine_lavor'])}"]

        # Add datatype properties
        g.add((project_uri, RDF.type, BASE.Project30))
        g.add((project_uri, BASE.hasStartYear, startyear_uri))
        g.add((project_uri, BASE.hasDescription, Literal(entry['descrizion'], datatype=XSD.string)))
        g.add((project_uri, BASE.hasStatus, Literal(entry['stato_semp'], datatype=XSD.string)))

        # Add proximity areas
        if(entry['zona'] in zone_hashmap):
            zone_uri = BASE[zone_hashmap[entry['zona']]]
            g.add((project_uri, BASE.hasProximityArea, zone_uri))


        # First check if the project type is instantiated in the graph
        thread_uri = BASE[type_hashmap[entry["filone_sec"]]]
        theme_1_uri =  BASE[type_hashmap[entry["tema_prima"]]]
        theme_2_uri =  BASE[type_hashmap[entry["tema_secon"]]]

        # Note Project types are already instantiated in the ontology, just add the uri
        if ((thread_uri, RDF.type, BASE.ProjectThread)) in btp:
            g.add((project_uri, BASE.hasProjectType, thread_uri))
        else:
            print(f"[WARN] Missing thread: {entry["filone_sec"]}")
        if ((theme_1_uri, RDF.type, BASE.ProjectTheme)) in btp:
            g.add((project_uri, BASE.hasProjectType, theme_1_uri))
        else:
            print(f"[WARN] Missing theme: {entry["tema_prima"]}")
        if ((theme_2_uri, RDF.type, BASE.ProjectTheme)) in btp:
            g.add((project_uri, BASE.hasProjectType, theme_2_uri))
        else:
            print(f"[WARN] Missing theme: {entry["tema_secon"]}")

        # Check if the project is inside an arco stradale, and associate the road through geometric shapes
        for road_entry in roads_data:
            if do_shapes_intersect(entry, road_entry):
                #print(f"Descrizione: {entry['descrizion']}\n{entry['luogo']} intersects: {road_entry['nomevia']}")
                g.add((project_uri, BASE.isProject, BASE[f"road_{road_entry['codvia']}"]))
        pbar.update(1)





# Serialize the updated graph back to a file
process_roads(roads_data)
process_speed(speed_data)
process_projects(projects_data)
output_path = 'rdf/roads.ttl'
print(f"Saving graph to {output_path}")

g.serialize(destination=output_path, format='turtle')

print(f"Ontology updated and saved to {output_path}")
