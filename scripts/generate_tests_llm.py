import json
import ollama

from scripts.prompt_strategies import load_strategies  # NEW

INPUT_FILE = "results/sampled_methods_with_code.json"
OUTPUT_FILE = "results/generated_tests_by_strategy.json"  # CHANGED

print("Loading sampled methods...")

with open(INPUT_FILE) as f:
    methods = json.load(f)

strategies = load_strategies()
print(f"Loaded {len(strategies)} prompt strategies.")

results = []

for i, m in enumerate(methods[:50]):
    method_name = m.get("method_name", "unknown_function")
    method_code = m.get("method_code", "")

    for strat in strategies:
        print(f"Generating test {i+1} / {min(50, len(methods))} | strategy={strat.id}")

        prompt = strat.prompt_template.format(
            function_name=method_name,
            method_code=method_code,
        )

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
                "prompt_used": prompt,
                "generated_test": test_code,
            }
        )

print("Generated tests:", len(results))

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print("Saved to:", OUTPUT_FILE)