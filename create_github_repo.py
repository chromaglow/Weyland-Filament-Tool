"""
Helper script to create GitHub repository via API
"""

import requests
import json
import getpass
import subprocess
import sys


def create_github_repo(token: str, repo_name: str, description: str, is_private: bool = False):
    """
    Create a GitHub repository using the GitHub API

    Args:
        token: GitHub personal access token
        repo_name: Name of the repository
        description: Repository description
        is_private: Whether the repo should be private
    """
    url = "https://api.github.com/user/repos"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    data = {
        "name": repo_name,
        "description": description,
        "private": is_private,
        "auto_init": False  # Don't create README - we already have one
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        repo_data = response.json()
        print(f"✅ Repository created successfully!")
        print(f"🔗 URL: {repo_data['html_url']}")
        return True
    elif response.status_code == 422:
        print(f"⚠️  Repository already exists!")
        return True
    else:
        print(f"❌ Failed to create repository: {response.status_code}")
        print(f"   {response.json().get('message', 'Unknown error')}")
        return False


def push_to_github():
    """Push the local repository to GitHub"""
    try:
        print("\n📤 Pushing to GitHub...")
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Successfully pushed to GitHub!")
            print("\n🎉 Your repository is now live!")
            print("🔗 https://github.com/chromaglow/bambu-filament-tool")
            return True
        else:
            print(f"❌ Push failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error during push: {e}")
        return False


def main():
    print("=" * 70)
    print("  GitHub Repository Creator")
    print("  Bambu Filament Profile Generator")
    print("=" * 70)
    print()

    print("This script will create a GitHub repository and push your code.")
    print()
    print("You'll need a GitHub Personal Access Token with 'repo' scope.")
    print("Create one at: https://github.com/settings/tokens/new")
    print()

    # Get token
    token = getpass.getpass("Enter your GitHub token (input hidden): ")

    if not token:
        print("❌ No token provided. Exiting.")
        sys.exit(1)

    # Repository details
    repo_name = "bambu-filament-tool"
    description = "Research and generate Bambu Studio filament profiles with an easy-to-use GUI"

    print(f"\n📦 Creating repository: {repo_name}")
    print(f"📝 Description: {description}")
    print()

    # Create repo
    if create_github_repo(token, repo_name, description, is_private=False):
        # Push to GitHub
        if push_to_github():
            print()
            print("=" * 70)
            print("🎊 SUCCESS! Your repository is live on GitHub!")
            print("=" * 70)
            print()
            print("Next steps:")
            print("1. Visit: https://github.com/chromaglow/bambu-filament-tool")
            print("2. Add topics: 3d-printing, bambu-lab, filament-profiles")
            print("3. Share with the community!")
            print()
        else:
            print("\n⚠️  Repository created but push failed.")
            print("Try manually: git push -u origin main")
    else:
        print("\n❌ Failed to create repository.")
        print("\nManual steps:")
        print("1. Go to https://github.com/new")
        print("2. Create repo named 'bambu-filament-tool'")
        print("3. Don't initialize with README")
        print("4. Run: git push -u origin main")


if __name__ == "__main__":
    main()
