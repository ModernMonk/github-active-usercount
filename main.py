import requests
import os
from datetime import datetime, timedelta

# GitHub auth headers
headers = {
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
    ...
}

# 60 days ago in ISO 8601 format
since_date = (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z"

# Replace with your list of orgs
orgs = [
    "abcd-xyz", "pqrs-abc"
]

all_contributors = set()

def get_paginated_results(url):
    results = []
    page = 1
    while True:
        response = requests.get(f"{url}&per_page=100&page={page}", headers=headers)
        if response.status_code != 200:
            break
        page_data = response.json()
        if not page_data:
            break
        results.extend(page_data)
        page += 1
    return results

for org in orgs:
    print(f"\n Fetching repos for org: {org}")
    repo_response = requests.get(f"https://api.github.com/orgs/{org}/repos?per_page=100", headers=headers)
    if repo_response.status_code != 200:
        print(f" Failed to fetch repos for {org}: {repo_response.status_code} - {repo_response.text}")
        continue

    repos = repo_response.json()
    for repo in repos:
        repo_name = repo.get("name")
        if not repo_name:
            continue
        print(f" Processing repo: {repo_name}")

        # --- Get commits from last 60 days ---
        commits_url = f"https://api.github.com/repos/{org}/{repo_name}/commits?since={since_date}"
        commits = get_paginated_results(commits_url)
        for commit in commits:
            if commit.get("author") and commit["author"].get("login"):
                all_contributors.add(commit["author"]["login"])

        # --- Get PRs and filter by created/merged date ---
        pr_page = 1
        while True:
            prs_url = f"https://api.github.com/repos/{org}/{repo_name}/pulls?state=all&per_page=100&page={pr_page}"
            prs_response = requests.get(prs_url, headers=headers)
            if prs_response.status_code != 200:
                break

            prs = prs_response.json()
            if not prs:
                break

            for pr in prs:
                created_at = pr.get("created_at", "")
                merged_at = pr.get("merged_at", "")
                user_login = pr.get("user", {}).get("login")

                if not user_login:
                    continue

                # Include PRs created or merged within the last 60 days
                if (created_at >= since_date) or (merged_at and merged_at >= since_date):
                    all_contributors.add(user_login)

                    # Get reviews
                    reviews_url = f"https://api.github.com/repos/{org}/{repo_name}/pulls/{pr['number']}/reviews"
                    reviews_response = requests.get(reviews_url, headers=headers)
                    if reviews_response.status_code == 200:
                        for review in reviews_response.json():
                            reviewer = review.get("user", {}).get("login")
                            if reviewer:
                                all_contributors.add(reviewer)

            pr_page += 1

# --- Final Output ---
print("\n Unique active contributors in last 60 days:")
for user in sorted(all_contributors):
    print(user)
