import json
import re
import time
import ollama

from prompt_strategies import load_strategies  # NEW

# INPUT / OUTPUT FILES
INPUT_FILE = "results/sampled_methods_with_code.json"
OUTPUT_FILE = "results/generated_tests_by_strategy.json"  # CHANGED to unified output

print("Loading sampled methods...")

with open(INPUT_FILE) as f:
    methods = json.load(f)

results = []

def extract_code(raw_text):
    """Pull just the Python code out of LLM responses.
    The model often wraps code in ```python ... ``` fences and adds
    explanatory prose. We want only the code block(s).
    """
    # Try to find ALL fenced code blocks and concatenate them
    blocks = re.findall(r"```(?:python)?\n?(.*?)```", raw_text, re.DOTALL)
    if blocks:
        return "\n\n".join(block.strip() for block in blocks if block.strip())

    # Handle unclosed fences (``` at start but no closing ```)
    if raw_text.strip().startswith("```"):
        lines = raw_text.strip().splitlines()
        # Skip the opening ``` line
        code_lines = lines[1:]
        return "\n".join(code_lines).strip()

    # If no fences, try to find the first 'import' or 'def ' line and take everything from there
    lines = raw_text.splitlines()
    # Skip common prose lines at the top
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ", "def ", "class ", "@")):
            return "\n".join(lines[idx:]).strip()

    # Fallback: return as-is (better than nothing)
    return raw_text.strip()

def get_edge_cases(method_name):
    """Return targeted edge cases based on the method name."""
    method_name = method_name.lower()

    cases = ["None", "0"]  # always include these basics

    if any(kw in method_name for kw in ("add", "sum", "total", "count", "calc")):
        cases.extend(["0,0", "-1,-2", "1000000,1000000", "0.5,0.5"])
    elif any(kw in method_name for kw in ("divide", "div", "ratio")):
        cases.extend(["1,0", "0,5", "-10,2", "0.1,0.3"])
    elif any(kw in method_name for kw in ("list", "array", "items", "elements")):
        cases.extend(["[]", "[1]", "[None]", "[1,2,3]"])
    elif any(kw in method_name for kw in ("string", "str", "text", "name", "parse", "format")):
        cases.extend(["''", "'a'", "'hello world'", "'special!@#'"])
    elif any(kw in method_name for kw in ("get", "fetch", "find", "search", "lookup")):
        cases.extend(["''", "None", "'nonexistent_key'"])
    elif any(kw in method_name for kw in ("set", "update", "put", "save", "write")):
        cases.extend(["''", "None", "{'key': 'value'}"])
    elif any(kw in method_name for kw in ("delete", "remove", "drop", "clear")):
        cases.extend(["''", "None", "'nonexistent'"])
    elif any(kw in method_name for kw in ("path", "file", "dir", "folder")):
        cases.extend(["''", "'/'", "'/nonexistent/path'", "'.'"])
    elif any(kw in method_name for kw in ("sort", "order", "rank")):
        cases.extend(["[]", "[1]", "[3,1,2]", "[1,1,1]"])
    elif any(kw in method_name for kw in ("bool", "is_", "has_", "check", "valid")):
        cases.extend(["True", "False", "None", "0", "1"])

    return cases

strategies = load_strategies()
print(f"Loaded {len(strategies)} prompt strategies.")

TOTAL = len(methods)
TOTAL_TASKS = TOTAL * len(strategies)
task_num = 0
start_time = time.time()

for i, m in enumerate(methods):
    method_name = m.get("method_name", "unknown_function")
    method_code = m.get("method_code", "")

    edge_cases = get_edge_cases(method_name)

    for strat in strategies:
        # Add edge_cases into any template that wants it (safe even if not used)
        prompt = strat.prompt_template.format(
            function_name=method_name,
            method_code=method_code,
            edge_cases=edge_cases,
        )

        # If a strategy does not mention edge cases, we append a small clause (so "advanced" stays advanced)
        if "{edge_cases}" not in strat.prompt_template:
            prompt = prompt + f"\n\nSpecific edge cases to include where applicable: {edge_cases}\n"

        task_num += 1
        pct = task_num * 100 // TOTAL_TASKS
        elapsed = time.time() - start_time
        print(f"[{pct:3d}%] {task_num}/{TOTAL_TASKS} | method {i+1}/{TOTAL} | strategy={strat.id} | elapsed={elapsed:.1f}s")

        try:
            response = ollama.chat(
                model="llama3",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": strat.temperature},
            )

            raw = response["message"]["content"]
            test_code = extract_code(raw)  # strip prose & markdown fences

            results.append(
                {
                    "method_name": method_name,
                    "method_code": method_code,
                    "prompt_strategy": strat.id,
                    "prompt_strategy_name": strat.name,
                    "model": "llama3",
                    "temperature": strat.temperature,
                    "edge_cases_hint": edge_cases,
                    "prompt_used": prompt,
                    "generated_test": test_code,
                }
            )

        except Exception as e:
            print(f"Error generating {i+1}/{TOTAL} (strategy={strat.id}):", e)

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

total_time = time.time() - start_time
print(f"\n✅ Generation Complete in {total_time:.1f}s")
print(f"Generated tests: {len(results)}")
print(f"Avg time per test: {total_time / max(len(results), 1):.1f}s")
print(f"Saved to: {OUTPUT_FILE}")