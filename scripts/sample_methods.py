import json
import random

INPUT_FILE = "results/extracted_methods.json"
OUTPUT_FILE = "results/sampled_methods.json"

SAMPLE_SIZE = 10

print("Loading extracted methods...")

with open(INPUT_FILE, "r") as f:
    methods = json.load(f)

print("Total methods available:", len(methods))

sampled_methods = random.sample(methods, SAMPLE_SIZE)

with open(OUTPUT_FILE, "w") as f:
    json.dump(sampled_methods, f, indent=2)

print("Sampled", SAMPLE_SIZE, "methods")
print("Saved to:", OUTPUT_FILE)