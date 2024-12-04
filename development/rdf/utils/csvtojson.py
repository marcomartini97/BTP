import pandas as pd
import json
import os
from tqdm import tqdm

# Count the number of elements in a JSON file
def count_json_elements(jsonfile):
    count = 0
    with open(jsonfile, 'r') as json_file:
        for line in json_file:
            count += 1
    return count

namefile = ""

# Open document
print("Enter the name of the CSV file you want to convert to JSON: ")
datasetfile = input()

if datasetfile.startswith("C:"):
    namefile = datasetfile
else:
    # Add the relative path
    abs_path = os.path.abspath(__file__)
    abs_path = os.path.dirname(abs_path)

    namefile = os.path.join(abs_path, datasetfile)

chunksizes = 50000 #You can change this value to speed up conversion or to avoid memory error

# Read and get the list of sheet names
try:
    csv_file = pd.read_csv(namefile)
except FileNotFoundError:
    print("File not found, please try again.")
    # print all the directories available
    print(os.listdir(abs_path))
    exit()

# Loop
print(f"Converting {datasetfile} to JSON file.")
jsonfilename = "json\\" + datasetfile.replace(".csv", "") + ".json"
jsonfile = os.path.join(abs_path, jsonfilename)

# Check if the file exists
if(os.path.exists(jsonfile)):
    print("File already exists, it will be overwritten. Do you want to continue? (y/n)")
    answer = input()
    if(answer.lower() == 'y'):
        print("Overwriting " + jsonfilename.replace("json\\", "") + "...")
        os.remove(jsonfile)
    else:
        exit()

try:
    total_rows = len(pd.read_csv(namefile))
    pbar = tqdm(total=total_rows)
    with open(jsonfile, 'w') as json_file:
        json_file.write('[')
    # Read the first line to save the labels
    csv_data_df = pd.read_csv(namefile, nrows=1)
    labels = list(csv_data_df.columns)
    # Read in chunks to avoid memory error
    for skip in range(1, total_rows, chunksizes):
        csv_data_df = pd.read_csv(namefile, skiprows=skip, nrows=chunksizes)
        # Mapping data with labels
        with open(jsonfile, 'a') as json_file:
            for index, row in csv_data_df.iterrows():
                record = {labels[i]: row.iloc[i] for i in range(len(labels))}
                # Write to JSON file
                json.dump(record, json_file)
                if skip + index + 1 < total_rows:
                    json_file.write(',\n')
                else:
                    json_file.write(']')
        pbar.update(chunksizes)
    pbar.close()

    print(f"JSON file created successfully!\nPath: {jsonfile}")
except MemoryError:
    print("Memory Error, try to reduce the chunksizes' value.")


# FIX: THE COUNT FUNCTION DOESN'T WORK PROPERLY

# Check if the conversion is right
jsonfile = os.path.join(abs_path, jsonfilename)
num_elements = count_json_elements(jsonfile)
if (num_elements == total_rows-1):
    print("Conversion successful!")
else:
    print("Conversion failed, please try again.")
    print(f"Total rows: {total_rows}, Total elements in JSON file: {num_elements}")