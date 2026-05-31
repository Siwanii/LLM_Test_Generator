import json
import os
from pathlib import Path
from typing import Any, Dict, List


def extract_methods(dataset_path: str = "pymethods2test/data") -> List[Dict[str, Any]]:
    """Walk through the pyMethods2Test dataset and extract focal method metadata."""
    methods: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            if file.endswith(".json"):
                filepath = os.path.join(root, file)

                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Skipping {filepath}: {e}")
                    continue

                for test_file in data:
                    if not isinstance(data[test_file], dict):
                        continue

                    focal_file = data[test_file].get("focal_file", "")
                    methods_data = data[test_file].get("methods", {})

                    if not isinstance(methods_data, dict):
                        continue

                    for test_method in methods_data:
                        method_info = methods_data[test_method]
                        if not isinstance(method_info, dict):
                            continue

                        focal_method = method_info.get("focal_method")

                        if focal_method and isinstance(focal_method, dict):
                            method_name = focal_method.get("name", "")
                            start_line = focal_method.get("line")
                            end_line = focal_method.get("line_end")

                            if method_name and start_line is not None and end_line is not None:
                                methods.append({
                                    "source_file": focal_file,
                                    "method_name": method_name,
                                    "start_line": start_line,
                                    "end_line": end_line,
                                })

    return methods


def main() -> None:
    methods = extract_methods()

    print("Total focal methods found:", len(methods))

    # Save extracted methods
    output_path = Path("results/extracted_methods.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(methods, f, indent=2)

    print("Saved extracted methods to:", output_path)

    if methods:
        print("\nExample method metadata:\n")
        print(json.dumps(methods[0], indent=2))


if __name__ == "__main__":
    main()
