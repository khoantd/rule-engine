#!/bin/bash

# Script to create GitHub repository and push code
# Usage: ./create_remote_repo.sh <repo-name> [github-token]

set -e

REPO_NAME="${1:-rule-engine}"
GITHUB_TOKEN="${2:-$GITHUB_TOKEN}"
GITHUB_USER=$(git config user.name | tr ' ' '-')

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GitHub token required"
    echo "Usage: $0 <repo-name> <github-token>"
    echo "Or set GITHUB_TOKEN environment variable"
    echo ""
    echo "To create a token:"
    echo "1. Go to https://github.com/settings/tokens"
    echo "2. Generate new token (classic) with 'repo' scope"
    echo "3. Use: $0 $REPO_NAME <your-token>"
    exit 1
fi

echo "Creating repository: $REPO_NAME"
echo "GitHub user: $GITHUB_USER"

# Create repository via GitHub API
RESPONSE=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/user/repos \
    -d "{\"name\":\"$REPO_NAME\",\"description\":\"Python Rule Engine - A flexible rule engine for evaluating business rules and workflows\",\"private\":false}")

# Extract clone_url from JSON response
if command -v jq &> /dev/null; then
    REPO_URL=$(echo "$RESPONSE" | jq -r '.clone_url // empty')
else
    REPO_URL=$(echo "$RESPONSE" | grep -o '"clone_url":"[^"]*"' | head -1 | cut -d'"' -f4)
fi

# Check if repository already exists (error response)
if echo "$RESPONSE" | grep -q '"message"'; then
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
    if echo "$ERROR_MSG" | grep -qi "already exists"; then
        echo "Repository already exists, using existing repository..."
        REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"
    else
        echo "Error creating repository: $ERROR_MSG"
        echo "Response: $RESPONSE"
        exit 1
    fi
elif [ -z "$REPO_URL" ]; then
    echo "Error: Could not extract repository URL from response"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "Repository created: $REPO_URL"

# Add remote and push
echo "Adding remote origin..."
git remote add origin "$REPO_URL" || git remote set-url origin "$REPO_URL"

echo "Pushing to remote..."
git branch -M main
git push -u origin main

echo "Done! Repository is available at:"
echo "https://github.com/$GITHUB_USER/$REPO_NAME"
