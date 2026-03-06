import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import nock from "nock";
import axios from "axios";
import { listWorkerGroups } from "../../src/api/endpoints/workers.js";
import { getSources, listSources } from "../../src/api/endpoints/sources.js";
import { getDestinations, listDestinations } from "../../src/api/endpoints/destinations.js";
import { getMetrics } from "../../src/api/endpoints/metrics.js";
import { listDatasets } from "../../src/api/endpoints/datasets.js";
import { listAlerts } from "../../src/api/endpoints/alerts.js";
import { listNotebooks } from "../../src/api/endpoints/notebooks.js";
import { runSearch, listSearchJobs, getSearchResults, listSavedSearches } from "../../src/api/endpoints/search.js";

const BASE = "https://mock.cribl.cloud";

function mockClient() {
  return axios.create({ baseURL: BASE });
}

describe("API endpoints", () => {
  afterEach(() => {
    nock.cleanAll();
  });

  it("listWorkerGroups", async () => {
    nock(BASE)
      .get("/api/v1/master/groups")
      .reply(200, { items: [{ id: "default", workerCount: 3 }] });

    const data = await listWorkerGroups(mockClient());
    expect(data.items).toHaveLength(1);
    expect(data.items[0].id).toBe("default");
  });

  it("getSources", async () => {
    nock(BASE)
      .get("/api/v1/m/default/system/inputs")
      .reply(200, { items: [{ id: "syslog:in_syslog", type: "syslog" }] });

    const data = await getSources(mockClient(), "default");
    expect(data.items[0].type).toBe("syslog");
  });

  it("getDestinations", async () => {
    nock(BASE)
      .get("/api/v1/m/default/system/outputs")
      .reply(200, { items: [{ id: "s3:out_s3", type: "s3" }] });

    const data = await getDestinations(mockClient(), "default");
    expect(data.items[0].type).toBe("s3");
  });

  it("getMetrics", async () => {
    nock(BASE)
      .get("/api/v1/system/metrics")
      .reply(200, { cpuUsage: 42 });

    const data = await getMetrics(mockClient());
    expect(data).toHaveProperty("cpuUsage", 42);
  });

  it("listDatasets", async () => {
    nock(BASE)
      .get("/api/v1/m/default_search/search/datasets")
      .reply(200, { items: [{ id: "ds1" }] });

    const data = await listDatasets(mockClient());
    expect(data.items[0].id).toBe("ds1");
  });

  it("listAlerts", async () => {
    nock(BASE)
      .get("/api/v1/notifications")
      .reply(200, { items: [{ id: "alert1" }] });

    const data = await listAlerts(mockClient());
    expect(data.items[0].id).toBe("alert1");
  });

  it("listNotebooks", async () => {
    nock(BASE)
      .get("/api/v1/m/default_search/search/notebooks")
      .reply(200, { items: [{ id: "nb1" }] });

    const data = await listNotebooks(mockClient());
    expect(data.items[0].id).toBe("nb1");
  });

  it("runSearch", async () => {
    nock(BASE)
      .post("/api/v1/m/default_search/search/jobs")
      .reply(200, { id: "job123", status: "running" });

    const job = await runSearch(mockClient(), { query: "test" });
    expect(job.id).toBe("job123");
  });

  it("listSearchJobs", async () => {
    nock(BASE)
      .get("/api/v1/m/default_search/search/jobs")
      .reply(200, { items: [{ id: "job1" }, { id: "job2" }] });

    const data = await listSearchJobs(mockClient());
    expect(data.items).toHaveLength(2);
  });

  it("getSearchResults", async () => {
    nock(BASE)
      .get("/api/v1/m/default_search/search/jobs/job123/results")
      .reply(200, [{ _raw: "test event" }]);

    const results = await getSearchResults(mockClient(), "job123");
    expect(results).toHaveLength(1);
  });

  it("listSavedSearches", async () => {
    nock(BASE)
      .get("/api/v1/m/default_search/search/saved")
      .reply(200, { items: [{ id: "saved1" }] });

    const data = await listSavedSearches(mockClient());
    expect(data.items[0].id).toBe("saved1");
  });
});
