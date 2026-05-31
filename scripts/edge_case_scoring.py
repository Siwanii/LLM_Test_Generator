import ast
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


RESULTS_DIR = Path("results")
DEFAULT_EXECUTION_SUMMARY = RESULTS_DIR / "execution_summary.json"
DEFAULT_OUT = RESULTS_DIR / "edge_case_scoring.json"


EDGE_CATEGORIES = [
    "none",
    "empty_string",
    "empty_list",
    "empty_dict",
    "zero",
    "negative",
    "large_number",
    "unicode",
    "nan_inf",
    "raises",
    "boundary",
]


@dataclass
class EdgeScore:
    id: str
    function_name: str
    prompt_strategy: str
    used_code: str  # "repaired" or "original"
    score: float
    covered: Dict[str, bool]
    evidence: Dict[str, List[str]]


def _extract_items(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(d, dict) and isinstance(d.get("results"), list):
        return d["results"]
    raise ValueError("Expected execution_summary.json with top-level key 'results' (list).")


def _get_test_code(item: Dict[str, Any], prefer_repaired: bool = True) -> Tuple[str, str]:
    repaired = item.get("repaired_test_code") or ""
    if prefer_repaired and isinstance(repaired, str) and repaired.strip():
        return repaired, "repaired"
    # fallback: try to get original test code from generated_test field
    original = item.get("generated_test") or item.get("test_code") or ""
    if isinstance(original, str) and original.strip():
        return original, "original"
    # last resort: return whatever repaired text we have (may be empty)
    return repaired, "original"


def _strip_markdown_fences(code: str) -> str:
    if not isinstance(code, str):
        return ""
    m = re.search(r"```(?:python)?\s*(.*?)```", code, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)
    return code


def _find_literals_and_calls(code: str) -> Dict[str, List[str]]:
    code = _strip_markdown_fences(code)
    out: Dict[str, List[str]] = {k: [] for k in EDGE_CATEGORIES}

    # quick regex evidence
    if re.search(r"\bpytest\.raises\b", code):
        out["raises"].append("pytest.raises")

    if re.search(r"\bfloat\(['\"]nan['\"]\)|\bnan\b", code, flags=re.I):
        out["nan_inf"].append("nan")
    if re.search(r"\bfloat\(['\"]inf['\"]\)|\binf\b", code, flags=re.I):
        out["nan_inf"].append("inf")

    if re.search(r"\\u[0-9a-fA-F]{4}", code) or re.search(r"[^\x00-\x7F]", code):
        out["unicode"].append("non-ascii or unicode escape")

    # AST-based evidence
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return out  # can't score reliably

    for node in ast.walk(tree):
        # None
        if isinstance(node, ast.Constant) and node.value is None:
            out["none"].append("None literal")

        # strings
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value == "":
                out["empty_string"].append('""')
            if any(ord(ch) > 127 for ch in node.value):
                out["unicode"].append("unicode string literal")
            # detect unicode escape sequences in string content
            if re.search(r'\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}', node.value):
                out["unicode"].append("unicode escape in string")

        # numbers
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            val = node.value
            if val == 0:
                out["zero"].append("0 literal")
            if isinstance(val, (int, float)) and val < 0:
                out["negative"].append(f"{val} literal")
            if isinstance(val, int) and abs(val) >= 10**6:
                out["large_number"].append(f"{val} literal")

            if isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
                out["nan_inf"].append(f"{val}")

        # Detect negative via UnaryOp(USub) — catches -1, -0.5, etc.
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
                out["negative"].append(f"-{node.operand.value} (unary)")

        # empty containers
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and len(node.elts) == 0:
            out["empty_list"].append("[]/()/set() empty")
        if isinstance(node, ast.Dict) and len(node.keys) == 0:
            out["empty_dict"].append("{} empty")

        # boundary hints: parametrize with 0/1/-1 or length 0/1 etc.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "parametrize":
                out["boundary"].append("parametrize")

    return out


def _score(evidence: Dict[str, List[str]]) -> Tuple[float, Dict[str, bool]]:
    covered = {k: (len(v) > 0) for k, v in evidence.items()}
    # simple equal-weight score
    score = sum(1 for k in EDGE_CATEGORIES if covered.get(k)) / float(len(EDGE_CATEGORIES))
    return score, covered


def main(
    execution_summary_path: Path = DEFAULT_EXECUTION_SUMMARY,
    out_path: Path = DEFAULT_OUT,
    prefer_repaired: bool = True,
) -> None:
    d = json.loads(Path(execution_summary_path).read_text(encoding="utf-8"))
    items = _extract_items(d)

    scored: List[EdgeScore] = []
    for item in items:
        code, used = _get_test_code(item, prefer_repaired=prefer_repaired)
        evidence = _find_literals_and_calls(code)
        score, covered = _score(evidence)

        scored.append(
            EdgeScore(
                id=str(item.get("id", "")),
                function_name=str(item.get("function_name", "")),
                prompt_strategy=str(item.get("prompt_strategy", "unknown")),
                used_code=used,
                score=float(score),
                covered=covered,
                evidence={k: v[:5] for k, v in evidence.items() if v},  # limit evidence verbosity
            )
        )

    # Per-strategy summary
    from collections import defaultdict
    per_strat = defaultdict(lambda: {"scores": [], "covered": defaultdict(int), "total": 0})
    for x in scored:
        s = x.prompt_strategy
        per_strat[s]["scores"].append(x.score)
        per_strat[s]["total"] += 1
        for cat, hit in x.covered.items():
            if hit:
                per_strat[s]["covered"][cat] += 1

    per_strategy_summary = {}
    for s, data in per_strat.items():
        t = data["total"]
        per_strategy_summary[s] = {
            "avg_score": sum(data["scores"]) / t if t else 0.0,
            "total": t,
            "category_coverage_rate": {k: data["covered"].get(k, 0) / t if t else 0.0 for k in EDGE_CATEGORIES},
        }

    summary = {
        "total": len(scored),
        "avg_score": sum(x.score for x in scored) / len(scored) if scored else 0.0,
        "category_coverage_rate": {
            k: (sum(1 for x in scored if x.covered.get(k)) / len(scored) if scored else 0.0)
            for k in EDGE_CATEGORIES
        },
        "per_strategy": per_strategy_summary,
    }

    payload = {"summary": summary, "items": [asdict(x) for x in scored]}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()