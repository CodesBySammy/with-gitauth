import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.github_client import github_api
from engines.xai_explainer import xai_engine
from engines.nlp_codebert import nlp_engine
from engines.ast_analyzer import ast_engine
from engines.rag_python_imports import rag_engine
from services.pr_gatekeeper import gatekeeper
from core.logger import logger


def _scan_single_file(file_data: dict) -> dict:
    """
    Fetch and scan a single Python file through all engines.
    Returns a dict with partial reports for aggregation.
    """
    filename = file_data.get("filename", "")
    raw_url = file_data.get("raw_url", "")
    result = {"filename": filename, "nlp": "", "ast": {}, "deps": []}

    raw_code = github_api.fetch_raw_code(raw_url)
    if not raw_code:
        return result

    try:
        tree = ast.parse(raw_code)
    except SyntaxError:
        tree = None

    # CodeBERT semantic scan
    result["nlp"] = nlp_engine.scan(raw_code, filename)

    # AST structural scan (returns dict with mi, complexity, suggestions)
    result["ast"] = ast_engine.scan(raw_code, filename, tree=tree)

    # RAG dependency extraction
    result["deps"] = rag_engine.extract_dependencies(raw_code, tree=tree)

    return result


def process_pipeline(repo_name: str, pr_number: int, head_sha: str, token: str = None):
    try:
        _run_pipeline(repo_name, pr_number, head_sha, token)
    except Exception:
        logger.exception(f"Pipeline FAILED for {repo_name} PR #{pr_number}")


def _run_pipeline(repo_name: str, pr_number: int, head_sha: str, token: str = None):
    logger.info(f"Starting Enterprise Review Pipeline for {repo_name} PR #{pr_number}")

    pr_files = github_api.get_pr_files(repo_name, pr_number, token)
    if not pr_files:
        return

    # Check for tests (Enterprise Requirement)
    has_tests = any("test" in f.get("filename", "").lower() for f in pr_files)

    # Metrics for ML risk model
    la = sum(f.get("additions", 0) for f in pr_files)
    ld = sum(f.get("deletions", 0) for f in pr_files)
    nf = len(pr_files)

    risk_score, xai_report = xai_engine.analyze_risk(la, ld, nf)

    py_files = [f for f in pr_files if f.get("filename", "").endswith(".py")]

    # Initialize Table contents
    nlp_rows = []
    ast_rows = []
    rag_rows = []
    mi_scores = []
    
    if py_files:
        with ThreadPoolExecutor(max_workers=min(4, len(py_files))) as pool:
            futures = {pool.submit(_scan_single_file, f): f for f in py_files}

            for future in as_completed(futures):
                try:
                    res = future.result()
                except Exception as e:
                    logger.error(f"Scan failed: {e}")
                    continue

                filename = res["filename"]
                
                # NLP
                if res["nlp"]: nlp_rows.append(res["nlp"])
                
                # AST
                ast_data = res["ast"]
                if ast_data:
                    mi = ast_data.get("mi", "N/A")
                    mi_display = f"🟢 {mi}" if isinstance(mi, float) and mi > 20 else f"🔴 {mi}"
                    mi_scores.append(f"| `{filename}` | {mi_display}/100 |")
                    
                    for cx in ast_data.get("complexity", []):
                        ast_rows.append(cx)
                    for sug in ast_data.get("suggestions", []):
                        ast_rows.append(sug)

                # RAG
                if res["deps"]: rag_rows.append(f"`{filename}`: {', '.join(res['deps'])}")

    # -----------------------------
    # BUILD ENTERPRISE MARKDOWN REPORT
    # -----------------------------
    final_report = "## 🛡️ Enterprise Automated PR Review\n\n"
    
    # Overview & Magic Fix Command
    final_report += "> **Review Summary**: PR scanned by CodeBERT (Semantic), AST Analyzer (Structural), and Random Forest SHAP (Deployment Risk).\n"
    final_report += "> 💡 **Auto-Fix Available**: Reply to this comment with `/fix <filename>` (e.g., `/fix bad_code.py`) and the AI will automatically push the suggested fixes directly to this branch!\n\n"
    
    # Test Coverage Enforcement (Capstone Soft-Requirement)
    if not has_tests:
        final_report += "### 🧪 Capstone Quality Recommendation\n"
        final_report += "> **No tests detected in this PR**. While not strictly enforced, adding unit tests demonstrates industry-standard rigor.\n\n"

    # XAI Report
    final_report += f"{xai_report}\n\n"
    
    # Deep Scans
    if py_files:
        final_report += "### 🔬 Code Quality & Maintenance\n\n"
        
        # Detailed AST Output with Fix commands
        final_report += "<details open><summary><b>Code Correctness & Auto-Fixes (AST)</b></summary>\n\n"
        
        if not ast_rows:
            final_report += "| 🟢 Passed | No structural issues | Clean code architecture |\n\n"
        else:
            for ast_item in ast_rows:
                if isinstance(ast_item, dict): 
                    if "title" in ast_item:
                        # It's an auto-fix suggestion
                        final_report += f"#### 🚨 {ast_item['title']} (Line {ast_item['line']})\n"
                        final_report += f"{ast_item['description']}\n\n"
                        final_report += f"**❌ Current Code**:\n```python\n{ast_item['original']}\n```\n"
                        final_report += f"**✅ Proposed Fix**:\n```python\n{ast_item['fix']}\n```\n"
                        final_report += f"*⚡ Apply this fix by replying with: `/fix {filename}`*\n\n"
                        final_report += "---\n\n"
                    elif "score" in ast_item:
                        # It's a complexity row
                        final_report += f"| 🔴 Complexity | `{ast_item['name']}` is too complex | Score: {ast_item['score']} |\n\n"
                elif isinstance(ast_item, str):
                    # Legacy string fallback
                    final_report += ast_item + "\n\n"
                    
        final_report += "</details>\n\n"

        final_report += "<details><summary><b>Maintainability Index (MI)</b></summary>\n\n"
        final_report += "> Maintainability Index evaluates complexity, comments, and structure. >20 is good.\n\n"
        final_report += "| File | Maintainability Score (0-100) |\n|------|-------------------------------|\n"
        final_report += "\n".join(mi_scores) + "\n\n"
        final_report += "</details>\n\n"

        final_report += "<details><summary><b>Semantic Security Constraints (CodeBERT)</b></summary>\n\n"
        final_report += "| File | Threat Label | Model Confidence |\n|------|--------------|------------------|\n"
        if nlp_rows:
            final_report += "\n".join(nlp_rows) + "\n\n"
        else:
            final_report += "| 🟢 Passed | No vulnerabilities detected | High |\n\n"
        final_report += "</details>\n\n"

        if rag_rows:
            final_report += "<details><summary><b>Integration Dependencies</b></summary>\n\n"
            final_report += "\n".join([f"- {r}" for r in rag_rows]) + "\n\n"
            final_report += "</details>\n"
    else:
        final_report += "> ℹ️ No Python (`.py`) files modified. Deep inspections skipped."

    github_api.post_comment(repo_name, pr_number, final_report, token)
    gatekeeper.evaluate_and_enforce(repo_name, head_sha, risk_score, token)
