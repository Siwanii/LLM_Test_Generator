import json
import os
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

INPUT_FILE = Path("results/sampled_methods.json")
OUTPUT_FILE = Path("results/sampled_methods_with_code.json")

DATASET_ROOT = Path("pymethods2test/data")
INDEX_CACHE = Path(".cache_method_index.pkl")  # Cache index so you don't rebuild each time


def _load_focal_json(focal_file: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a .focal.json file."""
    try:
        return json.loads(focal_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_index() -> Dict[str, Dict[str, Any]]:
    """
    Build index: method_name -> {focal_file, line, line_end}
    Scans all .focal.json files once and caches result.

    The pyMethods2Test .focal.json structure is:
    {
        "test_file_path": {
            "focal_file": "path/to/source.py",
            "methods": {
                "test_method_name": {
                    "focal_method": {
                        "name": "function_name",
                        "line": 42,
                        "line_end": 55,
                        "indent": 0
                    }
                }
            }
        }
    }
    """
    print("Building method index from dataset (this may take 1-2 min on first run)...")

    index: Dict[str, Dict[str, Any]] = {}
    count = 0
    files_scanned = 0

    for focal_file in DATASET_ROOT.rglob("*.focal.json"):
        files_scanned += 1
        data = _load_focal_json(focal_file)
        if not data:
            continue

        # Iterate through the nested structure
        for test_file_path, test_info in data.items():
            if not isinstance(test_info, dict):
                continue

            focal_source = test_info.get("focal_file", "")
            methods = test_info.get("methods", {})

            if not isinstance(methods, dict):
                continue

            for test_method_name, method_info in methods.items():
                if not isinstance(method_info, dict):
                    continue

                focal_method = method_info.get("focal_method")
                if not isinstance(focal_method, dict):
                    continue

                func_name = focal_method.get("name", "")
                line = focal_method.get("line")
                line_end = focal_method.get("line_end")

                if func_name and func_name not in index:
                    index[func_name] = {
                        "focal_file": focal_source,
                        "line": line,
                        "line_end": line_end,
                        "dataset_json": str(focal_file),
                    }
                    count += 1

    print(f"✅ Built index: {count} unique methods from {files_scanned} .focal.json files\n")

    # Cache for next time
    INDEX_CACHE.write_bytes(pickle.dumps(index))
    return index


def _load_or_build_index() -> Dict[str, Dict[str, Any]]:
    """Load cached index or build new one."""
    if INDEX_CACHE.exists():
        try:
            cached = pickle.loads(INDEX_CACHE.read_bytes())
            # Validate cache is not empty/corrupt (old cache was only 5 bytes)
            if isinstance(cached, dict) and len(cached) > 0:
                print(f"Loading cached method index ({len(cached)} methods)...")
                return cached
            else:
                print("Cache is empty or corrupt, rebuilding...")
        except Exception:
            print("Cache is corrupt, rebuilding...")
    return _build_index()


def _try_find_source_code(method_name: str, info: Dict[str, Any]) -> Optional[str]:
    """
    Try to find the actual source code for a method.
    The .focal.json files reference source files by path, but the actual
    .py source files are NOT bundled in the pyMethods2Test dataset.
    We look for the source file in the same dataset directory just in case.
    """
    focal_file = info.get("focal_file", "")
    if not focal_file:
        return None

    line = info.get("line")
    line_end = info.get("line_end")

    if line is None or line_end is None:
        return None

    # Try to find the source file in the dataset directory
    json_path = info.get("dataset_json", "")
    if json_path:
        dataset_dir = Path(json_path).parent
        # The focal_file path is relative to the repo root
        # Try both the full path and just the basename
        candidates = [
            dataset_dir / focal_file,
            dataset_dir / os.path.basename(focal_file),
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.suffix == ".py":
                try:
                    lines = candidate.read_text(encoding="utf-8").splitlines()
                    # line numbers are 1-indexed
                    method_lines = lines[line - 1 : line_end]
                    if method_lines:
                        return "\n".join(method_lines)
                except Exception:
                    continue

    return None


def _generate_context_stub(method_name: str, info: Dict[str, Any]) -> str:
    """
    Generate a context-rich stub when actual source code is unavailable.
    Includes file path and line range for better LLM context.
    """
    focal_file = info.get("focal_file", "unknown")
    line = info.get("line", "?")
    line_end = info.get("line_end", "?")

    return f'''def {method_name}(*args, **kwargs):
    """
    Function from: {focal_file}
    Original location: lines {line}-{line_end}
    Note: Actual source code not available in dataset.
    The function name and file path provide context about its purpose.
    """
    pass
'''


def main() -> None:
    methods = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    # Load index once (fast for subsequent runs)
    index = _load_or_build_index()

    enriched = []
    found_with_code = 0
    found_metadata = 0
    fallback = 0

    print(f"Processing {len(methods)} sampled methods...\n")

    for i, m in enumerate(methods, 1):
        entry = dict(m)
        method_name = entry.get("method_name", "?")

        # Lookup in index (O(1))
        info = index.get(method_name)

        if info:
            # Try to get actual source code
            source_code = _try_find_source_code(method_name, info)

            if source_code:
                entry["method_code"] = source_code
                entry["method_code_source"] = "dataset"
                entry["focal_file_path"] = info.get("focal_file", "")
                found_with_code += 1
                print(f"{i}. {method_name} ✅ (source code from dataset)")
            else:
                # We found the method in the index but can't get its source
                entry["method_code"] = _generate_context_stub(method_name, info)
                entry["method_code_source"] = "context_stub"
                entry["focal_file_path"] = info.get("focal_file", "")
                found_metadata += 1
                print(f"{i}. {method_name} ℹ️  (metadata found, context stub)")
        else:
            # Completely unknown method
            entry["method_code"] = f'''def {method_name}(*args, **kwargs):
    """Function not found in pyMethods2Test dataset."""
    pass
'''
            entry["method_code_source"] = "synthetic_fallback"
            fallback += 1
            print(f"{i}. {method_name} ⚠️  (not in dataset, synthetic)")

        enriched.append(entry)

    OUTPUT_FILE.write_text(json.dumps(enriched, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"✅ Wrote: {OUTPUT_FILE}")
    print(f"   Source code found:    {found_with_code} / {len(methods)}")
    print(f"   Metadata + stub:      {found_metadata} / {len(methods)}")
    print(f"   Synthetic fallback:   {fallback} / {len(methods)}")
    print(f"   Index size:           {len(index)} unique methods")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()