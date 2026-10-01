"""Read-only verification of human review, behind a replaceable API adapter."""
from __future__ import annotations

import base64
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from .records import WorkflowError, canonical_json, load_json, sha256

POLICY = "workflow/policy.json"


class RemoteNotFound(WorkflowError):
    """A verified HTTP 404, distinct from unavailable approval verification."""


def git(root: Path, *args) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise WorkflowError("trusted Git revision unavailable") from exc


def trusted_policy(root: Path, ref: str) -> tuple[dict, str, str]:
    commit = git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise WorkflowError("invalid trusted Git commit")
    git(root, "merge-base", "--is-ancestor", commit, "HEAD")
    try:
        text = subprocess.check_output(["git", "show", f"{commit}:{POLICY}"], cwd=root, stderr=subprocess.PIPE).decode("utf-8")
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        raise WorkflowError("trusted reviewer policy unavailable") from exc
    return parse_policy(text), commit, text


def parse_policy(text):
    try:
        policy = load_json(text)
    except json.JSONDecodeError as exc:
        raise WorkflowError("invalid trusted reviewer policy") from exc
    fields = {"schema_version", "repository", "researchers", "maintainers", "owners"}
    if not isinstance(policy, dict) or set(policy) != fields or type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise WorkflowError("invalid reviewer policy fields")
    if not isinstance(policy["repository"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", policy["repository"]):
        raise WorkflowError("invalid review repository")
    if not isinstance(policy["owners"], dict):
        raise WorkflowError("reviewer owner mapping required")
    for names in [policy["researchers"], policy["maintainers"], *policy["owners"].values()]:
        if not isinstance(names, list) or any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9-]+", n) for n in names):
            raise WorkflowError("invalid human reviewer assignment")
    return policy


def gh_api(endpoint: str):
    """No shell, no writes, no credential values in errors or output."""
    try:
        raw = subprocess.check_output(
            ["gh", "api", "--hostname", "github.com", "-H", "Accept: application/vnd.github+json", endpoint],
            stderr=subprocess.PIPE, timeout=30,
        )
        return load_json(raw)
    except subprocess.CalledProcessError as exc:
        try:
            error = load_json(exc.output)
            if isinstance(error, dict) and str(error.get("status")) == "404":
                raise RemoteNotFound("reviewed path does not exist") from exc
        except (json.JSONDecodeError, UnicodeError, TypeError):
            pass
        raise WorkflowError("GitHub review verification unavailable; proposal remains pending") from exc
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise WorkflowError("GitHub review verification unavailable; proposal remains pending") from exc


class GitHubReviews:
    """The supplied fetch function is the trusted external-system boundary."""

    def __init__(self, *, fetch=gh_api):
        self.fetch = fetch

    def verify(self, proposal: dict, policy: dict, groups: dict[str, set[str]], pull_number: int):
        if type(pull_number) is not int or pull_number < 1:
            raise WorkflowError("positive pull request number required")
        if any(not group for group in groups.values()):
            raise WorkflowError("human reviewer assignments are not configured in trusted policy")
        repo = policy["repository"]
        endpoint = f"repos/{repo}/pulls/{pull_number}"
        try:
            pr = self.fetch(endpoint)
            if pr["base"]["repo"]["full_name"].lower() != repo.lower() or pr.get("draft") or (pr["state"] != "open" and not pr.get("merged")):
                raise WorkflowError("pull request is not an eligible human review")
            head = pr["head"]["sha"]
            head_repo = pr["head"]["repo"]["full_name"]
            if not re.fullmatch(r"[0-9a-f]{40,64}", head) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", head_repo):
                raise WorkflowError("invalid reviewed commit/repository")
            proposal_path = f"docs/workflow/proposals/{proposal['digest']}.json"
            content = self.fetch(f"repos/{head_repo}/contents/{quote(proposal_path)}?ref={head}")
            if content.get("encoding") != "base64":
                raise WorkflowError("reviewed proposal content unavailable")
            reviewed = load_json(base64.b64decode(content["content"], validate=False))
            if canonical_json(reviewed) != canonical_json(proposal):
                raise WorkflowError("reviewed proposal differs from the requested change")
            for path, expected in proposal["snapshot"].items():
                try:
                    source = self.fetch(f"repos/{head_repo}/contents/{quote(path)}?ref={head}")
                except RemoteNotFound:
                    if expected is None:
                        continue
                    raise WorkflowError("reviewed source snapshot is missing")
                if expected is None or source.get("encoding") != "base64" or sha256(base64.b64decode(source["content"])) != expected:
                    raise WorkflowError(f"reviewed source snapshot differs at {path}")
            reviews = []
            page = 1
            while True:
                batch = self.fetch(f"{endpoint}/reviews?per_page=100&page={page}")
                if not isinstance(batch, list):
                    raise WorkflowError("invalid review API response")
                reviews.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
                if page > 100:
                    raise WorkflowError("review history exceeds supported page limit")
            latest = {}
            for review in reviews:
                if review.get("state") in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
                    latest[review["user"]["login"].lower()] = review
            approvals = []
            author = pr["user"]["login"].lower()
            authorized = set().union(*groups.values())
            if any(r["state"] == "CHANGES_REQUESTED" for who, r in latest.items() if who in authorized):
                raise WorkflowError("an authorized reviewer requests changes")
            for role, names in sorted(groups.items()):
                candidates = [r for who, r in latest.items() if who in names and who != author
                              and r["state"] == "APPROVED" and r.get("commit_id") == head
                              and r["user"].get("type") == "User" and r.get("submitted_at")]
                if not candidates:
                    raise WorkflowError(f"missing current human approval for {role}")
                review = candidates[-1]
                approvals.append({"role": role, "reviewer": review["user"]["login"], "review_id": review["id"],
                                  "commit": head, "url": review["html_url"], "submitted_at": review["submitted_at"]})
            if self.fetch(endpoint)["head"]["sha"] != head:
                raise WorkflowError("reviewed pull request changed during approval verification")
            return approvals
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            if isinstance(exc, WorkflowError):
                raise
            raise WorkflowError("incomplete or invalid GitHub approval evidence") from exc
