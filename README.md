# SafeSQL: Dual-Layer Verification Framework

SafeSQL is a research framework for trustworthy natural language to SQL translation. It implements a **dual-layer verification** system: a **guardrails** layer during generation and a **verification** layer before execution (schema validation, constraints, semantic checks, and optional auto-repair).

**Author:** Krishna Mohan Sripada  
**Student number:** PN1187423  
**Course:** M.Sc. Data Science  

---

## Prerequisites

- Python 3.10 or newer  
- **OpenAI API key** (for GPT-4–based evaluation and demos)  
- **Hugging Face token** (optional; for some dataset/model access)  
- CUDA-capable GPU (optional; for local LLaMA-style models)

Large datasets and model weights are not bundled with this repository; download them separately where noted below.

---

## Installation

From the project root (`SafeSQL_Research`):

```bash
python -m venv venv
```

Activate the virtual environment:

- **Windows (PowerShell):** `venv\Scripts\activate`  
- **Linux/macOS:** `source venv/bin/activate`

Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Optional editable install:

```bash
pip install -e .
```

### Environment variables

Create a file named `.env` in the project root (do not commit it). Example:

```env
OPENAI_API_KEY=your_openai_key_here
HUGGINGFACE_TOKEN=your_huggingface_token_here
```

`.env` is listed in `.gitignore`.

---

## Repository layout

| Path | Purpose |
|------|---------|
| **`src/`** | Main Python package: guardrails, verification, models, data loaders, evaluation helpers, utilities. |
| **`src/guardrails/`** | Layer 1: constrained decoding, grammar-guided generation, policy enforcement, pattern matching. |
| **`src/verification/`** | Layer 2: schema validation, constraint checking, semantic analysis, auto-repair, orchestrating verifier. |
| **`src/models/`** | LLM integrations: GPT-4 generator, LLaMA generator, base interfaces. |
| **`src/data/`** | Dataset loaders (Spider, BIRD, WikiSQL_VALUE) and schema preprocessors. |
| **`src/evaluation/`** | Evaluation orchestration (`evaluator.py`). |
| **`src/utils/`** | Config loading, SQL parsing, database helpers, logging. |
| **`config/`** | YAML configuration (e.g. `settings.yaml`, safety policies). |
| **`data/`** | Dataset layout: `datasets/` (raw benchmarks), `processed/`, `schemas/`. Paths are configured in `config/`. |
| **`scripts/`** | Runnable entry points: verification, demos, downloads, dataset checks, and evaluation drivers. |
| **`tests/`** | `pytest` tests (e.g. unit tests for the SQL parser). |
| **`analysis_output/`** | Generated analysis artifacts (figures, reports) when you run analysis scripts. |
| **`evaluation_results/`** | Default location for JSON and logs from evaluation runs (when scripts write here). |
| **`Final_thesis_chapters/`** | Thesis chapter text files for the related dissertation work. |
| **`docx_extract/`** | Extracted content from thesis documents (if present). |
| **`requirements.txt`** | Pinned dependency list for `pip`. |
| **`setup.py`** | Package metadata and install configuration. |
| **`create_presentation.py`** | Helper script for building presentation assets. |
| **`SafeSQL_Thesis_Presentation.pptx`** | Thesis presentation file (if included in your copy). |
| **`venv/`** | Local virtual environment (created by you; should not be uploaded if your institution expects a clean archive). |

Upstream dataset folders under `data/datasets/` (for example **Spider**) may include their own `README.md` files from the original releases; those describe the benchmark, not this project.

---

## Configuration

YAML files in `config/` control models, paths, and safety rules. Load settings in code:

```python
from src.utils import ConfigLoader

config = ConfigLoader()
temperature = config.get("models.gpt4.temperature")
```

Adjust `config/settings.yaml` and safety policy YAML files to match your machine paths and experiment settings.

---

## Verify the environment

```bash
python scripts/verify_installation.py
```

Quick import check:

```bash
python -c "from src.utils import ConfigLoader; print('OK')"
```

---

## Datasets

Benchmarks are large and are usually **downloaded separately**.

### Spider (common default)

1. Obtain **Spider 1.0** from the official site: [https://yale-lily.github.io/spider](https://yale-lily.github.io/spider)  
2. Extract so that paths resemble:

```
data/datasets/spider/
  dev.json
  tables.json
  database/    # per-database SQLite folders
```

### WikiSQL_VALUE (optional)

Use `scripts/download_wikisql_value.py` or follow the dataset’s instructions and place files under the paths expected by `config/` and the WikiSQL loaders.

### Status check

```bash
python scripts/check_datasets_status.py
```

---

## Main workflows

### Smoke test on datasets

After Spider (and optionally WikiSQL_VALUE) is in place and `.env` is set:

```bash
python scripts/test_both_datasets.py
```

### Run evaluations (Spider / WikiSQL)

Examples:

```bash
# Spider only
python scripts/run_models_spider_bird.py --spider_only --n_samples 50

# WikiSQL_VALUE only
python scripts/run_models_spider_bird.py --wikisql_only --n_samples 50

# Both
python scripts/run_models_spider_bird.py --n_samples 50
```

Results are written under `evaluation_results/` (exact filenames depend on the script and options).

### Other useful scripts

| Script | Role |
|--------|------|
| `demo_complete_system.py` | End-to-end demo of the stack |
| `demo_guardrails.py`, `demo_verifier.py`, `demo_schema_validator.py`, … | Layer-wise demos |
| `evaluate_accuracy.py`, `evaluate_comprehensive.py`, `evaluate_safety_suite.py` | Accuracy and safety evaluations |
| `analyze_results.py` | Summarize evaluation outputs |
| `download_datasets.py` / `download_wikisql_value.py` | Dataset acquisition helpers |

Use `python scripts/<name>.py --help` where supported.

---

## Tests

```bash
pytest
pytest tests/unit/test_sql_parser.py
pytest --cov=src --cov-report=html
```

---

## Evaluation metrics (summary)

Typical Text-to-SQL metrics include **execution accuracy (EX)** and **exact match (EM)**. SafeSQL additionally tracks safety-related outcomes (e.g. guardrails and verification pass rates, repair success). Exact definitions match the implementations in `scripts/` and `src/evaluation/`.

---

## Troubleshooting

- **Import errors:** Activate `venv` and run `pip install -r requirements.txt`.  
- **API errors:** Confirm `.env` keys and run `python scripts/test_api_key_simple.py` if available.  
- **Missing data:** Run `scripts/check_datasets_status.py` and align folder layout with `config/`.  

---

## License

Research project; license to be determined by the author/institution.

---

## Acknowledgments

This work builds on ideas and benchmarks from the broader Text-to-SQL literature, including systems and datasets such as Spider and related safety-focused research (e.g. SAFE-SQL, METASQL, and others referenced in the thesis).

---

**Version:** 0.1.0  
