# Autonomous Self-Healing LLM Unit Test Generator

An advanced, production-ready AI engineering pipeline that **automatically generates, executes, validates, and self-repairs unit tests** for Python applications. By combining local Large Language Models (Llama3 via Ollama) with grounded sandbox execution and compiler-grade static analysis, this system achieves a high-resiliency test generation pipeline that autonomously recovers from runtime and logical errors.

---

## Core Architecture & Technical Design

This project is built around four primary architectural pillars designed to ensure execution safety, evaluation depth, and system resilience:

* **Self-Healing Agent Loop**: Implements an autonomous feedback loop that handles execution failures. If a generated test crashes, the system dynamically parses the traceback diagnostics and constructs targeted prompt contexts to guide the LLM through up to 3 iterative self-repair attempts.
* **Isolated Sandbox Execution**: Executes all dynamically generated test cases inside isolated temporary sandbox directories, protecting the host system from executing untested code and simulating clean CI/CD runtime states.
* **Compiler-Grade Static Analysis (AST)**: Utilizes Python's standard `ast` package to programmatically parse test files into Abstract Syntax Trees. This allows the system to programmatically grade 11 critical edge-case categories (like exceptions, empty sequences, and None values) without executing the code.
* **Interactive Telemetry Dashboard**: A professional analytics interface built with Streamlit and Plotly to monitor pass/fail rates, self-repair flow Sankey graphs, edge-case coverage footprint radar charts, and a side-by-side code differential viewer.

---

## How the Pipeline Works

The system acts like a real-world developer: it writes a test, runs it, reads the error traceback, and iterates on fixes. Here is the step-by-step workflow:

1. **Extraction**: We scan the raw `pyMethods2Test` dataset to locate real-world Python functions (called focal methods) and extract their metadata.
2. **Sampling**: We select a random sample of functions to construct a reproducible benchmark. The sample size is fully configurable, allowing you to run any number of test cases depending on your evaluation needs.
3. **Enrichment**: We match the sampled functions back to the dataset to extract their original source code, fallback paths, and surrounding file context.
4. **Generation**: We prompt Llama3 to write pytest cases using four different prompting styles (detailed below) at controlled temperatures.
5. **Sandbox Execution & Self-Repair**: We launch the generated tests inside an isolated sandbox using `pytest`. If a test fails, we capture the exact failure traceback, bundle it with explicit formatting rules (like correct parametrize layouts), and feed it back to Llama3. The model gets **up to 3 attempts** to fix its own code.
6. **AST-Based Grading**: We use Python’s Abstract Syntax Tree (AST) analyzer to parse the final passing test code. This grades the tests based on whether they actually covered critical boundary cases (like empty lists, negative numbers, division by zero, and exceptions).
7. **Interactive Dashboard**: We display the results in a beautiful Streamlit web interface, showing pass/fail distributions, Sankey flows of the repair loop, strategy comparisons, and side-by-side code diffs.

---

## The Four Prompting Strategies

We compare four different strategies to see how much context and prompt structure affect test quality:

* **Baseline (Name-Only)**: We only give Llama3 the name of the function. It has to guess what the function does and write tests based on that guess. This measures how much the LLM relies on standard naming conventions.
* **Advanced (Code + Edge Cases)**: We provide the full source code of the function alongside targeted edge cases (like None or large integers). We also explicitly ask it to use `pytest.mark.parametrize` for clean code structure.
* **Strict Import**: We restrict the model's creativity. We instruct it to output absolutely no markdown fences or conversational text, enforce precise imports, and focus strictly on test execution.
* **Chain-of-Thought (CoT)**: We ask Llama3 to slow down and think. It is instructed to write a Python comment block analyzing the function's behavior and planning 5 key edge cases *before* it writes any test code. This significantly reduces hallucinations and syntax slips.

---

## Getting Started

### 1. Set Up Your Environment
First, clone this repository, set up a virtual environment, and install the required libraries:
```bash
# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install the dependencies
pip install -r requirements.txt
```

### 2. Start Ollama & Llama3
Ensure you have [Ollama](https://ollama.com/) running on your system, and pull the Llama3 model:
```bash
ollama pull llama3
```

---

## Running the Pipeline

You can run each stage of the pipeline sequentially with these commands:

### Step 1: Scan the Dataset
Extract focal function metadata from the `pyMethods2Test` data directory:
```bash
python3 scripts/extract_methods.py
```

### Step 2: Create a Sample
Grab a reproducible sample of functions using our fixed random seed:
```bash
python3 scripts/sample_methods.py
```
*(Tip: You can edit `SAMPLE_SIZE` inside `scripts/sample_methods.py` to change the number of test cases you want to run!)*

### Step 3: Enrich with Source Code
Find the original code and file locations for the sampled functions:
```bash
python3 scripts/enrich_sampled_methods_with_code.py
```

### Step 4: Generate the Unit Tests
Send the enriched functions to Llama3 to generate tests using all 4 strategies:
```bash
python3 scripts/generate_tests_llm_advanced.py
```

### Step 5: Execute & Repair
Run the tests in a sandbox and let the self-repair loop fix any failing runs:
```bash
python3 scripts/execute_generated_tests.py
```

### Step 6: Grade the Tests
Score the passing tests using our AST edge-case analyzer:
```bash
python3 scripts/edge_case_scoring.py
```

---

## Viewing the Dashboard

Once the pipeline has completed, you can explore the results using our interactive Streamlit web dashboard:
```bash
streamlit run scripts/dashboard.py
```
This will spin up a local server and open the dashboard in your default web browser at `http://localhost:8501`. You can compare strategy performance, see where the self-repair loop succeeded, inspect passing/failed test runs, and view the side-by-side original and repaired code!

---

## Evaluation Results & Key Engineering Insights

We validated our system using a robust benchmark of **136 distinct test cases** (34 sampled focal functions generated across all 4 prompt strategies) executed locally on Llama3. The results highlight several critical successes in AI-agent resilience and code generation quality:

### 1. Exceptional Resiliency via the Self-Healing Loop
A primary engineering challenge with raw LLM-generated code is its tendency to fail on runtime imports, missing mocks, or logical assumptions. Rather than allowing these tests to remain broken, our autonomous self-repair architecture successfully intervened:
* Out of 80 initially failing tests, the system initiated targeted self-repair cycles and **autonomously fixed 25 tests** (representing a highly successful **31.25% self-healing recovery rate**).
* This self-healing pipeline directly raised the final, compilable passing rate of our test suites to **59.5%** (**81 out of 136 tests** completely verified and passing).

### 2. Flawless Syntactic Compilation (97.8% Success)
Out of 136 raw generated files, only **3 tests** encountered compilation or syntax errors. This proves that contemporary LLMs possess an exceptional **97.8% syntactic accuracy** in Python. The vast majority of failures are confined entirely to logical discrepancies (such as asserting against empty stubs returning `None`) rather than raw syntax issues, proving that the runtime sandboxed executor is the exact tool needed to bridge the gap.

### 3. Data-Driven Prompt Strategy Optimization
Our AST-based code analyzer programmatically graded the logical depth of each passing test suite across 11 critical edge-case categories:
* **Prompt Strategy Impact**: Enforcing structured target edge cases and parametrization (Advanced strategy) successfully drove deep edge-case coverage to a top average of **40.3%**.
* **LLM Coverage Patterns**: The models naturally showed strong proficiency in writing assertions for **None checks** (55.8% frequency) and **zero boundaries** (42.6%).
* **Logical Blindspots**: The evaluation revealed that models rarely test for **large numeric scale** (3.6%) or **unicode edge cases** (0.7%) without explicit developer directives, proving the necessity of hybrid developer-in-the-loop strategies.

---

## Project Directory Map

* **`configs/`**: Contains `prompt_strategies.json` which holds the templates and temperatures for our AI models.
* **`scripts/`**: The core execution scripts for extracting, sampling, generating, executing, repairing, and grading tests, along with the dashboard UI.
* **`results/`**: Where all pipeline outputs, logs, execution summaries, and AST scores are saved in JSON format.
* **`requirements.txt`**: The pip packages needed to run the project.
* **`pymethods2test/`**: The local storage directory containing the focal-method dataset files.
