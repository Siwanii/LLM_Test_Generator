import json
import random
from pathlib import Path
from typing import Any, Dict, List


INPUT_FILE = Path("results/extracted_methods.json")
OUTPUT_FILE = Path("results/sampled_methods.json")

SAMPLE_SIZE = 34  # 34 methods × 4 strategies = 136 tests (was 102 with 3 strategies)
RANDOM_SEED = 42  # Fixed seed for reproducibility


def sample_methods(
    input_path: Path = INPUT_FILE,
    output_path: Path = OUTPUT_FILE,
    sample_size: int = SAMPLE_SIZE,
    seed: int = RANDOM_SEED,
) -> List[Dict[str, Any]]:
    """Randomly sample methods from the extracted methods pool."""
    print("Loading extracted methods...")

    methods: List[Dict[str, Any]] = json.loads(input_path.read_text(encoding="utf-8"))
    print("Total methods available:", len(methods))

    random.seed(seed)
    sampled = random.sample(methods, min(sample_size, len(methods)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sampled, indent=2), encoding="utf-8")

    print(f"Sampled {len(sampled)} methods (seed={seed})")
    print("Saved to:", output_path)
    return sampled


if __name__ == "__main__":
    sample_methods()