from github_client import (
    get_issues,
    get_pull_requests,
    get_commits,
)


def normalize_issue(issue):
    """
    Convert a GitHub issue into the standard
    ProjectPulse document format.
    """

    return {
        "id": f"github_issue_{issue['id']}",
        "source": "github",
        "type": "issue",
        "title": issue["title"],
        "content": issue.get("body") or "",
        "author": issue["user"]["login"],
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "url": issue["html_url"],
        "metadata": {
            "number": issue["number"],
            "state": issue["state"],
            "labels": [
                label["name"]
                for label in issue.get("labels", [])
            ],
        },
    }


def normalize_pull_request(pr):
    """
    Convert a GitHub pull request into the standard
    ProjectPulse document format.
    """

    return {
        "id": f"github_pr_{pr['id']}",
        "source": "github",
        "type": "pull_request",
        "title": pr["title"],
        "content": pr.get("body") or "",
        "author": pr["user"]["login"],
        "created_at": pr["created_at"],
        "updated_at": pr["updated_at"],
        "url": pr["html_url"],
        "metadata": {
            "number": pr["number"],
            "state": pr["state"],
            "base_branch": pr["base"]["ref"],
            "head_branch": pr["head"]["ref"],
        },
    }


def normalize_commit(commit):
    """
    Convert a GitHub commit into the standard
    ProjectPulse document format.
    """

    commit_data = commit["commit"]

    author = commit.get("author")

    if author:
        author_name = author["login"]
    else:
        author_name = commit_data["author"]["name"]

    return {
        "id": f"github_commit_{commit['sha']}",
        "source": "github",
        "type": "commit",
        "title": commit_data["message"].split("\n")[0],
        "content": commit_data["message"],
        "author": author_name,
        "created_at": commit_data["author"]["date"],
        "updated_at": commit_data["committer"]["date"],
        "url": commit["html_url"],
        "metadata": {
            "sha": commit["sha"],
        },
    }


def collect_normalized_documents():
    """
    Fetch GitHub activity and convert everything
    into ProjectPulse's common document structure.
    """

    issues = get_issues()
    pull_requests = get_pull_requests()
    commits = get_commits()

    documents = []

    documents.extend(
        normalize_issue(issue)
        for issue in issues
    )

    documents.extend(
        normalize_pull_request(pr)
        for pr in pull_requests
    )

    documents.extend(
        normalize_commit(commit)
        for commit in commits
    )

    return documents


if __name__ == "__main__":
    documents = collect_normalized_documents()

    print(f"Normalized documents: {len(documents)}")

    for document in documents:
        print("\n" + "=" * 60)
        print(f"Type: {document['type']}")
        print(f"Title: {document['title']}")
        print(f"Author: {document['author']}")
        print(f"Created: {document['created_at']}")