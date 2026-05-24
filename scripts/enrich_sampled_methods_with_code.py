import json
from pathlib import Path
from typing import Optional, Dict, Any
import pickle

INPUT_FILE = Path("results/sampled_methods.json")
OUTPUT_FILE = Path("results/sampled_methods_with_code.json")

DATASET_ROOT = Path("pymethods2test/data")
INDEX_CACHE = Path(".cache_method_index.pkl")  # Cache index so you don't rebuild each time


def _load_focal_json(focal_file: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a .focal.json file."""
    try:
        return json.loads(focal_file.read_text(encoding="utf-8"))
    except Exception as e:
        return None


def _build_index() -> Dict[str, str]:
    """
    Build index: function_name -> focal_method_code
    Scans all .focal.json files once and caches result.
    """
    print("Building method index from dataset (this may take 1-2 min on first run)...")
    
    index: Dict[str, str] = {}
    count = 0
    
    for focal_file in DATASET_ROOT.rglob("*.focal.json"):
        data = _load_focal_json(focal_file)
        if not data:
            continue
        
        func_name = data.get("function_name")
        code = data.get("focal_method_code")
        
        if func_name and code and func_name not in index:  # Keep first occurrence
            index[func_name] = code
            count += 1
    
    print(f"✅ Built index: {count} unique methods\n")
    
    # Cache for next time
    INDEX_CACHE.write_bytes(pickle.dumps(index))
    return index


def _load_or_build_index() -> Dict[str, str]:
    """Load cached index or build new one."""
    if INDEX_CACHE.exists():
        print("Loading cached method index...")
        return pickle.loads(INDEX_CACHE.read_bytes())
    return _build_index()


def _generate_synthetic_fallback(method_name: str) -> str:
    """Generate a fallback synthetic method if not found in dataset."""
    return f"""def {method_name}(*args, **kwargs):
    \"\"\"Synthetic method for testing (not found in dataset).\"\"\"
    return None
"""


def main() -> None:
    methods = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    # Load index once (fast for subsequent runs)
    index = _load_or_build_index()

    enriched = []
    found = 0
    fallback = 0

    print(f"Processing {len(methods)} sampled methods...\n")

    for i, m in enumerate(methods, 1):
        entry = dict(m)
        method_name = entry.get("method_name", "?")

        # Lookup in index (O(1))
        code = index.get(method_name)

        if code:
            entry["method_code"] = code
            entry["method_code_source"] = "dataset"
            found += 1
            print(f"{i}. {method_name} ✅ (from dataset)")
        else:
            # Fallback to synthetic
            entry["method_code"] = _generate_synthetic_fallback(method_name)
            entry["method_code_source"] = "synthetic_fallback"
            fallback += 1
            print(f"{i}. {method_name} ⚠️  (synthetic)")

        enriched.append(entry)

    OUTPUT_FILE.write_text(json.dumps(enriched, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"✅ Wrote: {OUTPUT_FILE}")
    print(f"   From dataset: {found} / {len(methods)}")
    print(f"   Synthetic fallback: {fallback} / {len(methods)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()