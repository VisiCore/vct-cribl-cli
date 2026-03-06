---
name: cribl-deploy
description: "Version control and deployment workflows for Cribl"
requires:
  skills: ["cribl-shared"]
---

# Cribl CLI — Version Control & Deployment

Cribl has built-in version control for configuration changes. This skill covers the commit → push → deploy workflow.

## Check Current State

```bash
# What branch are we on?
cribl version current-branch -g default

# Any uncommitted changes?
cribl version status -g default

# See what changed
cribl version diff -g default

# Version info (commit history)
cribl version info -g default
```

## Commit and Push (Standard Workflow)

```bash
# Step 1: Commit pending changes
cribl version commit "Updated syslog pipeline filters" -g default

# Step 2: Push to deploy
cribl version push -g default
```

## One-Step Deploy

The `deploy` command combines commit + push:

```bash
cribl version deploy "Updated syslog pipeline filters" -g default
```

This is equivalent to running `commit` followed by `push`.

## Branch Management

```bash
# List all branches
cribl version branches -g default

# Check current branch
cribl version current-branch -g default

# Sync with remote
cribl version sync -g default
```

## CI/CD Integration

### GitHub Actions Example

```yaml
steps:
  - name: Deploy Cribl config
    env:
      CRIBL_BASE_URL: ${{ secrets.CRIBL_BASE_URL }}
      CRIBL_CLIENT_ID: ${{ secrets.CRIBL_CLIENT_ID }}
      CRIBL_CLIENT_SECRET: ${{ secrets.CRIBL_CLIENT_SECRET }}
    run: |
      # Make changes (e.g., update a pipeline)
      cribl pipelines update my_pipeline "$(cat pipeline-config.json)" -g default

      # Deploy
      cribl version deploy "CI: update pipeline config [build ${{ github.run_number }}]" -g default
```

### Shell Script Example

```bash
#!/bin/bash
set -e

GROUP="default"

# Check for uncommitted changes
status=$(cribl version status -g "$GROUP")
echo "Current status: $status"

# Deploy if there are changes
if echo "$status" | jq -e '.changed // false' > /dev/null 2>&1; then
  cribl version deploy "Automated deploy $(date +%Y-%m-%d)" -g "$GROUP"
  echo "Deploy complete"
else
  echo "No changes to deploy"
fi
```

## Common Patterns

### Deploy across multiple groups

```bash
for group in $(cribl workers list | jq -r '.[].id'); do
  echo "Deploying $group..."
  cribl version deploy "Bulk deploy: updated routing rules" -g "$group" || echo "  No changes in $group"
done
```

### Check deploy status after push

```bash
cribl version status -g default
cribl system health
```
