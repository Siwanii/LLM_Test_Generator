import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ollama  # NEW


RESULTS_DIR = Path("results")
DEFAULT_INPUT = RESULTS_DIR / "generated_tests_by_strategy.json"
DEFAULT_OUTPUT = RESULTS_DIR / "execution_summary.json"


@dataclass
class ExecutionResult:
    id: str
    function_name: str
    prompt_strategy: str
    pytest_exit_code: int
    passed: bool
    duration_sec: float
    error_category: str
    pytest_output_tail: str
    # NEW fields for repair loop
    repair_attempted: bool
    repair_success: bool
    repair_iters: int
    repaired_test_code: str


def _safe_id(s: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9_\-]+", "_", s).strip("_")
    return s[:max_len] if len(s) > max_len else s


def _classify_pytest_output(exit_code: int, output: str) -> str:
    out = output.lower()
    if exit_code == 0:
        return "passed"
    if "syntaxerror" in out:
        return "syntax_error"
    if "importerror" in out or "modulenotfounderror" in out:
        return "import_error"
    if "nameerror" in out:
        return "name_error"
    if "typeerror" in out:
        return "type_error"
    if "assertionerror" in out:
        return "assertion_error"
    if "failed" in out:
        return "test_failed"
    return "other_failure"


def _tail(s: str, lines: int = 60) -> str:
    parts = s.splitlines()
    return "\n".join(parts[-lines:])


def _extract_generated_tests(items: Any) -> List[Dict[str, Any]]:
    if isinstance(items, list):
        return items
    if isinstance(items, dict):
        for k in ("tests", "data", "items", "results"):
            if k in items and isinstance(items[k], list):
                return items[k]
    raise ValueError("Unexpected JSON structure in generated tests file.")

def _normalize_method_code(entry: Dict[str, Any]) -> str:
    # generator uses: method_code
    for key in ("method_code", "focal_method", "function_code", "code", "method"):
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip() + ("\n" if not v.endswith("\n") else "")
    return ""


def _normalize_test_code(entry: Dict[str, Any]) -> str:
    # generator uses: generated_test
    for key in ("generated_test", "test_code", "generated_test_code", "tests", "output"):
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip() + ("\n" if not v.endswith("\n") else "")
    return ""


def _normalize_function_name(entry: Dict[str, Any]) -> str:
    # generator uses: method_name
    for key in ("method_name", "function_name", "name"):
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "unknown_function"


def _normalize_strategy(entry: Dict[str, Any]) -> str:
    # generator uses: prompt_strategy
    for key in ("prompt_strategy", "strategy", "prompt_type"):
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "unknown"

def _extract_python_from_llm(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # If it contains a fenced block, extract it
    m = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip() + "\n"

    # If it starts with ``` but no closing fence, drop the first line
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]

    while lines and re.match(r"^\s*(here (are|is)|sure|okay|below)\b", lines[0], flags=re.I):
        lines.pop(0)

    return "\n".join(lines).strip() + "\n"

def _repair_with_ollama(
    function_name: str,
    method_code: str,
    broken_test_code: str,
    pytest_output: str,
    model: str = "llama3",
) -> str:
    """
    Uses Ollama locally to fix the test so it becomes valid pytest code.
    Returns repaired test code (python only).
    """
    system = (
        "You are a senior Python engineer. "
        "Fix the provided pytest test file so it is valid Python and imports the focal function. "
        "Return ONLY Python code (no Markdown, no explanations)."
    )
    user = f"""
Focal function name: {function_name}

Focal function code (in focal_module.py):
{method_code}

Broken pytest file (test_generated.py):
{broken_test_code}

Pytest output / traceback:
{pytest_output}

Requirements:
- Output must be a valid pytest test module.
- Must run under pytest without syntax or collection errors.
- Start with: import pytest
- Import the focal function using: from focal_module import {function_name}
- Do not include Markdown fences or any prose.
- Do NOT use pytest.raises(TypeError) unless the function code explicitly raises TypeError.
- If using @pytest.mark.parametrize("a, b", [...]), every tuple MUST have exactly 2 values.
- If the function returns None or has 'pass' as body, assert the result is None.
- Fix ALL errors shown in the traceback above.
"""
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = resp.get("message", {}).get("content", "")
    return _extract_python_from_llm(content)


def _make_project(tmpdir: Path, function_name: str, method_code: str, test_code: str) -> None:
    tmpdir.mkdir(parents=True, exist_ok=True)

    focal_path = tmpdir / "focal_module.py"
    if method_code.strip():
        focal_path.write_text(method_code, encoding="utf-8")
    else:
        focal_path.write_text(
            f"def {function_name}(*args, **kwargs):\n"
            f"    raise NotImplementedError('No focal method code available')\n",
            encoding="utf-8",
        )

    # Inject both pytest and focal_module imports if missing
    injected_lines = []
    if "import pytest" not in test_code:
        injected_lines.append("import pytest")
    if f"from focal_module import {function_name}" not in test_code:
        injected_lines.append(f"from focal_module import {function_name}")

    final_test = test_code
    if injected_lines:
        final_test = "\n".join(injected_lines) + "\n\n" + test_code

    (tmpdir / "test_generated.py").write_text(final_test, encoding="utf-8")

    (tmpdir / "pytest.ini").write_text(
        "[pytest]\naddopts = -q\npython_files = test_*.py\n",
        encoding="utf-8",
    )


def _run_pytest(tmpdir: Path, timeout_sec: int = 60) -> Tuple[int, str, float]:
    start = time.time()
    proc = subprocess.run(
        ["python3", "-m", "pytest"],
        cwd=str(tmpdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
        env={**os.environ, "PYTHONPATH": str(tmpdir)},
    )
    dur = time.time() - start
    return proc.returncode, proc.stdout, dur


def main(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    limit: Optional[int] = None,
    timeout_sec: int = 60,
    enable_repair: bool = True,
    max_repair_iters: int = 3,           # Increased from 1 for better fix rate
    ollama_model: str = "llama3",
) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    entries = _extract_generated_tests(raw)

    results: List[ExecutionResult] = []
    totals = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "by_error_category": {},
        "avg_duration_sec": 0.0,
        # NEW aggregate stats
        "repair_attempted": 0,
        "repair_success": 0,
        "avg_repair_iters": 0.0,
    }

    n = len(entries) if limit is None else min(limit, len(entries))
    durations: List[float] = []
    repair_iters_list: List[int] = []

    print(f"\n🚀 Starting execution & repair of {n} generated tests...\n")
    start_all = time.time()

    for i in range(n):
        entry = entries[i]
        function_name = _normalize_function_name(entry)
        strategy = _normalize_strategy(entry)
        method_code = _normalize_method_code(entry)
        test_code = _normalize_test_code(entry)

        test_id = entry.get("id") or f"{_safe_id(function_name)}_{i}"
        tmp_root = Path(tempfile.mkdtemp(prefix="llm_test_exec_"))

        repair_attempted = False
        repair_success = False
        repair_iters = 0
        repaired_test_code = ""

        # Print current test progress
        print(f"[{i+1:3d}/{n}] Focal: {function_name:<25} | Strategy: {strategy:<28} ... ", end="", flush=True)

        try:
            # 1) First run (original)
            _make_project(tmp_root, function_name, method_code, test_code)
            exit_code, out, dur = _run_pytest(tmp_root, timeout_sec=timeout_sec)

            passed = exit_code == 0
            category = _classify_pytest_output(exit_code, out)

            # 2) Repair loop (MVP)
            current_test_code = test_code
            current_out = out
            current_exit = exit_code

            if enable_repair and not passed and max_repair_iters > 0:
                print(f"❌ Failed ({category}) -> entering repair loop...")
                repair_attempted = True
                totals["repair_attempted"] += 1

                for it in range(1, max_repair_iters + 1):
                    repair_iters = it
                    print(f"   ↳ [Iter {it}/{max_repair_iters}] Querying Llama3 for fix... ", end="", flush=True)
                    fixed = _repair_with_ollama(
                        function_name=function_name,
                        method_code=method_code,
                        broken_test_code=current_test_code,
                        pytest_output=current_out,
                        model=ollama_model,
                    )
                    if not fixed.strip():
                        print("Empty response, aborted.")
                        break

                    repaired_test_code = fixed

                    shutil.rmtree(tmp_root, ignore_errors=True)
                    tmp_root = Path(tempfile.mkdtemp(prefix="llm_test_exec_"))
                    _make_project(tmp_root, function_name, method_code, repaired_test_code)

                    current_exit, current_out, dur2 = _run_pytest(tmp_root, timeout_sec=timeout_sec)
                    dur = dur + dur2

                    if current_exit == 0:
                        repair_success = True
                        passed = True
                        category = "passed_after_repair"
                        print("✅ Success! Repaired.")
                        break
                    else:
                        cat_fail = _classify_pytest_output(current_exit, current_out)
                        print(f"❌ Still failing ({cat_fail})")

                    # keep trying with latest failure context
                    current_test_code = repaired_test_code

                repair_iters_list.append(repair_iters)
            else:
                if passed:
                    print("✅ Passed!")
                else:
                    print(f"❌ Failed ({category})")

            res = ExecutionResult(
                id=str(test_id),
                function_name=function_name,
                prompt_strategy=strategy,
                pytest_exit_code=int(current_exit if enable_repair and repair_attempted else exit_code),
                passed=bool(passed),
                duration_sec=float(dur),
                error_category=category,
                pytest_output_tail=_tail(current_out if enable_repair and repair_attempted else out, lines=80),
                repair_attempted=repair_attempted,
                repair_success=repair_success,
                repair_iters=int(repair_iters),
                repaired_test_code=repaired_test_code,
            )
            results.append(res)

            totals["total"] += 1
            if passed:
                totals["passed"] += 1
            else:
                totals["failed"] += 1

            totals["by_error_category"][category] = totals["by_error_category"].get(category, 0) + 1
            durations.append(dur)
            if repair_success:
                totals["repair_success"] += 1

        except subprocess.TimeoutExpired as e:
            out2 = (e.stdout or "")
            out2 = out2 + f"\nTIMEOUT: exceeded {timeout_sec}s\n"
            category = "timeout"
            print("⏳ TIMEOUT!")
            res = ExecutionResult(
                id=str(test_id),
                function_name=function_name,
                prompt_strategy=strategy,
                pytest_exit_code=124,
                passed=False,
                duration_sec=float(timeout_sec),
                error_category=category,
                pytest_output_tail=_tail(out2, lines=80),
                repair_attempted=repair_attempted,
                repair_success=repair_success,
                repair_iters=int(repair_iters),
                repaired_test_code=repaired_test_code,
            )
            results.append(res)

            totals["total"] += 1
            totals["failed"] += 1
            totals["by_error_category"][category] = totals["by_error_category"].get(category, 0) + 1
            durations.append(timeout_sec)

        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    totals["avg_duration_sec"] = (sum(durations) / len(durations)) if durations else 0.0
    totals["avg_repair_iters"] = (sum(repair_iters_list) / len(repair_iters_list)) if repair_iters_list else 0.0

    print(f"\n🎉 Completed execution of {totals['total']} tests in {time.time() - start_all:.1f}s")
    print(f"📊 Summary: Passed {totals['passed']}/{totals['total']} | Repaired {totals['repair_success']}/{totals['repair_attempted']}\n")

    payload = {
        "input_file": str(input_path),
        "executed": totals["total"],
        "summary": totals,
        "results": [asdict(r) for r in results],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()