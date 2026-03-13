from core.github_client import github_api
from core.logger import logger

class PRGatekeeper:
    def __init__(self, risk_threshold: float = 75.0):
        self.risk_threshold = risk_threshold

    def evaluate_and_enforce(self, repo_name: str, sha: str, risk_score: float):
        """Hard Gate: Blocks the PR merge button if blast radius is too high."""
        if risk_score >= self.risk_threshold:
            state = "failure"
            desc = f"Merge Blocked: Deployment Risk is {risk_score:.1f}% (High Blast Radius)"
            logger.warning(f"GATEKEEPER BLOCKED PR COMMIT: {sha}")
        else:
            state = "success"
            desc = f"Cleared: Deployment Risk is {risk_score:.1f}%"
            logger.info(f"GATEKEEPER APPROVED PR COMMIT: {sha}")

        github_api.set_status_check(repo_name, sha, state, desc)

gatekeeper = PRGatekeeper()