---
name: cribl-admin
description: "Administrative tasks: users, roles, credentials, and secrets management"
requires:
  skills: ["cribl-shared"]
---

# Cribl CLI — Administration

Manage users, roles, credentials, and secrets. These are typically global resources (no `-g` group flag needed for users/roles).

## Users

```bash
# List all users
cribl users list
cribl users list --table

# Get a specific user
cribl users get admin

# Create a user
cribl users create '{"id":"jdoe","username":"jdoe","first":"Jane","last":"Doe","email":"jane@example.com","roles":["user"]}'

# Update a user
cribl users update jdoe '{"email":"jane.doe@example.com"}'

# Delete a user
cribl users delete jdoe
```

## Roles

```bash
# List all RBAC roles
cribl roles list

# Get a role
cribl roles get admin

# Create a custom role
cribl roles create '{"id":"pipeline_editor","description":"Can edit pipelines","policy":"pipeline_edit_policy"}'

# Update a role
cribl roles update pipeline_editor '{"description":"Pipeline editor role (updated)"}'

# Delete a role
cribl roles delete pipeline_editor
```

## Credentials (Group-Scoped)

Credentials are stored per worker group and are used by sources/destinations to authenticate with external systems.

```bash
# List credentials
cribl credentials list -g default

# Get a credential
cribl credentials get my_aws_cred -g default

# Create a credential
cribl credentials create '{"id":"my_aws_cred","type":"aws","awsAccessKeyId":"AKIA...","awsSecretAccessKey":"..."}' -g default

# Update a credential
cribl credentials update my_aws_cred '{"awsAccessKeyId":"AKIA_NEW..."}' -g default

# Delete a credential
cribl credentials delete my_aws_cred -g default
```

## Secrets (Group-Scoped)

```bash
# List secrets
cribl secrets list -g default

# Get a secret
cribl secrets get my_api_key -g default

# Create a secret
cribl secrets create '{"id":"my_api_key","value":"sk-...","description":"External API key"}' -g default

# Update a secret
cribl secrets update my_api_key '{"value":"sk-new..."}' -g default

# Delete a secret
cribl secrets delete my_api_key -g default
```

## Teams

```bash
cribl teams list
cribl teams get my_team
cribl teams create '{"id":"data_eng","name":"Data Engineering","members":["jdoe","asmith"]}'
cribl teams update data_eng '{"members":["jdoe","asmith","bjones"]}'
cribl teams delete data_eng
```

## Policies

```bash
cribl policies list
cribl policies get my_policy
cribl policies create '{"id":"pipeline_edit_policy","rules":[{"effect":"allow","action":["pipelines:read","pipelines:write"]}]}'
cribl policies update my_policy '{"rules":[...]}'
cribl policies delete my_policy
```

## Notification Targets

```bash
cribl notification-targets list
cribl notification-targets get my_slack
cribl notification-targets create '{"id":"my_slack","type":"slack","url":"https://hooks.slack.com/..."}'
cribl notification-targets update my_slack '{"url":"https://hooks.slack.com/new-url"}'
cribl notification-targets delete my_slack
```

## Common Admin Workflows

### Audit user access

```bash
# List all users and their roles
cribl users list | jq '.[] | {id, email, roles}'
```

### Rotate credentials

```bash
# Update credential with new key
cribl credentials update my_aws_cred '{"awsAccessKeyId":"AKIA_NEW","awsSecretAccessKey":"new_secret"}' -g default

# Deploy the change
cribl version deploy "Rotate AWS credentials" -g default
```

### List all secrets across groups

```bash
for group in $(cribl workers list | jq -r '.[].id'); do
  echo "=== $group ==="
  cribl secrets list -g "$group" | jq '.[].id'
done
```
