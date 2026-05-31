import json
import re



INPUT_FILE = "results/generated_tests_advanced.json"

print("Loading generated tests...")

with open(INPUT_FILE) as f:
    data = json.load(f)

total = len(data)

valid = 0
syntax_errors = 0
no_assertions = 0
extra_text = 0

def clean_code(code):
    # Remove markdown ``` blocks
    code = re.sub(r"```.*?```", "", code, flags=re.DOTALL)
    
    # Remove common extra text
    code = re.sub(r"Here are.*", "", code)
    code = re.sub(r"Note that.*", "", code)
    
    return code.strip()

for item in data:
    code = item.get("generated_test", "")

    # CLEAN CODE
    cleaned_code = clean_code(code)

    # CHECK ASSERTIONS
    if "assert" not in cleaned_code:
        no_assertions += 1

    # CHECK EXTRA TEXT
    if "Here are the pytest" in code or "Note that" in code:
        extra_text += 1

    # CHECK SYNTAX
    try:
        compile(cleaned_code, "<string>", "exec")
        valid += 1
    except Exception:
        syntax_errors += 1

# PRINT RESULTS
print("\n===== FAILURE ANALYSIS (FIXED) =====")
print("Total tests:", total)
print("Valid Python code:", valid)
print("Syntax errors:", syntax_errors)
print("No assertions:", no_assertions)
print("Extra text issues:", extra_text)


results = {
    "total_tests": total,
    "valid": valid,
    "syntax_errors": syntax_errors,
    "no_assertions": no_assertions,
    "extra_text": extra_text
}

with open("results/failure_summary.json", "w") as f:
    json.dump(results, f, indent=2)


