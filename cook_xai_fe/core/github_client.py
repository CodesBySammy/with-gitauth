import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from core.config import settings
from core.logger import logger

class GitHubClient:
    """GitHub API client with retry logic and request timeouts."""
    
    TIMEOUT = 30  # seconds

    def __init__(self):
        self.base_url = "https://api.github.com"
        self.session = requests.Session()

        # Retry on transient failures and rate limits
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}" if settings.GITHUB_TOKEN else ""
        })

    def _get_headers(self, token: str = None) -> dict:
        """Helper to get headers, optionally overriding the token."""
        use_token = token or settings.GITHUB_TOKEN
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if use_token:
            headers["Authorization"] = f"Bearer {use_token}"
        return headers

    def get_pr_files(self, repo_name: str, pr_number: int, token: str = None) -> list:
        url = f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}/files"
        try:
            res = self.session.get(url, headers=self._get_headers(token), timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json()
            logger.error(f"Error fetching PR files: HTTP {res.status_code} — {res.text[:200]}")
        except requests.RequestException as e:
            logger.error(f"Network error fetching PR files: {e}")
        return []

    def get_pr_details(self, repo_name: str, pr_number: int, token: str = None) -> dict:
        url = f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}"
        try:
            resp = self.session.get(url, headers=self._get_headers(token), timeout=self.TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch PR details: {e}")
            return {}

    def fetch_raw_code(self, raw_url: str) -> str:
        if not raw_url:
            return ""
        try:
            resp = requests.get(raw_url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch raw code: {e}")
            return ""

    def get_file_content(self, repo_name: str, file_path: str, ref: str, token: str = None) -> dict:
        """
        Fetch file details (including content and SHA) via GitHub API.
        Required for updating a file.
        """
        url = f"{self.base_url}/repos/{repo_name}/contents/{file_path}?ref={ref}"
        try:
            resp = self.session.get(url, headers=self._get_headers(token), timeout=self.TIMEOUT) # Changed to self.session.get and self.TIMEOUT
            resp.raise_for_status()
            data = resp.json()
            # Content is base64 encoded
            decoded_content = base64.b64decode(data['content']).decode('utf-8')
            return {"sha": data["sha"], "content": decoded_content}
        except requests.RequestException as e:
            logger.error(f"Failed to get file content for {file_path} on {ref}: {e}")
            return None

    def update_file(self, repo_name: str, file_path: str, new_content: str, commit_message: str, file_sha: str, branch: str, token: str = None) -> bool:
        """
        Push a commit directly to the branch modifying the specified file.
        """
        url = f"{self.base_url}/repos/{repo_name}/contents/{file_path}"
        encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": commit_message,
            "content": encoded_content,
            "sha": file_sha,
            "branch": branch
        }
        
        try:
            resp = self.session.put(url, headers=self._get_headers(token), json=payload, timeout=self.TIMEOUT) # Changed to self.session.put and self.TIMEOUT
            resp.raise_for_status()
            logger.info(f"Successfully pushed commit to {file_path} on branch {branch}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to update file {file_path}: {e}")
            return False

    def post_comment(self, repo_name: str, pr_number: int, body: str, token: str = None):
        url = f"{self.base_url}/repos/{repo_name}/issues/{pr_number}/comments" # Changed to use self.base_url
        payload = {"body": body} # Extracted payload
        try:
            res = self.session.post(url, json=payload, headers=self._get_headers(token), timeout=self.TIMEOUT) # Changed to use self._get_headers(token)
            if res.status_code == 201:
                logger.info(f"Review posted to PR #{pr_number}")
            else:
                logger.error(f"Failed to post comment: HTTP {res.status_code} — {res.text[:200]}")
        except requests.RequestException as e:
            logger.error(f"Network error posting comment: {e}")

    def set_status_check(self, repo_name: str, sha: str, state: str, description: str, token: str = None): # Renamed to set_status_check as per original, added token
        url = f"{self.base_url}/repos/{repo_name}/statuses/{sha}"
        payload = {
            "state": state,
            "description": description[:140], # Kept original description length
            "context": "XAI PR Gatekeeper" # Kept original context
        }
        try:
            res = self.session.post(url, json=payload, headers=self._get_headers(token), timeout=self.TIMEOUT) # Changed to use self._get_headers(token)
            if res.status_code == 201:
                logger.info(f"Status check '{state}' set for commit {sha[:7]}")
            else:
                logger.warning(f"Status check response: HTTP {res.status_code}")
        except requests.RequestException as e:
            logger.error(f"Network error setting status check: {e}")

    def check_webhook_exists(self, repo_name: str, webhook_url: str, token: str = None) -> bool:
        """Verifies if the specific webhook URL exists on the target repository."""
        url = f"{self.base_url}/repos/{repo_name}/hooks"
        try:
            res = self.session.get(url, headers=self._get_headers(token), timeout=self.TIMEOUT)
            if res.status_code == 200:
                hooks = res.json()
                for hook in hooks:
                    if hook.get("config", {}).get("url") == webhook_url:
                        return True
            return False
        except requests.RequestException as e:
            logger.error(f"Network error checking webhook exists: {e}")
            return False

    def create_webhook(self, repo_name: str, webhook_url: str, secret: str, token: str = None) -> bool: # Added token
        """Create or update a webhook on a target repository""" # Kept original docstring
        url = f"{self.base_url}/repos/{repo_name}/hooks"
        
        payload = {
            "name": "web",
            "active": True,
            "events": ["pull_request"], # Kept original events
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0",
                "secret": secret
            }
        }
        
        try:
            res = self.session.post(url, json=payload, headers=self._get_headers(token), timeout=self.TIMEOUT)
            if res.status_code == 201:
                logger.info(f"✅ Successfully created webhook on {repo_name} pointing to {webhook_url}")
                return True
            else:
                # If it already exists (422)
                try:
                    error_data = res.json()
                    for error in error_data.get("errors", []):
                        if "Hook already exists" in error.get("message", ""):
                            logger.info(f"✅ Webhook already exists on {repo_name}")
                            return True
                except ValueError:
                    pass
                
                logger.error(f"Failed to create webhook on {repo_name}: HTTP {res.status_code} - {res.text[:200]}")
                return False
        except requests.RequestException as e:
            logger.error(f"Network error creating webhook: {e}")
            return False

github_api = GitHubClient()