# # code_quality.py
# """
# Evaluate Hugging Face model code quality programmatically.
# Submetrics:
# - Python code quality (docstrings, complexity, lint) [weight 0.4]
# - README presence [weight 0.2]
# - LICENSE presence [weight 0.2]
# - Example notebook presence [weight 0.2]
# Only downloads small repo files, not full weights.
# """

# import ast
# import subprocess
# import time
# from huggingface_hub import HfApi, hf_hub_download
# from pathlib import Path

# # --------- Helper functions ---------

# def run_command(cmd):
#     """Run shell command and return stdout."""
#     result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
#     return result.stdout

# def get_repo_files(model_name):
#     """Return a list of all files in the HF repo."""
#     api = HfApi()
#     try:
#         return api.list_repo_files(repo_id=model_name)
#     except Exception:
#         return []

# def download_file(model_name, filename):
#     """Download a single file and return local path."""
#     try:
#         return hf_hub_download(repo_id=model_name, filename=filename)
#     except Exception:
#         return None

# # --------- Submetric calculators ---------

# def python_files_score(model_name):
#     """Calculate Python code submetric (docstrings, complexity, lint)."""
#     py_files = [f for f in get_repo_files(model_name) if f.endswith(".py")]
#     if not py_files:
#         return 0.0

#     doc_percent = []
#     complexity_vals = []
#     lint_vals = []

#     for f in py_files:
#         local_path = download_file(model_name, f)
#         if not local_path:
#             continue

#         # Docstring coverage
#         try:
#             with open(local_path, "r", encoding="utf-8") as fi:
#                 tree = ast.parse(fi.read())
#             funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
#             with_doc = [n for n in funcs if ast.get_docstring(n)]
#             doc_percent.append(len(with_doc)/len(funcs) if funcs else 1.0)
#         except Exception:
#             doc_percent.append(0.0)

#         # Cyclomatic complexity
#         try:
#             out = run_command(f"radon cc {local_path} -s -a")
#             avg = 1.0
#             for line in out.splitlines():
#                 if "Average complexity" in line:
#                     avg = max(0, 1 - float(line.split()[3])/10)
#             complexity_vals.append(avg)
#         except Exception:
#             complexity_vals.append(0.0)

#         # Lint issues
#         try:
#             out = run_command(f"flake8 {local_path} --exit-zero --statistics")
#             total = 0
#             for line in out.splitlines():
#                 parts = line.strip().split()
#                 if parts and parts[0].isdigit():
#                     total += int(parts[0])
#             lint_vals.append(max(0, 1 - total/20))
#         except Exception:
#             lint_vals.append(0.0)

#     if not doc_percent:
#         return 0.0
#     # Aggregate submetrics
#     doc_score = sum(doc_percent)/len(doc_percent)
#     complexity_score = sum(complexity_vals)/len(complexity_vals)
#     lint_score_val = sum(lint_vals)/len(lint_vals)
#     return 0.4*doc_score + 0.3*complexity_score + 0.3*lint_score_val

# def readme_score(model_name):
#     files = get_repo_files(model_name)
#     for f in files:
#         if f.lower().startswith("readme"):
#             return 1.0
#     return 0.0

# def license_score(model_name):
#     files = get_repo_files(model_name)
#     for f in files:
#         if "license" in f.lower():
#             return 1.0
#     return 0.0

# def notebook_score(model_name):
#     files = get_repo_files(model_name)
#     for f in files:
#         if f.endswith(".ipynb"):
#             return 1.0
#     return 0.0

# # --------- Main metric calculator ---------

# def code_quality_score(model_name):
#     """
#     Calculate overall code quality for a Hugging Face model.
#     Returns: (score 0-1 float, latency in seconds)
#     """
#     start_time = time.time()

#     py_score = python_files_score(model_name)          # 0.4 submetric
#     rd_score = readme_score(model_name) * 0.2         # README weight
#     lic_score = license_score(model_name) * 0.2       # LICENSE weight
#     nb_score = notebook_score(model_name) * 0.2       # Notebook weight

#     print(py_score)
#     print(rd_score) #
#     print(lic_score) #
#     print(nb_score)


#     overall_score = py_score + rd_score + lic_score + nb_score
#     latency = time.time() - start_time
#     return overall_score, latency

# # --------- Test / CLI ---------
# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) < 2:
#         print("Usage: python code_quality.py <model_name>")
#         sys.exit(1)
#     model_name = sys.argv[1]
#     score, latency = code_quality_score(model_name)
#     print(f"Code quality score for {model_name}: {score:.3f}, latency: {latency:.2f}s")

# code_quality.py
"""
Evaluate Hugging Face model repository quality.
Submetrics:
- JSON/config presence and validity [weight 0.4]
- README presence [weight 0.2]
- LICENSE presence [weight 0.2]
- Example notebooks / usage examples [weight 0.2]
Only fetches repo metadata/files, not full model weights.
"""

import json
import time
from huggingface_hub import HfApi, hf_hub_download

# --------- Helper functions ---------


def get_repo_files(model_name):
    """Return a list of all files in the HF repo."""
    api = HfApi()
    try:
        return api.list_repo_files(repo_id=model_name)
    except Exception:
        return []


def download_file(model_name, filename):
    """Download a single file and return local path."""
    try:
        return hf_hub_download(repo_id=model_name, filename=filename)
    except Exception:
        return None


# --------- Submetric calculators ---------


def json_score(model_name):
    """Score based on presence and validity of JSON/config files."""
    files = get_repo_files(model_name)
    json_files = [f for f in files if f.endswith(".json")]
    if not json_files:
        return 0.0

    valid_count = 0
    for f in json_files:
        local_path = download_file(model_name, f)
        if not local_path:
            continue
        try:
            with open(local_path, "r", encoding="utf-8") as fi:
                json.load(fi)
            valid_count += 1
        except Exception:
            continue

    score = valid_count / len(json_files)
    return score * 0.4  # weight of 0.4


def readme_score(model_name):
    files = get_repo_files(model_name)
    for f in files:
        if f.lower().startswith("readme"):
            return 0.2
    return 0.0


def license_score(model_name):
    files = get_repo_files(model_name)
    for f in files:
        if "license" in f.lower():
            return 0.2
    return 0.0


# --------- Main metric calculator ---------


def code_quality_score(model_name):
    """
    Calculate overall code quality for a Hugging Face model repo.
    Returns: (score 0-1 float, latency in seconds)
    """
    start_time = time.time()

    j_score = json_score(model_name)
    rd_score = readme_score(model_name)
    lic_score = license_score(model_name)

    print(j_score)
    print(rd_score)  #
    print(lic_score)  #

    overall_score = j_score + rd_score + lic_score
    latency = time.time() - start_time
    return overall_score, latency


# --------- Test / CLI ---------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python code_quality.py <model_name>")
        sys.exit(1)
    model_name = sys.argv[1]
    score, latency = code_quality_score(model_name)
    print(f"Code quality score for {model_name}: {score:.3f}, latency: {latency:.2f}s")
