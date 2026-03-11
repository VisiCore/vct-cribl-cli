# Configuration

The CLI supports three configuration methods, applied in priority order:

1. **CLI flags** (highest priority)
2. **Environment variables**
3. **Profile file** (`~/.criblrc`)

## Profiles

Profiles are stored in `~/.criblrc` (JSON, mode `0600`). Each profile contains connection and auth settings.

### Create a profile

```bash
# Cribl Cloud (OAuth2)
cribl config set -p cloud \
  --base-url https://your-org.cribl.cloud \
  --auth-type cloud \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# Cribl Local (username/password)
cribl config set -p local \
  --base-url http://localhost:9000 \
  --auth-type local \
  --username admin \
  --password admin
```

### Switch profiles

```bash
cribl config use cloud
```

### View a profile

```bash
cribl config show               # shows active profile
cribl config show -p local      # shows specific profile
```

Secrets are redacted in output (`clientSecret: "****"`).

### File format

```json
{
  "profiles": {
    "cloud": {
      "baseUrl": "https://your-org.cribl.cloud",
      "authType": "cloud",
      "clientId": "...",
      "clientSecret": "..."
    },
    "local": {
      "baseUrl": "http://localhost:9000",
      "authType": "local",
      "username": "admin",
      "password": "admin"
    }
  },
  "activeProfile": "cloud"
}
```

## Environment variables

| Variable | Description |
|---|---|
| `CRIBL_PROFILE` | Profile name to use (overrides active profile) |
| `CRIBL_BASE_URL` | Cribl instance URL |
| `CRIBL_CLIENT_ID` | OAuth2 client ID |
| `CRIBL_CLIENT_SECRET` | OAuth2 client secret |
| `CRIBL_USERNAME` | Local auth username |
| `CRIBL_PASSWORD` | Local auth password |

Environment variables override profile values but are overridden by CLI flags.

## CLI flag overrides

```bash
cribl --base-url https://other-org.cribl.cloud \
      --client-id ... \
      --client-secret ... \
      workers list
```

## Authentication

### Cloud auth (OAuth2)

Uses `client_credentials` grant against `https://login.cribl.cloud/oauth/token`.

- Audience is always `https://api.cribl.cloud` (not the org URL)
- Tokens are cached in memory and refreshed 60 seconds before expiry
- Default token lifetime is 3600 seconds

### Local auth

Posts `username` and `password` to `{base_url}/api/v1/auth/login`. Same caching behavior as cloud auth.

### Auth type auto-detection

If `auth_type` is not explicitly set:

- `local` when `username` and `password` are provided (and `client_id`/`client_secret` are not)
- `cloud` when `client_id` and `client_secret` are provided

## Global flags

Every command supports these root-level options:

| Flag | Description |
|---|---|
| `-p, --profile` | Profile name |
| `--base-url` | Base URL override |
| `--client-id` | Client ID override |
| `--client-secret` | Client secret override |
| `--verbose` | Log HTTP requests to stderr |
| `--dry-run` | Preview mode — logs request details without sending |
| `-h, --help` | Show help |

### Dry-run mode

With `--dry-run`, the CLI logs every API call to stderr as JSON and exits `0` without making any changes:

```bash
cribl --dry-run sources list -g default
# stderr: {"dry_run": true, "method": "GET", "url": "https://...", "headers": {...}}
```

### Verbose mode

With `--verbose`, the CLI logs `>> METHOD URL` to stderr for each request while still executing normally.
