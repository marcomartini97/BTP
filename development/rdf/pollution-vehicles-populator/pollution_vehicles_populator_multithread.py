import pandas as pd
import os
from tqdm import tqdm
import datetime
import re

from rdflib import Graph, Literal, RDF, RDFS, URIRef, Namespace
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import XSD

# For memory monitoring
import psutil

# For multi-threading
import threading

############################################################################################################

global threads
threads = []

global pbar

print(f'Number of threads: {psutil.cpu_count()}')
print(f'Number of core: {psutil.cpu_count(logical=False)}')

## Datasets

# Set the path to the data
abs_path = os.path.abspath(__file__)
abs_path = os.path.dirname(abs_path)

# Rilevazione flusso datasets
rilevazione_flusso = []
# rilevazione_flusso.append(os.path.join(abs_path, 'datasets\\test\\rilevazione_flusso_veicoli_2019.csv'))
rilevazione_flusso.append(os.path.join(abs_path, '../../../datasets/csv/rilevazione_flusso_veicoli_2019.csv'))
rilevazione_flusso.append(os.path.join(abs_path, '../../../datasets/csv/rilevazione_flusso_veicoli_2020.csv'))
rilevazione_flusso.append(os.path.join(abs_path, '../../../datasets/csv/rilevazione_flusso_veicoli_2021.csv'))
rilevazione_flusso.append(os.path.join(abs_path, '../../../datasets/csv/rilevazione_flusso_veicoli_2022.csv'))

# Accuratezza spire datasets 
accuratezza_spire = []
# accuratezza_spire.append(os.path.join(abs_path, 'datasets\\test\\accuratezza_spire_2019.csv'))
accuratezza_spire.append(os.path.join(abs_path, '../../../datasets/csv/accuratezza_spire_2019.csv'))
accuratezza_spire.append(os.path.join(abs_path, '../../../datasets/csv/accuratezza_spire_2020.csv'))
accuratezza_spire.append(os.path.join(abs_path, '../../../datasets/csv/accuratezza_spire_2021.csv'))
accuratezza_spire.append(os.path.join(abs_path, '../../../datasets/csv/accuratezza_spire_2022.csv'))

# Centraline qualità datasets
centraline = []
# centraline.append(os.path.join(abs_path, 'datasets\\test\\dati_centraline_2019.csv'))
centraline.append(os.path.join(abs_path, '../../../datasets/csv/dati_centraline_2019.csv'))
centraline.append(os.path.join(abs_path, '../../../datasets/csv/dati_centraline_2020.csv'))
centraline.append(os.path.join(abs_path, '../../../datasets/csv/dati_centraline_2021.csv'))
centraline.append(os.path.join(abs_path, '../../../datasets/csv/dati_centraline_2022.csv'))

# Save path
global save_path
save_path = os.path.join(abs_path, 'rdf')

# Temporary path
global temp_path
temp_path = os.path.join(abs_path, 'temp')

# Chunksize (aviod memory error)
chunksize = 200

# Define the Namespace
global BTP
BTP = Namespace("http://www.dei.unipd.it/~gdb/ontology/btp/")

# Pollution coils geopoint -> from google maps!
global viaChiarini_gp, giardiniMargherita_gp, portaSanFelice_gp
viaChiarini_gp = [44.4997732567231, 11.2873095406444]
giardiniMargherita_gp = [44.4830615285162, 11.3528830371546] # via Medaro Bottonelli
portaSanFelice_gp = [44.4991470592725, 11.3270506316853]

############################################################################################################

def clear_threads():
    for thread in threads:
        if not thread.is_alive():
            threads.remove(thread)

# Function to save a graph - multi-threading
def save_graph(graph, path):
    with open(path, 'w') as file:
        # Save the graph using the longturtle format to speed up the process of serialization (still a .ttl file)
        file.write(graph.serialize(format='longturtle'))
    # Remove the threads from the active list of threads
    clear_threads()

############################################################################################################

# Function to populate the coils dataset
def coils_process_chunk(chunk, piece, year_dataset):
    # Graph
    g_coils = Graph()

    # Bind Namespaces
    g_coils.bind("xsd", XSD)
    g_coils.bind("btp", BTP)

    for index, row in chunk.iterrows():

        # I check if the record is valid or not -> must have all the field not NaN
        if row['Livello'] == '' or row['tipologia'] == '':
            # I skip the record -> next record
            continue
        
        # else: is valid -> continue

        codice_arco = str(row['codice arco'])

        # If the codice arco is '' -> Nan, I try to find the codice arco associated to the road
        if(row['codice arco'] == ''):
            # Call the function to check if exists
            codice_arco = get_arch_by_road(row['Nome via'])
            if codice_arco == '':
                # I skip the record -> next record
                continue

        ## COIL:
        # -uri: coil_ + id number.
        # -attributi: hasID
        # -object properties: hasLevel, hasType, isOn, and isPlacedOn.

        Coil = URIRef(BTP["coil_"+str(row['ID_univoco_stazione_spira'])])

        # PollutionCoils and SimpleCoils are subclasses of Coil
        g_coils.add((BTP.SimpleCoil, RDFS.subClassOf, BTP.Coil))
        g_coils.add((BTP.PollutionCoil, RDFS.subClassOf, BTP.Coil))

        # Cast to float
        latitudine = row['latitudine']
        longitudine = row['longitudine']

        if(type(latitudine) == str):
            latitudine = latitudine.replace(',', '')
            # From 113473933293812,00 to 11.3473933293812
            latitudine = latitudine[:2] + '.' + latitudine[2:]
            # Cast to float
            latitudine = float(latitudine)
        if(type(longitudine) == str):
            longitudine = longitudine.replace(',', '')
            # From 44500438455000,00 to 44.500438455000
            longitudine = longitudine[:2] + '.' + longitudine[2:]
            longitudine = float(longitudine)

        # Pollution coils -> must be around 300 m
        if ((latitudine <= viaChiarini_gp[0] + 0.0027) and (latitudine >= viaChiarini_gp[0] + 0.0027)) and ((longitudine <= viaChiarini_gp[1] + 0.0013) and (longitudine >= viaChiarini_gp[1] - 0.0013)):
            g_coils.add((Coil, RDF.type, BTP.PollutionCoil))
            PollutionStation = URIRef(BTP["controlUnitViaChiarini"])
            g_coils.add((PollutionStation, RDF.type, BTP.PollutionStation))
            g_coils.add((PollutionStation, BTP.isNearTo, Coil))
        elif ((latitudine <= giardiniMargherita_gp[0] + 0.0027) and (latitudine >= giardiniMargherita_gp[0] + 0.0027)) and ((longitudine <= giardiniMargherita_gp[1] + 0.0013) and (longitudine >= giardiniMargherita_gp[1] - 0.0013)):
            g_coils.add((Coil, RDF.type, BTP.PollutionCoil))
            PollutionStation = URIRef(BTP["controlUnitGiardiniMargherita"])
            g_coils.add((PollutionStation, RDF.type, BTP.PollutionStation))
            g_coils.add((PollutionStation, BTP.isNearTo, Coil))
        elif ((latitudine <= portaSanFelice_gp[0] + 0.0027) and (latitudine >= portaSanFelice_gp[0] + 0.0027)) and ((longitudine <= portaSanFelice_gp[1] + 0.0013) and (longitudine >= portaSanFelice_gp[1] - 0.0013)):
            g_coils.add((Coil, RDF.type, BTP.PollutionCoil))
            PollutionStation = URIRef(BTP["controlUnitPortaSanFelice"])
            g_coils.add((PollutionStation, RDF.type, BTP.PollutionStation))
            g_coils.add((PollutionStation, BTP.isNearTo, Coil))
        else:
            g_coils.add((Coil, RDF.type, BTP.SimpleCoil))


        for i in range(2, 26):
            date_obj = datetime.datetime.strptime(str(row['data']), '%Y-%m-%d')
            VehicleDetection = URIRef(BTP["vehicleDetection_"+str(row['ID_univoco_stazione_spira'])+"_"+date_obj.strftime('%Y-%m-%d')+"_"+str(i-2).zfill(2)+":00-"+str(i-1).zfill(2)+":00"])
            g_coils.add((VehicleDetection, RDF.type, BTP.VehicleDetection))

            g_coils.add((VehicleDetection, BTP.isObserved, Coil))
            g_coils.add((Coil, BTP.hasObserve, VehicleDetection))

        ################################################################

        Level = URIRef(BTP["level_"+str(int(row['Livello']))])
        g_coils.add((Level, RDF.type, BTP.Level))
        g_coils.add((Coil, BTP.hasLevel, Level))

        Type = URIRef(BTP["type_"+str(row['tipologia'])])
        g_coils.add((Type, RDF.type, BTP.Type))
        g_coils.add((Coil, BTP.hasType, Type))

        g_coils.add((Coil, BTP.hasID, Literal(str(row['codice spira']), datatype=XSD.string)))

        # Road here can't be empty
        RoadArch = URIRef(BTP["road_"+codice_arco])
        g_coils.add((Coil, BTP.isOn, RoadArch))
        g_coils.add((RoadArch, BTP.isPlacedOn, Coil))
    
    # Save the graph
    save_graph(g_coils, temp_path+'/coils_populated_'+year_dataset+'_'+str(piece)+'.ttl')

    pbar.update(len(chunk))

############################################################################################################

# Function that populates the vehicle count dataset
def vehicle_count_process_chunk(chunk, piece, year_dataset):

    # Graph
    g_vc = Graph()

    # Bind Namespaces
    g_vc.bind("xsd", XSD)
    g_vc.bind("btp", BTP)

    for index, row in chunk.iterrows():

        # I check if the record is valid or not -> must have all the field not NaN
        if row['Livello'] == '' or row['tipologia'] == '':
            # I skip the record -> next record
            continue
        # else: is valid -> continue

        for i in range(2, 26):

            ## VEHICLEDETECTION:
            # -uri: vehicleDetection_ + id number + _ + date.
            # -attributi: hasCount.
            # -object properties: isObserved, hasObserve, isObservedOnPeriod, and hasObservedOnPeriod.

            date_obj = datetime.datetime.strptime(str(row['data']), '%Y-%m-%d')
            VehicleDetection = URIRef(BTP["vehicleDetection_"+str(row['ID_univoco_stazione_spira'])+"_"+date_obj.strftime('%Y-%m-%d')+"_"+str(i-2).zfill(2)+":00-"+str(i-1).zfill(2)+":00"])
            g_vc.add((VehicleDetection, RDF.type, BTP.VehicleDetection))

            g_vc.add((VehicleDetection, BTP.hasCount, Literal(row.iloc[i], datatype=XSD.integer)))

            # # PERIOD:
            # -uri: period_ + date + _ + hour1 + _ + hour2.
            # -attributi: startTime and endTime.
            # -object properties: onDay.

            date_obj = datetime.datetime.strptime(str(row['data']), '%Y-%m-%d')
            Period = URIRef(BTP["period_"+date_obj.strftime('%Y-%m-%d')+"_"+str(i-2).zfill(2)+":00-"+str(i-1).zfill(2)+":00"])
            g_vc.add((Period, RDF.type, BTP.Period))

            g_vc.add((Period, BTP.isObservedOnPeriod, VehicleDetection))
            g_vc.add((VehicleDetection, BTP.hasObservedOnPeriod, Period))

            startTime = str(i-2).zfill(2)+":00"
            date_obj = datetime.datetime.strptime(str(row['data']), '%Y-%m-%d')

            g_vc.add((Period, BTP.startTime, Literal(date_obj.strftime('%Y-%m-%d')+"T"+startTime, datatype=XSD.dateTime)))

            endTime = str(i-1).zfill(2)+":00"

            # If the endTime is 24 -> date+1 and endTime = 00
            if(endTime == '24:00'):
                endTime = '00:00'
                # I add one day
                date_obj = date_obj + datetime.timedelta(days=1)

            g_vc.add((Period, BTP.endTime, Literal(date_obj.strftime('%Y-%m-%d')+"T"+endTime, datatype=XSD.dateTime)))

            ## Convert day from italian to english ex: lunedì -> monday
            day_value = ''
            if 'Giorno della settimana' in row:
                day_value = str(row['Giorno della settimana']).lower()
            elif 'giorno della settimana' in row:
                day_value = str(row['giorno della settimana']).lower()

            match day_value:
                case 'lunedì':
                    DayWeek = URIRef(BTP["Monday"])
                    g_vc.add((DayWeek, RDF.type, BTP.DayWeek))
                    g_vc.add((Period, BTP.onDay, DayWeek))
                case 'martedì':
                    DayWeek = URIRef(BTP["Tuesday"])
                    g_vc.add((DayWeek, RDF.type, BTP.DayWeek))
                    g_vc.add((Period, BTP.onDay, DayWeek))
                case 'mercoledì':
                    DayWeek = URIRef(BTP["Wednesday"])
                    g_vc.add((DayWeek, RDF.type, BTP.DayWeek))
                    g_vc.add((Period, BTP.onDay, DayWeek))
                case 'giovedì':
                    DayWeek = URIRef(BTP["Thursday"])
                    g_vc.add((DayWeek, RDF.type, BTP.DayWeek))
                    g_vc.add((Period, BTP.onDay, DayWeek))
                case 'venerdì':
                    DayWeek = URIRef(BTP["Friday"])
                    g_vc.add((DayWeek, RDF.type, BTP.DayWeek))
                    g_vc.add((Period, BTP.onDay, DayWeek))
                case 'sabato':
                    DayWeek = URIRef(BTP["Saturday"])
                    g_vc.add((DayWeek, RDF.type, BTP.DayWeek))
                    g_vc.add((Period, BTP.onDay, DayWeek))
                case 'domenica':
                    DayWeek = URIRef(BTP["Sunday"])
                    g_vc.add((DayWeek, RDF.type, BTP.DayWeek))
                    g_vc.add((Period, BTP.onDay, DayWeek))
                case _:
                    # No day provided
                    pass
    
    # Save the graph
    save_graph(g_vc, temp_path+'/vehicle_count_populated_'+year_dataset+'_'+str(piece)+'.ttl')

    pbar.update(len(chunk))

############################################################################################################

# Function that populates the vehicle accuracy dataset
def vehicle_accuracy_process_chunk(chunk, piece, year_dataset):

    # Graphs
    g_acc = Graph()

    # Bind Namespaces
    g_acc.bind("xsd", XSD)
    g_acc.bind("btp", BTP)

    for index, row in chunk.iterrows():

        for i in range(2, 26):

            ## VEHICLEDETECTION:
            # -uri: vehicleDetection_ + id number + _ + date.
            # -attributi: hasAccuracy, and hasCount.

            coil = ''

            # Query to get the coil's code associated to an ID
            coil = get_coil_by_id(str(row['codice spira']))
            if coil == '':
                # I skip the record -> next record
                continue

            date_obj = datetime.datetime.strptime(str(row['data']), '%Y-%m-%d')

            VehicleDetection = URIRef(BTP["vehicleDetection_"+coil+"_"+date_obj.strftime('%Y-%m-%d')+"_"+str(i-2).zfill(2)+":00-"+str(i-1).zfill(2)+":00"])
            g_acc.add((VehicleDetection, RDF.type, BTP.VehicleDetection))
            percentage = row.iloc[i].replace('%', '')
            g_acc.add((VehicleDetection, BTP.hasAccuracy, Literal(float(percentage), datatype=XSD.float)))

            # # PERIOD:
            # -uri: period_ + date + _ + hour1 + _ + hour2.
            # -attributi: startTime and endTime.
            # -object properties: onDay.

            Period = URIRef(BTP["period_"+date_obj.strftime('%Y-%m-%d')+"_"+str(i-2).zfill(2)+":00-"+str(i-1).zfill(2)+":00"])
            g_acc.add((Period, RDF.type, BTP.Period))

            g_acc.add((Period, BTP.isObservedOnPeriod, VehicleDetection))
            g_acc.add((VehicleDetection, BTP.hasObservedOnPeriod, Period))

            startTime = str(i-2).zfill(2)+":00"
            date_obj = datetime.datetime.strptime(str(row['data']), '%Y-%m-%d')

            g_acc.add((Period, BTP.startTime, Literal(date_obj.strftime('%Y-%m-%d')+"T"+startTime, datatype=XSD.dateTime)))

            endTime = str(i-1).zfill(2)+":00"

            # If the endTime is 24 -> date+1 and endTime = 00
            if(endTime == '24:00'):
                endTime = '00:00'
                # I add one day
                date_obj = date_obj + datetime.timedelta(days=1)

            g_acc.add((Period, BTP.endTime, Literal(date_obj.strftime('%Y-%m-%d')+"T"+endTime, datatype=XSD.dateTime)))

    # Save the graph
    save_graph(g_acc, 'rdf/vehicle_accuracy_populated_'+year_dataset+'_'+str(piece)+'.ttl')

    pbar.update(len(chunk))

############################################################################################################

# Function that populates the pollution data
def pollution_process_chunk(chunk, piece, year_dataset):

    # Graphs
    g_pol = Graph()

    # Bind Namespaces
    g_pol.bind("xsd", XSD)
    g_pol.bind("btp", BTP)

    for index, row in chunk.iterrows():

        ## POLLUTIONSTATION:
        # -uri: centralUnit + pollution name.
        # -object properties: hasRegister, and isRegistered.

        PollutionStation = URIRef(BTP["controlUnit" + (str(row['COD_STAZ']).lower()).replace(" ", "")])
        g_pol.add((PollutionStation, RDF.type, BTP.PollutionStation))

        # PERIOD:
        # -uri: period_ + date + _ + hour1 + _ + hour2.
        # -attributi: startTime and endTime.
        # -object properties: onDay.

        # date format: yyyy-mm-ddThh:mm:ss+hh:mm
        # keep only the data: 'Thh:mm:ss+hh:mm' -> yyyy-mm-dd
        date_obj = datetime.datetime.strptime((str(row['DATA_INIZIO']).split('T'))[0], '%Y-%m-%d')
        # keep only the hour: 'Thh:mm:ss+hh:mm' -> hh:mm:ss
        startTime = str((((str(row['DATA_INIZIO']).split('T'))[1].split('+')[0]).split(':'))[0])+":00"
        endTime = str((((str(row['DATA_FINE']).split('T'))[1].split('+')[0]).split(':'))[0])+":00"
        Period = URIRef(BTP["period_"+date_obj.strftime('%Y-%m-%d')+"_"+startTime+"-"+endTime])

        g_pol.add((Period, RDF.type, BTP.Period))
        g_pol.add((Period, BTP.startTime, Literal(date_obj.strftime('%Y-%m-%d')+"T"+startTime, datatype=XSD.dateTime)))
        g_pol.add((Period, BTP.endTime, Literal(date_obj.strftime('%Y-%m-%d')+"T"+endTime, datatype=XSD.dateTime)))

        ## CHEMICALDETECTION:
        # -uri: chemicalDetection_ + pollution_station_name + _ + date + _ + element.
        # -attributi: inQuantity (conversion all in ug/m), and hasChemicalName.
        # -object properties: isDetectedOnPeriod, hasDetectedOnPeriod, hasDetect, and isDetected.

        chemical_element = (row['AGENTE'].split("(")[0]).strip()
        ChemicalElement = URIRef(BTP["chemicalElement_"+chemical_element])

        date_obj = datetime.datetime.strptime((str(row['DATA_INIZIO']).split('T'))[0], '%Y-%m-%d')
        ChemicalDetection = URIRef(BTP["chemicalDetection_"+(str(row['COD_STAZ']).lower()).replace(" ", "")+"_"+date_obj.strftime('%Y-%m-%d')+"_"+startTime+"-"+endTime+"_"+chemical_element])
        g_pol.add((ChemicalDetection, RDF.type, BTP.ChemicalDetection))

        # Cast from mg/m^3 to ug/m^3
        if(row['UM'] == 'mg/m3'):
            g_pol.add((ChemicalDetection, BTP.inQuantity, Literal((row['VALORE']*1000), datatype=XSD.float)))
        else:
            g_pol.add((ChemicalDetection, BTP.inQuantity, Literal((row['VALORE']), datatype=XSD.float)))

        ## CHEMICALELEMENT:
        # -uri: chemicalElement_ + chemical element name.
        # -object properties: hasDetect, and isDetected

        g_pol.add((ChemicalElement, RDF.type, BTP.ChemicalElement))
        g_pol.add((ChemicalDetection, BTP.hasDetect, ChemicalElement))
        g_pol.add((ChemicalElement, BTP.isDetected, ChemicalDetection))

        if len(row['AGENTE'].split("(")) > 1:
            chemical_element_name = (((row['AGENTE'].split("(")[1]).replace(")","")).strip()).lower()

            match chemical_element_name:
                case 'benzene':
                    g_pol.add((ChemicalDetection, BTP.hasChemicalName, Literal("Benzene", datatype=XSD.string)))
                case 'monossido di carbonio':
                    g_pol.add((ChemicalDetection, BTP.hasChemicalName, Literal("Carbon monoxide", datatype=XSD.string)))
                case 'monossido di azoto':
                    g_pol.add((ChemicalDetection, BTP.hasChemicalName, Literal("Nitrogen Monoxide", datatype=XSD.string)))
                case 'biossido di azoto':
                    g_pol.add((ChemicalDetection, BTP.hasChemicalName, Literal("Nitrogen dioxide", datatype=XSD.string)))
                case 'ossidi di azoto':
                    g_pol.add((ChemicalDetection, BTP.hasChemicalName, Literal("Nitrogen oxides", datatype=XSD.string)))
                case 'ozono':
                    g_pol.add((ChemicalDetection, BTP.hasChemicalName, Literal("Ozone", datatype=XSD.string)))
                case _:
                    # New element provided
                    g_pol.add((ChemicalDetection, BTP.hasChemicalName, Literal(chemical_element_name, datatype=XSD.string)))

    # Save the graph
    save_graph(g_pol, temp_path+'/pollution_station_populated_'+year_dataset+'_'+str(piece)+'.ttl')

    pbar.update(len(chunk))

############################################################################################################

def merge_graph(regex, name_file):
    merged_graph = Graph()

    merged_graph.bind('btp', BTP)
    merged_graph.bind('rdfs', RDFS)

    files = [f for f in os.listdir(temp_path) if regex.match(f)]
    total_lenght = len(files)
    pbar = tqdm(total=total_lenght)

    for filename in files:
        temp = Graph()
        temp.parse(os.path.join(temp_path, filename), format='turtle')
        # Add all triples to the merged graph as: subject, predicate, object
        merged_graph += temp
        del temp
        pbar.update(1)

    pbar.close()
    
    # Save the merged graph using the longturtle format to speed up the process of serialization
    merged_graph.serialize(destination=os.path.join(save_path, name_file), format='longturtle')

    # Remove all the partial files in the directory (temp_path)
    for filename in os.listdir(temp_path):
        if regex.match(filename):
            os.remove(os.path.join(temp_path, filename))

############################################################################################################

def get_arch_by_road(road_name):

    # TODO: Add the road.ttl file
    return ''
    ############################################

    #Graph
    g_road = Graph()
    g_road.parse(os.path.join(save_path, 'road.ttl'), format='turtle')

    # Query to get the arc's code associated to a road
    arc_query = prepareQuery("""
        SELECT DISTINCT ?arc WHERE {
            ?arc btp:hasRoad ?road .
        FILTER (?road = ?road_name)
                                }""" , initNs={"btp": BTP})
    
    res = g_road.query(arc_query, initBindings={'road_name':Literal(road_name, datatype=XSD.string)})
    if res == [] or res == None:
        return ''
    else:
        for r in res:
            return str(r.arc).replace('http://www.dei.unipd.it/~gdb/ontology/btp/arc_', '')

############################################################################################################

def get_coil_by_id(coil_id):
    # Graph
    g_coils = Graph()
    g_coils.parse(os.path.join(save_path, 'coils_populated.ttl'), format='turtle')

    code_coil_query = prepareQuery("""
    SELECT DISTINCT ?coil WHERE {
        ?coil btp:hasID ?id .
    FILTER (?id = ?coil_id)
                               }""" , initNs={"btp": BTP})
    
    res = g_coils.query(code_coil_query, initBindings={'coil_id':Literal(coil_id, datatype=XSD.string)})
    if res == [] or res == None:
        return ''
    else:
        for r in res:
            return str(r.coil).replace('http://www.dei.unipd.it/~gdb/ontology/btp/coil_', '')

############################################################################################################

# I check if the folder is empty or not
if not os.listdir(save_path) == []:
    print("The folder is not empty, do you want to continue? (y/n)")
    answer = input()
    if(answer.lower() == 'y'):
        # I remove all the files in the folders
        print("Removing all the files in the folder ...")
        for file in os.listdir(save_path):
            os.remove(os.path.join(save_path, file))
        for file in os.listdir(temp_path):
            os.remove(os.path.join(temp_path, file))
        print("DONE!")
    else:
        exit()

############################################################################################################

print("--- populating coils ---")

for namefile in rilevazione_flusso:

    year_dataset = namefile.split('_')[3].split('.')[0]
    piece = 0

    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)

    test_iter = 10

    for chunk in pd.read_csv(namefile, sep=';', chunksize=chunksize):
        
        # Manage NaN values
        chunk = chunk.fillna('')

        if test_iter == 0:
            break

        # Memory monitor
        if psutil.virtual_memory().percent > 80 or len(threads) == psutil.cpu_count():
            # I'm using more than 70% of the whole RAM or I'm using all the threads
            for thread in threads:
                thread.join()
                # At least one thread is now available
                break

        test_iter -= 1
        
        # I can start a new thread
        thread = threading.Thread(target=coils_process_chunk, args=(chunk, piece, year_dataset))
        thread.start()
        threads.append(thread)
        piece+=1
      
    for thread in threads:
        thread.join()

    pbar.close()

############################################################################################################

print("--- merging coils ---")

regex = re.compile(r'coils_populated_\d{4}_\d+\.ttl')
merge_graph(regex, 'coils_populated.ttl')

print("--- merging done ---")

############################################################################################################

print("--- populating vehicle count ---")

for namefile in rilevazione_flusso:

    year_dataset = namefile.split('_')[3].split('.')[0]
    piece = 0

    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)

    test_iter = 10

    for chunk in pd.read_csv(namefile, sep=';', chunksize=chunksize):

        # Manage NaN values
        chunk = chunk.fillna('')

        if test_iter == 0:
            break

        # Memory monitor
        if psutil.virtual_memory().percent > 80 or len(threads) == psutil.cpu_count():
            # I'm using more than 70% of the whole RAM or I'm using all the threads
            for thread in threads:
                thread.join()
                # At least one thread is now available
                break

        test_iter -= 1
        
        # I can start a new thread
        thread = threading.Thread(target=vehicle_count_process_chunk, args=(chunk, piece, year_dataset))
        thread.start()
        threads.append(thread)
        piece+=1
        
        pbar.update(chunksize)

    for thread in threads:
        thread.join()

    pbar.close()

############################################################################################################

print("--- merging vehicle count ---")

regex = re.compile(r'vehicle_count_populated_\d{4}_\d+\.ttl')
merge_graph(regex, 'vehicle_count_populated.ttl')

print("--- merging done ---")

############################################################################################################

print("--- populating vehicle accuracy ---")

for namefile in accuratezza_spire:

    year_dataset = namefile.split('/')[-1].split('_')[2].split('.')[0]
    piece = 0

    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)

    test_iter = 10

    for chunk in pd.read_csv(namefile, sep=';', chunksize=chunksize):

        # Manage NaN values
        chunk = chunk.fillna('')

        if test_iter == 0:
            break

        # Memory monitor
        if psutil.virtual_memory().percent > 80 or len(threads) == psutil.cpu_count():
            # I'm using more than 70% of the whole RAM or I'm using all the threads
            for thread in threads:
                thread.join()
                # At least one thread is now available
                break

        test_iter -= 1
        
        # I can start a new thread
        thread = threading.Thread(target=vehicle_accuracy_process_chunk, args=(chunk, piece, year_dataset))
        thread.start()
        threads.append(thread)
        piece+=1

    for thread in threads:
        thread.join()

    pbar.close()

############################################################################################################

print("--- merging vehicles accuracy ---")

regex = re.compile(r'vehicle_accuracy_populated_\d{4}_\d+\.ttl')
merge_graph(regex, 'vehicle_accuracy_populated.ttl')

print("--- merging done ---")

############################################################################################################

print("--- populating pollution data ---")

for namefile in centraline:

    year_dataset = namefile.split('/')[-1].split('_')[2].split('.')[0]
    piece = 0

    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)

    test_iter = 10

    for chunk in pd.read_csv(namefile, sep=';', chunksize=chunksize):

        # Manage NaN values
        chunk = chunk.fillna('')

        if test_iter == 0:
            break

        # Memory monitor
        if psutil.virtual_memory().percent > 80 or len(threads) == psutil.cpu_count():
            # I'm using more than 70% of the whole RAM or I'm using all the threads
            for thread in threads:
                thread.join()
                # At least one thread is now available
                break

        test_iter -= 1

        # I can start a new thread
        thread = threading.Thread(target=pollution_process_chunk, args=(chunk, piece, year_dataset))
        thread.start()
        threads.append(thread)
        piece+=1

    for thread in threads:
        thread.join()

    pbar.close()

############################################################################################################

print("--- merging pollution data ---")

regex = re.compile(r'pollution_station_populated_\d{4}_\d+\.ttl')
merge_graph(regex, 'pollution_station_populated.ttl')

print("--- merging done ---")

############################################################################################################

print("--- end ---")