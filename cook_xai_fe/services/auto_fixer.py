import re
from core.github_client import github_api
from engines.ast_analyzer import ast_engine
from core.logger import logger

class AutoFixer:
    def process_fix_command(self, repo_name: str, pr_number: int, comment_body: str):
        """
        Intercepts issue comments like '/fix bad_code.py'
        Finds the PR branch, fetching the file, running AST, and pushing the fix.
        """
        # Parse the command
        match = re.search(r'/fix\s+([/\w.-]+)', comment_body)
        if not match:
            return
            
        file_path = match.group(1).strip()
        logger.info(f"Auto-fixing requested for {file_path} in {repo_name} PR #{pr_number}")
        
        # 1. We need the PR branch name to push to
        pr_data = github_api.get_pr_details(repo_name, pr_number)
        if not pr_data:
            github_api.post_comment(repo_name, pr_number, f"❌ Auto-Fix Failed: Could not fetch PR #{pr_number} details.")
            return
            
        branch = pr_data['head']['ref']
        
        # 2. Fetch the current file content from that branch
        file_data = github_api.get_file_content(repo_name, file_path, branch)
        if not file_data:
            github_api.post_comment(repo_name, pr_number, f"❌ Auto-Fix Failed: Could not find `{file_path}` in branch `{branch}`.")
            return
            
        raw_code = file_data['content']
        file_sha = file_data['sha']
        
        # 3. Ask AST Engine what to fix
        scan_result = ast_engine.scan(raw_code, file_path)
        suggestions = scan_result.get("suggestions", [])
        
        if not suggestions:
            github_api.post_comment(repo_name, pr_number, f"ℹ️ Auto-Fix: No structural fixes available for `{file_path}`.")
            return
            
        # 4. Apply all fixes to the raw string (Naive capstone approach)
        new_code = raw_code
        applied_fixes = 0
        
        for sug in suggestions:
            if "original" in sug and "fix" in sug and sug["original"] in new_code:
                new_code = new_code.replace(sug["original"], sug["fix"])
                applied_fixes += 1
                
        if applied_fixes == 0:
            github_api.post_comment(repo_name, pr_number, f"⚠️ Auto-Fix Failed: Could not apply fixes to `{file_path}` safely.")
            return
            
        # 5. Push the new commit!
        msg = f"🤖 Enterprise XAI: Auto-fixed {applied_fixes} issues in {file_path}"
        success = github_api.update_file(repo_name, file_path, new_code, msg, file_sha, branch)
        
        if success:
            github_api.post_comment(repo_name, pr_number, f"✅ **Auto-Fix Successful!**\n\nThe XAI engine just pushed `{msg}` to your branch. A new review will start shortly.")
        else:
             github_api.post_comment(repo_name, pr_number, f"❌ Auto-Fix Failed: Could not push commit to GitHub.")

auto_fixer = AutoFixer()
