import pandas as pd
import os
from tqdm import tqdm
import datetime

from rdflib import Graph, Literal, RDF, RDFS, URIRef, Namespace
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import XSD

##############################################################################################################

# Set the path to the data
abs_path = os.path.abspath(__file__)
abs_path = os.path.dirname(abs_path)

## Datasets

# Rilevazione flusso datasets
rilevazione_flusso = []
rilevazione_flusso.append(os.path.join(abs_path, 'datasets\\test\\rilevazione_flusso_veicoli_2019.csv'))
# rilevazione_flusso.append(os.path.join(abs_path, 'datasets\\test\\rilevazione_flusso_veicoli_2020.csv'))
# rilevazione_flusso.append(os.path.join(abs_path, 'datasets\\test\\rilevazione_flusso_veicoli_2021.csv'))
# rilevazione_flusso.append(os.path.join(abs_path, 'datasets\\test\\rilevazione_flusso_veicoli_2022.csv'))

# Accuratezza spire datasets 
accuratezza_spire = []
accuratezza_spire.append(os.path.join(abs_path, 'datasets\\test\\accuratezza_spire_2019.csv'))
# accuratezza_spire.append(os.path.join(abs_path, 'datasets\\test\\accuratezza_spire_2020.csv'))
# accuratezza_spire.append(os.path.join(abs_path, 'datasets\\test\\accuratezza_spire_2021.csv'))
# accuratezza_spire.append(os.path.join(abs_path, 'datasets\\test\\accuratezza_spire_2022.csv'))

# Centraline qualità datasets
centraline = []
centraline.append(os.path.join(abs_path, 'datasets\\test\\dati_centraline_2019.csv'))
# centraline.append(os.path.join(abs_path, 'datasets\\test\\dati_centraline_2020.csv'))
# centraline.append(os.path.join(abs_path, 'datasets\\test\\dati_centraline_2021.csv'))
# centraline.append(os.path.join(abs_path, 'datasets\\test\\dati_centraline_2022.csv'))

# Save path
save_path = os.path.join(abs_path, 'rdf')

chunksize = 50

# Define the Namespace
BTP = Namespace("http://www.dei.unipd.it/~gdb/ontology/btp/#")

# Pollution coils geopoint -> from google maps!
viaChiarini_gp = [44.4997732567231, 11.2873095406444]
giardiniMargherita_gp = [44.4830615285162, 11.3528830371546] # via Medaro Bottonelli
portaSanFelice_gp = [44.4991470592725, 11.3270506316853]

# I check if the folder is empty or not
if not os.listdir(save_path) == []:
    print("The folder is not empty, do you want to continue? (y/n)")
    answer = input()
    if(answer.lower() == 'y'):
        # I remove all the files in the folder
        print("Removing all the files in the folder ...")
        for file in os.listdir(save_path):
            os.remove(os.path.join(save_path, file))
        print("DONE!")
    else:
        exit()

##############################################################################################################

## Data Loading ##############################################################################################

print("--- populating vehicle count and coils ---")

# Graphs

# Graph for coils
g_coils = Graph()

# Bind Namespaces
g_coils.bind("xsd", XSD)
g_coils.bind("btp", BTP)

# Graph for vehicle count
g_vc = Graph()

# Bind Namespaces
g_vc.bind("xsd", XSD)
g_vc.bind("btp", BTP)

for namefile in rilevazione_flusso:

    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)

    for chunk in pd.read_csv(namefile, sep=';', chunksize=chunksize):
        
        for index, row in chunk.iterrows():

            # I check if the record is valid or not -> must have all the field not NaN
            if row['Livello'] == '' and row['tipologia'] == '' and row['Nome via'] == '':
                # I skip the record -> next record
                continue
            # else: is valid -> continue
            
            for i in range(2, 26):

                ## COIL:
                # -uri: coil_ + id number.
                # -attributi: hasID
                # -object properties: hasLevel, hasType, isOn, and isPlacedOn.

                ## VEHICLEDETECTION:
                # -uri: vehicleDetection_ + id number + _ + date.
                # -attributi: hasCount. 
                # -object properties: isObserved, hasObserve, isObservedOnPeriod, and hasObservedOnPeriod.
                
                date_obj = datetime.datetime.strptime(str(row['data']), '%Y-%m-%d')
                VehicleDetection = URIRef(BTP["vehicleDetection_"+str(row['ID_univoco_stazione_spira'])+"_"+date_obj.strftime('%Y-%m-%d')+"_"+str(i-2).zfill(2)+":00-"+str(i-1).zfill(2)+":00"])
                g_vc.add((VehicleDetection, RDF.type, BTP.VehicleDetection))

                # CHECK IF IT WORKS!! ##########################################
                
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
                
                g_vc.add((VehicleDetection, BTP.isObserved, Coil))
                g_vc.add((Coil, BTP.hasObserve, VehicleDetection))

                ################################################################

                Level = URIRef(BTP["level_"+str(row['Livello'])])
                g_coils.add((Level, RDF.type, BTP.Level))
                g_coils.add((Coil, BTP.hasLevel, Level))

                Type = URIRef(BTP["type_"+str(row['tipologia'])])
                g_coils.add((Type, RDF.type, BTP.Type))
                g_coils.add((Coil, BTP.hasType, Type))

                g_coils.add((Coil, BTP.hasID, Literal(str(row['codice spira']), datatype=XSD.string)))

                # Add the road
                if(row['codice via'] == ''):
                    continue
                    # MARCO's CODE
                
                # Road here can't be empty
                Road = URIRef(BTP["road_"+str(row['codice via'])])
                g_coils.add((Coil, BTP.isOn, Road))
                g_coils.add((Road, BTP.isPlacedOn, Coil))
                g_coils.add((Road, RDFS.label, Literal(str(row['Nome via']).lower(), datatype=XSD.string)))

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
        pbar.update(chunksize)
    pbar.close()

# Save the graph
with open(os.path.join(save_path, 'vehicle_counted_populated.ttl'), 'w') as file:
    file.write(g_vc.serialize(format='turtle'))
with open(os.path.join(save_path, 'coils_populated.ttl'), 'w') as file2:
    file2.write(g_coils.serialize(format='turtle'))

# Free memory
del g_coils, g_vc

##############################################################################################################

print("--- populating vehicle accuracy ---")

# Graphs

# Graph for vehicle count
g_acc = Graph()

# Bind Namespaces
g_acc.bind("xsd", XSD)
g_acc.bind("btp", BTP)

# Load coils dataset
g_coils = Graph()
g_coils.bind("xsd", XSD)
g_coils.parse(os.path.join(save_path, 'coils_populated.ttl'), format='turtle')


# FOR TEST TRY TO USE THE COILS DATASET!!
# g_coils.parse(os.path.join(save_path, 'spire_populated.ttl'), format='turtle')


# Query to get the coil's code associated to an ID (input: ID)
code_coil_query = prepareQuery("""
    SELECT DISTINCT ?coil WHERE {
        ?coil btp:hasID ?id .
    FILTER (?id = ?coil_id)                                                    
                               }""" , initNs={"btp": BTP})
    
for namefile in accuratezza_spire:

    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)

    for chunk in pd.read_csv(namefile, sep=';', chunksize=chunksize):
        
        for index, row in chunk.iterrows():
            
            for i in range(2, 26):

                ## VEHICLEDETECTION:
                # -uri: vehicleDetection_ + id number + _ + date.
                # -attributi: hasAccuracy, and hasCount.

                coil = ''

                # Query to get the coil's code associated to an ID
                res = g_coils.query(code_coil_query, initBindings={'coil_id':Literal(row['codice spira'], datatype=XSD.string)})
                if res == [] or res == None:
                    # I skip the record -> next record
                    continue
                else:
                    for r in res:
                        coil = str(r.coil).replace('http://www.dei.unipd.it/~gdb/ontology/btp/#coil_', '')
                        # It must be one!
                        break
                
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
        
        pbar.update(chunksize)
    pbar.close()

# Save the graph
with open (os.path.join(save_path, 'vehicle_accuracy_populated.ttl'), 'w') as file:
    file.write(g_acc.serialize(format='turtle'))
# Free memory
del g_acc, g_coils

##############################################################################################################

print("--- populating pollution data ---")

# Graphs

# Graph for vehicle count
g_pol = Graph()

# Bind Namespaces
g_pol.bind("xsd", XSD)
g_pol.bind("btp", BTP)

for namefile in centraline:
    
    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)

    for chunk in pd.read_csv(namefile, sep=';', chunksize=chunksize):
        
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
        
        pbar.update(chunksize)
    pbar.close()

# Save the graph
with open (os.path.join(save_path, 'pollution_data_populated.ttl'), 'a') as file:
    file.write(g_pol.serialize(format='turtle'))

# Free memory
del g_pol

print("--- end ---")
