## csv_to_json.py

# import pandas as pd

# Load the CSV file
# df = pd.read_csv('./data/vessel_details.csv')

# Convert to JSON file (orient='records' formats it as a clean list of dictionaries)
# df.to_json('./data/vessel_details_output.json', orient='records', indent=4)

"""Convert source vessel CSV data into a JSON export for downstream processing."""

import csv
import json

# File paths are intentionally relative to the project root so the script can be run
# from the repository directory without any additional setup.
csv_file_path = './data/vessel_details.csv'
json_file_path = './data/vessel_details_output.json'

data = []

# Read the CSV data and keep each row as a dictionary entry.
with open(csv_file_path, encoding='utf-8') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for rows in csv_reader:
        data.append(rows)

# Write the structured records back out as formatted JSON.
with open(json_file_path, 'w', encoding='utf-8') as json_file:
    json_file.write(json.dumps(data, indent=4))