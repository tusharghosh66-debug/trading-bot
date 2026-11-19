"""
Automated Cloud Deployment Script
Commits local code changes and pushes to GitHub main branch.
Render auto-detects the commit and deploys in the cloud.
"""

import subprocess
import sys
import os

GIT_EXE = r"c:\Users\Tushar\mingit\cmd\git.exe"
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

def deploy_to_cloud(commit_message="Auto-update trading bot code"):
    print(f"Staging changes in {WORKSPACE_DIR}...")
    subprocess.run([GIT_EXE, "add", "-A"], cwd=WORKSPACE_DIR, check=True)
    
    # Check if there are changes to commit
    status = subprocess.run([GIT_EXE, "status", "--porcelain"], cwd=WORKSPACE_DIR, capture_output=True, text=True)
    if not status.stdout.strip():
        print("No new changes to commit. Everything is up to date!")
        return True
        
    print(f"Committing: {commit_message}")
    subprocess.run([GIT_EXE, "commit", "-m", commit_message], cwd=WORKSPACE_DIR, check=True)
    
    print("Pushing to GitHub origin main...")
    subprocess.run([GIT_EXE, "push", "origin", "main"], cwd=WORKSPACE_DIR, check=True)
    print("Successfully pushed to GitHub! Render is now auto-deploying in the cloud.")
    return True

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Auto-update trading bot"
    deploy_to_cloud(msg)
