import json
import re
from pathlib import Path
from typing import Any, Dict, List


INPUT_FILE = Path("results/generated_tests_advanced.json")
OUTPUT_FILE = Path("results/evaluation_summary.json")


def evaluate_tests(
    input_path: Path = INPUT_FILE,
    output_path: Path = OUTPUT_FILE,
) -> Dict[str, Any]:
    """Evaluate generated test quality: assertion count and edge case coverage."""
    tests: List[Dict[str, Any]] = json.loads(input_path.read_text(encoding="utf-8"))

    total_tests = len(tests)
    total_assertions = 0
    edge_cases = 0

    for t in tests:
        code = t.get("generated_test", "")

        # count assertions
        assertions = re.findall(r"assert ", code)
        total_assertions += len(assertions)

        # simple edge case detection
        if any(k in code.lower() for k in ["none", "0", "negative", "[]", "-1", "large"]):
            edge_cases += 1

    # calculate average
    avg_assertions = total_assertions / total_tests if total_tests > 0 else 0.0

    # print results
    print("Total generated tests:", total_tests)
    print("Total assertions:", total_assertions)
    print("Average assertions per test:", round(avg_assertions, 2))
    print("Edge case tests:", edge_cases)

    # save for dashboard
    results: Dict[str, Any] = {
        "total_tests": total_tests,
        "total_assertions": total_assertions,
        "avg_assertions": avg_assertions,
        "edge_cases": edge_cases,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    return results


if __name__ == "__main__":
    evaluate_tests()
