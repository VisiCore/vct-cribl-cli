---
name: cribl-sources
description: "CRUD operations for Cribl data sources"
requires:
  skills: ["cribl-shared"]
---

# Cribl CLI — Source Management

Full CRUD for data sources (inputs). Sources are group-scoped resources.

## List Sources

```bash
cribl sources list -g default
cribl sources list -g default --table
cribl sources list -g default | jq '.[].id'
```

## Get a Source

```bash
cribl sources get <source-id> -g default
cribl sources get my_syslog_source -g default --table
```

## Create a Source

### Using flags (simple sources)

```bash
cribl sources create \
  --id my_syslog \
  --type syslog \
  --host 0.0.0.0 \
  --port 514 \
  -g default
```

### Using --json-config (full control)

```bash
cribl sources create \
  --id my_http_source \
  --type http \
  --json-config '{"id":"my_http_source","type":"http","port":10080,"disabled":false,"authType":"none"}' \
  -g default
```

### Common source types

| Type | Description |
|------|-------------|
| `syslog` | Syslog (UDP/TCP) |
| `http` | HTTP/HTTPS event receiver |
| `tcp` | Raw TCP |
| `splunk_tcp` | Splunk-to-Splunk (S2S) |
| `kafka` | Kafka consumer |
| `kinesis` | AWS Kinesis |
| `s3` | AWS S3 (pull) |
| `elastic` | Elasticsearch |

## Update a Source

```bash
# Pass full or partial JSON config
cribl sources update my_syslog '{"disabled":true}' -g default
```

## Delete a Source

```bash
cribl sources delete my_syslog -g default
```

## Common Workflows

### Inventory all sources across groups

```bash
for group in $(cribl workers list | jq -r '.[].id'); do
  echo "=== $group ==="
  cribl sources list -g "$group" | jq '.[].id'
done
```

### Find sources by type

```bash
cribl sources list -g default | jq '.[] | select(.type == "syslog") | {id, port, disabled}'
```

### Create source from a file

```bash
cribl sources create \
  --id from_file \
  --type http \
  --json-config "$(cat source-config.json)" \
  -g default
```
