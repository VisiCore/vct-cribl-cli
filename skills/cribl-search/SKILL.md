---
name: cribl-search
description: "Run searches and retrieve results from Cribl Search"
requires:
  skills: ["cribl-shared"]
---

# Cribl CLI — Search Workflows

Run queries against Cribl Search, poll for results, and analyze search job output.

## Run a Search (Fire and Forget)

```bash
# Returns the job object immediately (doesn't wait for results)
cribl search run "dataset='cribl_internal_logs' level=='error'"
```

The response includes a job `id` you can use to poll for results.

## Run a Search (Wait for Results)

```bash
# --wait polls until the job completes, then returns results
cribl search run "dataset='cribl_internal_logs' | top 10 source" --wait

# Custom time range
cribl search run "dataset='cribl_metrics'" --earliest -1h --latest now --wait

# Custom poll interval (default 2000ms)
cribl search run "dataset='cribl_internal_logs'" --wait --poll-interval 5000
```

## Search Job Lifecycle

### 1. Start the job

```bash
JOB_ID=$(cribl search run "dataset='cribl_internal_logs'" | jq -r '.id')
```

### 2. Check job status

```bash
# Listed among all search jobs
cribl search jobs
```

### 3. Get results when complete

```bash
cribl search results "$JOB_ID"
```

### 4. Get additional job data

```bash
# Timeline buckets (event counts over time)
cribl search timeline "$JOB_ID"

# Field summary (field names, types, coverage)
cribl search field-summary "$JOB_ID"

# Job logs (internal logs from the search execution)
cribl search job-logs "$JOB_ID"

# Job metrics (performance stats)
cribl search job-metrics "$JOB_ID"

# Job diagnostics
cribl search job-diag "$JOB_ID"
```

## Saved Searches

```bash
# List saved searches
cribl search saved

# List with table output
cribl search saved --table
```

## Common Search Patterns

### Search recent errors

```bash
cribl search run "dataset='cribl_internal_logs' level=='error' | head 100" --wait
```

### Get metrics for a specific source

```bash
cribl search run "dataset='cribl_metrics' input=='syslog_input' | stats avg(total) by host" \
  --earliest -4h --wait
```

### Search and pipe to jq

```bash
cribl search run "dataset='cribl_internal_logs' | top source" --wait | jq '.[] | {source, count}'
```

### Monitor search jobs

```bash
# List all running/completed search jobs
cribl search jobs --table
```
