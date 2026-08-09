import os
import requests
from dotenv import load_dotenv


# Load variables from .env
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")

BASE_URL = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2026-03-10",
}


def github_get(endpoint, params=None):
    """
    Send a GET request to the GitHub API.
    """

    url = f"{BASE_URL}{endpoint}"

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response


def get_paginated_data(endpoint, params=None):
    """
    Retrieve all pages of results from a GitHub API endpoint.
    """

    if params is None:
        params = {}

    params["per_page"] = 100

    all_items = []
    page = 1

    while True:
        params["page"] = page

        response = github_get(endpoint, params=params)

        items = response.json()

        all_items.extend(items)

        if len(items) < 100:
            break

        page += 1

    return all_items


def get_repository():
    """
    Fetch basic repository information.
    """

    endpoint = f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

    return github_get(endpoint).json()


def get_issues():
    """
    Fetch repository issues.

    GitHub's Issues API can also return pull requests,
    so pull requests are filtered out here.
    """

    endpoint = f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"

    items = get_paginated_data(
        endpoint,
        params={"state": "all"},
    )

    issues = [
        item
        for item in items
        if "pull_request" not in item
    ]

    return issues


def get_pull_requests():
    """
    Fetch repository pull requests.
    """

    endpoint = f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls"

    return get_paginated_data(
        endpoint,
        params={"state": "all"},
    )


def get_commits():
    """
    Fetch repository commits.
    """

    endpoint = f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits"

    return get_paginated_data(endpoint)


if __name__ == "__main__":

    print("Testing GitHub data connector...\n")

    repo = get_repository()

    print(f"Repository: {repo['full_name']}")

    issues = get_issues()
    pull_requests = get_pull_requests()
    commits = get_commits()

    print(f"Issues found: {len(issues)}")
    print(f"Pull requests found: {len(pull_requests)}")
    print(f"Commits found: {len(commits)}")

    print("\nGitHub ingestion test successful.")