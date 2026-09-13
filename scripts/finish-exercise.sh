#!/usr/bin/env bash

set -e

# Move to repository root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "Have you updated this week's review and ticked off the exercise? (y/n)"
read -r answer

case "$answer" in
    y|Y|yes|YES)
        ;;
    *)
        echo "Cancelled. Update the weekly review first."
        exit 0
        ;;
esac

echo
echo "Updating progress..."
python scripts/update_progress.py

echo
echo "Adding files..."
git add .

if git diff --cached --quiet; then
    echo "No changes to commit."
    exit 0
fi

echo
echo "Staged changes:"
git status --short

echo
read -r -p "Enter commit message: " commit_message

if [ -z "$commit_message" ]; then
    echo "Commit message cannot be empty."
    exit 1
fi

echo
echo "Creating commit..."
git commit -m "$commit_message"

echo
echo "Pushing to origin..."
git push origin

echo
echo "Exercise recorded successfully."