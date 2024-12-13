#Import libraries
import os
import json
from rdflib import Graph, URIRef, Literal, RDF, Namespace
from rdflib.namespace import XSD
from pathlib import Path

# Read JSON file

json_file_path = "C:/Users/alibk/Desktop/UNIVERSITY/5th Semster/DataBase/Proj/data/roadAccident.json"


# Define namespaces
BTP = Namespace("http://www.dei.unipd.it/~gdb/ontology/btp/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
RDF_NS = RDF
XSD_NS = XSD

# Create RDF graph
g = Graph()
g.bind("btp", BTP)
g.bind("rdf", RDF_NS)
g.bind("xsd", XSD_NS)


try:
    with open(json_file_path, 'r') as file:
        road_accidents = json.load(file)
        assert road_accidents, "Road accidents data is empty. Check the JSON file."
except (FileNotFoundError, AssertionError, json.JSONDecodeError) as e:
    print(f"Error reading JSON file: {e}")
    exit()

print("Road accidents JSON file read successfully.")

# Clean JSON data
for accident in road_accidents:
    if 'nomequart' in accident and accident['nomequart']:
        accident['nomequart'] = ''.join(
            word.capitalize() if idx > 0 else word.lower()
            for idx, word in enumerate(accident['nomequart'].replace('-', ' ').split())
        )
    if 'nomezona' in accident and accident['nomezona']:
        accident['nomezona'] = ''.join(
            word.capitalize() if idx > 0 else word.lower()
            for idx, word in enumerate(accident['nomezona'].replace('-', ' ').split())
        )

print("JSON data cleaned.")

# Define mappings for subclasses
subclass_mappings = {
    "Driver": {
        "rdf_type": BTP.Driver,
        "properties": {
            'n_autist_m': BTP.numberOfDriverDeath,
            'n_autist_f': BTP.numberOfDriverInjuries
        }
    },
    "Scooter": {
        "rdf_type": BTP.Scooter,
        "properties": {
            'n_monop_m': BTP.numberOfScooterDeath,
            'n_monop_f': BTP.numberOfScooterInjuries
        }
    },
    "Cyclist": {
        "rdf_type": BTP.Cyclist,
        "properties": {
            'n_cicl_m': BTP.numberOfCyclistsDeath,
            'n_cicl_f': BTP.numberOfCyclistsInjuries
        }
    },
    "Pedestrain": {
        "rdf_type": BTP.Pedestrain,
        "properties": {
            'n_pedoni_m': BTP.numberOfPedestrainDeath,
            'n_pedoni_f': BTP.numberOfPedestrainInjuries
        }
    },
    "Motorcyclist": {
        "rdf_type": BTP.Motorcyclist,
        "properties": {
            'n_motoc_m': BTP.numberOfMotorcyclistsDeath,
            'n_motoc_f': BTP.numberOfMotorcyclistsInjuries
        }
    }
}

# Process JSON data
for idx, accident in enumerate(road_accidents):
    accident_id = f"accident_{idx}"
    Accident = URIRef(BTP[accident_id])
    g.add((Accident, RDF.type, BTP.RoadAccident))

    # Add general properties for RoadAccident
    if 'totale_mor' in accident:
        g.add((Accident, BTP.totalNumberOfDeath, Literal(accident['totale_mor'], datatype=XSD.integer)))
    if 'totale_fer' in accident:
        g.add((Accident, BTP.totalNumberOfInjuries, Literal(accident['totale_fer'], datatype=XSD.integer)))
    if 'n_incident' in accident:
        g.add((Accident, BTP.numberOfAccidents, Literal(accident['n_incident'], datatype=XSD.integer)))

    # Map 'anno' to the Year
    if 'anno' in accident and accident['anno']:
        year_uri = URIRef(BTP[f"year_{accident['anno']}"])
        g.add((year_uri, RDF.type, BTP.Year))
        g.add((year_uri, BTP.hasYear, Literal(accident['anno'], datatype=XSD.integer)))
        g.add((Accident, BTP.hasAccidentYear, year_uri))

    # Map 'nomezona' to proximity area
    if 'nomezona' in accident and accident['nomezona']:
        zone_uri = URIRef(BTP[accident['nomezona']])
        g.add((Accident, BTP.happendInArea, zone_uri))

    # Map 'nomequart' to district
    if 'nomequart' in accident and accident['nomequart']:
        district_uri = URIRef(BTP[accident['nomequart']])
        g.add((Accident, BTP.recordedInDistrict, district_uri))

    # Process each subclass
    for subclass_name, subclass_info in subclass_mappings.items():
        subclass_id = f"{subclass_name.lower()}Accident_{idx}"
        SubclassAccident = URIRef(BTP[subclass_id])
        g.add((SubclassAccident, RDF.type, subclass_info["rdf_type"]))

        # Map 'anno' to the Year for subclass instance
        if 'anno' in accident and accident['anno']:
            g.add((SubclassAccident, BTP.hasAccidentYear, year_uri))

        # Map 'nomezona' to proximity area for subclass instance
        if 'nomezona' in accident and accident['nomezona']:
            g.add((SubclassAccident, BTP.happendInArea, zone_uri))

        # Map 'nomequart' to district for subclass instance
        if 'nomequart' in accident and accident['nomequart']:
            g.add((SubclassAccident, BTP.recordedInDistrict, district_uri))

        # Add subclass-specific properties
        for property_key, property_uri in subclass_info["properties"].items():
            if property_key in accident:
                g.add((SubclassAccident, property_uri, Literal(accident[property_key], datatype=XSD.integer)))


        #Define Obj Properties
        g.add ((BTP.recordedInDistrict, RDF.type, OWL.ObjectProperty))
        g.add ((BTP.happendInArea, RDF.type, OWL.ObjectProperty))
        g.add ((BTP.hasAccidentYear, RDF.type, OWL.ObjectProperty))
        # Define properties for Driver
        g.add((BTP.numberOfDriverDeath, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.numberOfDriverInjuries, RDF.type, OWL.DatatypeProperty))

        # Define properties for Scooter
        g.add((BTP.numberOfScooterDeath, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.numberOfScooterInjuries, RDF.type, OWL.DatatypeProperty))

        # Define properties for Cyclist
        g.add((BTP.numberOfCyclistsDeath, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.numberOfCyclistsInjuries, RDF.type, OWL.DatatypeProperty))

        # Define properties for Pedestrian
        g.add((BTP.numberOfPedestrainDeath, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.numberOfPedestrainInjuries, RDF.type, OWL.DatatypeProperty))

        # Define properties for Motorcyclist
        g.add((BTP.numberOfMotorcyclistsDeath, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.numberOfMotorcyclistsInjuries, RDF.type, OWL.DatatypeProperty))

        # Add general properties for RoadAccident
        g.add((BTP.totalNumberOfDeath, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.totalNumberOfInjuries, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.numberOfAccidents, RDF.type, OWL.DatatypeProperty))
        g.add((BTP.hasYear, RDF.type, OWL.DatatypeProperty))

print("RDF graph mapping completed.")

# Save RDF graph to Turtle file
turtle_file_path = 'MappedRoadAccidents.ttl'

if os.path.exists(turtle_file_path):
    user_input = input(f"The file '{turtle_file_path}' already exists. Do you want to overwrite it? (y/n): ").lower()
    if user_input != 'y':
        print("Serialization not saved. Exiting.")
        exit()

print("--- saving serialization ---")
g.serialize(destination=turtle_file_path, format='turtle')

print(f"RDF data exported to {turtle_file_path}")
print("Serialization saved successfully.")
