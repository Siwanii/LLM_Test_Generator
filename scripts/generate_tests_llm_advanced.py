import json
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

def get_edge_cases(method_name):
    method_name = method_name.lower()

    if "add" in method_name or "sum" in method_name:
        return ["0,0", "-1,-2", "1000000,1000000"]
    elif "divide" in method_name:
        return ["1,0", "0,5", "-10,2"]
    elif "list" in method_name:
        return ["[]", "[1]", "[None]"]
    elif "string" in method_name or "str" in method_name:
        return ["''", "'a'", "'longstring'*100"]
    else:
        return ["None", "0"]

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

            test_code = response["message"]["content"]

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