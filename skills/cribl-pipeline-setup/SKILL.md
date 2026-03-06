---
name: cribl-pipeline-setup
description: "Set up an end-to-end data pipeline in Cribl"
requires:
  skills: ["cribl-shared", "cribl-sources", "cribl-destinations"]
---

# Cribl CLI — End-to-End Pipeline Setup

This skill walks through creating a complete data flow: source → pipeline → route → destination.

## Overview

In Cribl, data flows through:
1. **Source** — receives data (e.g., syslog, HTTP, S2S)
2. **Pipeline** — processes/transforms data (functions like regex extract, eval, drop)
3. **Route** — connects a source filter to a pipeline and output destination
4. **Destination** — sends data to its final target (e.g., S3, Splunk, Elasticsearch)

## Step 1: Create a Source

```bash
cribl sources create \
  --id syslog_input \
  --type syslog \
  --port 514 \
  -g default
```

## Step 2: Create a Destination

```bash
cribl destinations create \
  --id s3_archive \
  --type s3 \
  --json-config '{"id":"s3_archive","type":"s3","bucket":"my-log-bucket","region":"us-east-1","disabled":false}' \
  -g default
```

## Step 3: Create a Pipeline

```bash
cribl pipelines create '{
  "id": "syslog_processing",
  "conf": {
    "functions": [
      {
        "id": "serde",
        "filter": "true",
        "conf": { "mode": "extract", "type": "json" }
      },
      {
        "id": "eval",
        "filter": "true",
        "conf": { "add": [{"name": "index", "value": "\"main\""}] }
      }
    ]
  }
}' -g default
```

## Step 4: Create a Route

Routes connect sources to pipelines and destinations:

```bash
cribl routes create '{
  "id": "syslog_to_s3",
  "name": "Syslog to S3",
  "filter": "sourcetype==\"syslog\"",
  "pipeline": "syslog_processing",
  "output": "s3_archive",
  "enabled": true
}' -g default
```

## Step 5: Deploy Changes

```bash
# Option A: Commit + push separately
cribl version commit "Add syslog-to-S3 pipeline" -g default
cribl version push -g default

# Option B: One-step deploy
cribl version deploy "Add syslog-to-S3 pipeline" -g default
```

## Verify the Setup

```bash
# Check all pieces exist
cribl sources get syslog_input -g default
cribl pipelines get syslog_processing -g default
cribl routes get syslog_to_s3 -g default
cribl destinations get s3_archive -g default

# Check deployment status
cribl version status -g default
```

## Clone a Pipeline Between Groups

```bash
cribl pipelines clone my_pipeline --from prod_group --to staging_group
cribl pipelines clone my_pipeline --from prod_group --to staging_group --new-id my_pipeline_v2
```

## Common Patterns

### List routes with their pipeline and output

```bash
cribl routes list -g default | jq '.[] | {id, filter, pipeline, output, enabled}'
```

### Disable a route without deleting

```bash
cribl routes update syslog_to_s3 '{"enabled":false}' -g default
```

### Full pipeline inventory

```bash
echo "Sources:"  && cribl sources list -g default | jq '.[].id'
echo "Pipelines:" && cribl pipelines list -g default | jq '.[].id'
echo "Routes:"    && cribl routes list -g default | jq '.[].id'
echo "Destinations:" && cribl destinations list -g default | jq '.[].id'
```
