import os

import requests
from dotenv import load_dotenv


load_dotenv()


class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = os.getenv("GITHUB_OWNER")
        self.repo = os.getenv("GITHUB_REPO")

        if not self.token:
            raise ValueError("GITHUB_TOKEN is missing in .env")

        if not self.owner:
            raise ValueError("GITHUB_OWNER is missing in .env")

        if not self.repo:
            raise ValueError("GITHUB_REPO is missing in .env")

        self.base_url = "https://api.github.com"

        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2026-03-10",
        }

    def get_repository(self):
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10,
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code

            if status_code == 401:
                raise RuntimeError(
                    "Authentication failed. Check your GitHub token."
                ) from None

            if status_code == 403:
                raise RuntimeError(
                    "GitHub denied access. Check token permissions."
                ) from None

            if status_code == 404:
                raise RuntimeError(
                    "Repository not found. Check GITHUB_OWNER and GITHUB_REPO."
                ) from None

            raise RuntimeError(
                f"GitHub API returned HTTP {status_code}."
            ) from None

        except requests.exceptions.Timeout:
            raise RuntimeError(
                "GitHub API request timed out."
            ) from None

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Could not connect to GitHub API."
            ) from None


if __name__ == "__main__":
    client = GitHubClient()
    repository = client.get_repository()

    print("\nGitHub connection successful!")
    print("-" * 40)
    print(f"Repository : {repository['full_name']}")
    print(f"Private    : {repository['private']}")
    print(f"Branch     : {repository['default_branch']}")
    print(f"Language   : {repository['language']}")
    print(f"Stars      : {repository['stargazers_count']}")
    print(f"Open issues: {repository['open_issues_count']}")
    print(f"URL        : {repository['html_url']}")