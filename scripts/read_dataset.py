import os
import json

dataset_path = "pymethods2test/data"

json_count = 0

for root, dirs, files in os.walk(dataset_path):

    for file in files:

        if file.endswith(".json"):

            json_count += 1

            filepath = os.path.join(root, file)

            print("Reading:", filepath)

            with open(filepath) as f:
                data = json.load(f)

                print("Top keys:", list(data.keys())[:2])

            print("-----")

print("Total JSON files detected:", json_count)