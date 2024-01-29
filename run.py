import requests
import subprocess
import os
import shutil


# Constants
GITHUB_API = "https://api.github.com"
USERNAME = ""
TOKEN = ""
LOCAL_REPO_PATH = ""


headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_forked_repos(username):
    username = USERNAME
    """Get a list of forked repositories for a given user with pagination handling"""
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/users/{username}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        current_repos = response.json()
        if not current_repos:
            break
        repos.extend([repo for repo in current_repos if repo['fork']])
        page += 1
    return repos

def get_default_branch(repo):
    """Get the default branch of a repository"""
    url = repo['url']
    response = requests.get(url, headers=headers)
    return response.json().get('default_branch', 'master')

def setup_repository(repo, local_repo_path):
    """Clone the repository if not already cloned, or pull the latest changes"""
    repo_dir = os.path.join(local_repo_path, repo['name'])
    if not os.path.exists(repo_dir):
        print(f"Cloning {repo['full_name']}")
        subprocess.run(["git", "clone", repo['clone_url']], cwd=local_repo_path)
    else:
        print(f"Updating {repo['full_name']}")
        subprocess.run(["git", "pull"], cwd=repo_dir)

def get_upstream_repo_url(repo):
    """Get the clone URL of the upstream repository for a given fork"""
    if 'parent' in repo:
        return repo['parent']['clone_url']
    else:
        # Fallback: Make an additional API request if 'parent' is not in the repo details
        url = repo['url']
        response = requests.get(url, headers=headers)
        parent_repo = response.json().get('parent', None)
        return parent_repo['clone_url'] if parent_repo else None

def fetch_upstream_changes(repo, local_repo_path):
    """Fetch changes from the upstream repository"""
    repo_dir = os.path.join(local_repo_path, repo['name'])
    upstream_url = get_upstream_repo_url(repo)
    if not upstream_url:
        print(f"No upstream repository found for {repo['full_name']}")
        return
    fork_default_branch = get_default_branch(repo)

    setup_repository(repo, local_repo_path)

    os.chdir(repo_dir)

    subprocess.run(["git", "remote", "add", "upstream", upstream_url], check=False)
    subprocess.run(["git", "fetch", "upstream"], check=True)
    subprocess.run(["git", "checkout", fork_default_branch], check=True)
    subprocess.run(["git", "merge", f"upstream/{fork_default_branch}"], check=True)
    subprocess.run(["git", "push", "origin", fork_default_branch], check=True)

    os.chdir("..")

def update_forks(forked_repos, local_repo_path):
    """Update forked repositories and remove local copies"""
    for repo in forked_repos:
        repo_dir = os.path.join(local_repo_path, repo['name'])
        try:
            fetch_upstream_changes(repo, local_repo_path)
            print(f"Successfully updated {repo['full_name']}")
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
        except Exception as e:
            print(f"Failed to update {repo['full_name']}: {e}")
        finally:
            remove_local_repo(repo_dir)

def remove_local_repo(repo_dir):
    """Remove the local repository directory"""
    try:
        shutil.rmtree(repo_dir)
        print(f"Removed local repository {repo_dir}")
    except OSError as e:
        print(f"Error: {e.filename} - {e.strerror}")


def main():
    forked_repos = get_forked_repos(USERNAME)
    update_forks(forked_repos, LOCAL_REPO_PATH)

if __name__ == "__main__":
    main()
