import os
import json

dataset_path = "pymethods2test/data"

methods = []

# Walk through dataset
for root, dirs, files in os.walk(dataset_path):

    for file in files:

        if file.endswith(".json"):

            filepath = os.path.join(root, file)

            with open(filepath, "r") as f:

                data = json.load(f)

                for test_file in data:

                    focal_file = data[test_file]["focal_file"]
                    methods_data = data[test_file]["methods"]

                    for test_method in methods_data:

                        focal_method = methods_data[test_method]["focal_method"]

                        if focal_method:

                            method_name = focal_method["name"]
                            start_line = focal_method["line"]
                            end_line = focal_method["line_end"]

                            methods.append({
                                "source_file": focal_file,
                                "method_name": method_name,
                                "start_line": start_line,
                                "end_line": end_line
                            })

print("Total focal methods found:", len(methods))

# Save extracted methods
output_path = "results/extracted_methods.json"

with open(output_path, "w") as f:
    json.dump(methods, f, indent=2)

print("Saved extracted methods to:", output_path)

if methods:
    print("\nExample method metadata:\n")
    print(methods[0])
