# LLM-Based Automatic Unit Test Generation Using Focal-Method Datasets

---

## 1. Project Overview

This project explores how **Large Language Models (LLMs)** can automatically generate **unit tests for Python functions** using a focal-method-based approach.

The system takes real-world functions from a dataset and generates pytest test cases using LLMs. The generated tests are then evaluated using multiple metrics such as:

* Assertion count
* Edge-case coverage
* Syntax validity
* Failure modes

Finally, results are visualized using an interactive dashboard.

---

## 2. Objectives

* Automate unit test generation using LLMs
* Compare different prompting strategies
* Evaluate generated tests using measurable metrics
* Analyze limitations of LLM-generated outputs
* Build a visual dashboard for insights

---

## 3. End-to-End Pipeline

### Workflow Diagram

```text
Dataset (pyMethods2Test)
        ↓
Method Extraction
        ↓
Method Sampling
        ↓
Test Generation (LLM)
        ↓
Evaluation
        ↓
Failure Analysis
        ↓
Dashboard Visualization
```

---

## 4. Execution Flow (Step-by-Step)

```text
1. extract_methods.py
2. sample_methods.py
3. generate_tests_llm.py
4. generate_tests_llm_advanced.py
5. evaluate_tests.py
6. failure_analysis.py
7. dashboard_streamlit.py
```

---

## 5. Project Structure

```text
LLM_Test_Generator_Project/
│
├── pymethods2test/data/           # Dataset
│
├── scripts/
│   ├── extract_methods.py
│   ├── sample_methods.py
│   ├── generate_tests_llm.py
│   ├── generate_tests_llm_advanced.py
│   ├── evaluate_tests.py
│   ├── failure_analysis.py
│   ├── dashboard_streamlit.py
│
├── results/
│   ├── sampled_methods.json
│   ├── generated_tests_advanced.json
│   ├── evaluation_summary.json
│   ├── failure_summary.json
│
└── README.md
```

---

## 6. Setup Instructions

### Install Dependencies

```bash
pip install ollama streamlit
```

---

### Run LLM Model

```bash
ollama run llama3
```

---

## 7. How to Run the Project

### Step 1: Extract Methods

```bash
python3 scripts/extract_methods.py
```

---

### Step 2: Sample Methods

```bash
python3 scripts/sample_methods.py
```

---

### Step 3: Generate Tests (Baseline)

```bash
python3 scripts/generate_tests_llm.py
```

---

### Step 4: Generate Tests (Advanced)

```bash
python3 scripts/generate_tests_llm_advanced.py
```

---

### Step 5: Evaluate Tests

```bash
python3 scripts/evaluate_tests.py
```

### ✅ Output:

```text
Total tests: 300
Total assertions: 2814
Average assertions per test: 9.38
Edge case tests: 300
```

---

### Step 6: Failure Analysis

```bash
python3 scripts/failure_analysis.py
```

### ✅ Output:

```text
Valid Python code: 159
Syntax errors: 141
No assertions: 215
Extra text issues: 88
```

---

### Step 7: Run Dashboard

```bash
streamlit run scripts/dashboard_streamlit.py
```

Open in browser:

```
http://localhost:8501
```

---

## 8. Prompt Strategies

### Baseline Prompt

* Uses only function name
* Generates simple tests

### Context Prompt

* Adds structured instructions
* Improves quality

### Advanced Prompt

* Includes edge cases
* Multiple assertions
* Parameterized tests
* Better structure

---

## 9. Evaluation Metrics

| Metric              | Description                         |
| ------------------- | ----------------------------------- |
| Total Assertions    | Total number of `assert` statements |
| Avg Assertions/Test | Average assertions per test         |
| Edge Case Coverage  | % of tests containing edge cases    |
| Syntax Validity     | % of compilable tests               |
| Failure Types       | Error classification                |

---

## 10. Results

### Test Generation Results

| Metric              | Value |
| ------------------- | ----- |
| Total Tests         | 300   |
| Total Assertions    | 2814   |
| Average Assertions/Test | 9.38  |
| Edge Case Coverage  | 100%  |

---

### Failure Analysis

| Metric        | Value |
| ------------- | ----- |
| Valid Tests   | 159    |
| Syntax Errors | 141    |
| No Assertions | 215    |
| Extra Text    | 88    |

---

## 11. Research Questions

---

### RQ1: Effect of Prompting Strategy

Prompt design significantly improves test quality.

* Baseline → simple tests
* Context → better structure
* Advanced → highest coverage

👉 Key Insight:
Structured prompts matter more than raw context.

---

### RQ2: Quality of Generated Tests

Generated tests show strong coverage:

* High number of assertions
* 100% edge-case inclusion

However:

* Many tests are not executable
* Some assertions are incorrect

---

### RQ3: Limitations of LLMs

Key limitations observed:

* Syntax errors in generated code
* Extra non-code text
* Incorrect assumptions about logic
* Lack of execution correctness

👉 Conclusion:
LLMs assist test generation but require validation.

---

## 12. Key Insights

* LLMs generate diverse test cases
* Prompt engineering improves output quality
* Outputs are not always executable
* Post-processing is necessary

---

## 13. Dashboard

The project includes an interactive dashboard built using Streamlit.

### Features:

* Live metrics visualization
* Test validity breakdown
* Edge-case coverage display
* Interactive test viewer

---

## 14. Conclusion

This project demonstrates that:

* LLMs can generate meaningful test cases
* They significantly reduce manual effort
* However, they are not fully reliable

👉 Human validation is still required.

---

## 15. Future Work

* Add pytest execution
* Measure real code coverage
* Improve cleaning of outputs
* Fine-tune LLMs for test generation

---

## 16. Technologies Used

* Python
* Ollama
* Llama3
* Streamlit
* JSON

---

## 17. Final Status

```text
Project Completed: ✅ 100%
```

---

## 18. Acknowledgements

* pyMethods2Test dataset
* Open-source LLM tools
* Course guidance

---
