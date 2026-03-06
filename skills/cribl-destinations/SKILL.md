---
name: cribl-destinations
description: "CRUD operations for Cribl data destinations"
requires:
  skills: ["cribl-shared"]
---

# Cribl CLI — Destination Management

Full CRUD for data destinations (outputs). Destinations are group-scoped resources.

## List Destinations

```bash
cribl destinations list -g default
cribl destinations list -g default --table
cribl destinations list -g default | jq '.[].id'
```

## Get a Destination

```bash
cribl destinations get <dest-id> -g default
cribl destinations get my_s3_output -g default --table
```

## Create a Destination

### Using flags (simple destinations)

```bash
cribl destinations create \
  --id my_s3_output \
  --type s3 \
  -g default
```

### Using --json-config (full control)

```bash
cribl destinations create \
  --id my_splunk_output \
  --type splunk \
  --json-config '{"id":"my_splunk_output","type":"splunk","host":"splunk.example.com","port":9997,"disabled":false}' \
  -g default
```

### Common destination types

| Type | Description |
|------|-------------|
| `s3` | AWS S3 |
| `splunk` | Splunk HEC or S2S |
| `syslog` | Syslog output |
| `elastic` | Elasticsearch |
| `kafka` | Kafka producer |
| `default` | Default output (passthrough) |
| `devnull` | /dev/null (drop events) |
| `azure_blob` | Azure Blob Storage |
| `google_cloud_storage` | GCS |

## Update a Destination

```bash
cribl destinations update my_s3_output '{"disabled":true}' -g default
```

## Delete a Destination

```bash
cribl destinations delete my_s3_output -g default
```

## Common Workflows

### Find destinations by type

```bash
cribl destinations list -g default | jq '.[] | select(.type == "s3") | {id, disabled}'
```

### List all disabled destinations

```bash
cribl destinations list -g default | jq '.[] | select(.disabled == true) | .id'
```

### Bulk disable destinations (scripting)

```bash
for dest_id in $(cribl destinations list -g default | jq -r '.[] | select(.type == "devnull") | .id'); do
  cribl destinations update "$dest_id" '{"disabled":true}' -g default
done
```
