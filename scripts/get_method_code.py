import json
import os

SAMPLED_FILE = "results/sampled_methods.json"
OUTPUT_FILE = "results/sampled_methods_with_code.json"

DATASET_ROOT = "pymethods2test"

with open(SAMPLED_FILE, "r") as f:
    methods = json.load(f)

results = []


def find_file(filename):
    """Search dataset for the file"""
    for root, dirs, files in os.walk(DATASET_ROOT):
        if filename in files:
            return os.path.join(root, filename)
    return None


for m in methods:

    filename = os.path.basename(m["source_file"])
    start = m["start_line"]
    end = m["end_line"]

    filepath = find_file(filename)

    if not filepath:
        print("File not found:", filename)
        continue

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        method_code = "".join(lines[start-1:end])

        m["method_code"] = method_code
        results.append(m)

    except Exception:
        print("Skipping:", filepath)

print("Methods with code:", len(results))

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print("Saved to:", OUTPUT_FILE)