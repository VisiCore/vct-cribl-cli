import { describe, it, expect, afterEach } from "vitest";
import nock from "nock";
import axios from "axios";
import { listSources, getSource, createSource, updateSource, deleteSource } from "../../src/api/endpoints/sources.js";
import { listDestinations, getDestination, createDestination, updateDestination, deleteDestination } from "../../src/api/endpoints/destinations.js";
import { listRoutes, getRoute, createRoute, updateRoute, deleteRoute } from "../../src/api/endpoints/routes.js";
import { createLookup } from "../../src/api/endpoints/lookups.js";
import { createDashboard } from "../../src/api/endpoints/dashboards.js";
import { createCredential, updateCredential, deleteCredential } from "../../src/api/endpoints/credentials.js";
import { getWorkerGroup } from "../../src/api/endpoints/workers.js";
import { getNotebook, deleteNotebook } from "../../src/api/endpoints/notebooks.js";

const BASE = "https://mock.cribl.cloud";
const client = () => axios.create({ baseURL: BASE });

describe("CRUD API endpoints", () => {
  afterEach(() => nock.cleanAll());

  // Sources CRUD
  describe("sources", () => {
    it("listSources", async () => {
      nock(BASE).get("/api/v1/m/default/system/inputs").reply(200, { items: [{ id: "s1", type: "syslog" }] });
      const data = await listSources(client(), "default");
      expect(data.items[0].id).toBe("s1");
    });

    it("getSource", async () => {
      nock(BASE).get("/api/v1/m/default/system/inputs/s1").reply(200, { items: [{ id: "s1", type: "syslog" }] });
      const data = await getSource(client(), "default", "s1");
      expect(data.id).toBe("s1");
    });

    it("createSource", async () => {
      nock(BASE).post("/api/v1/m/default/system/inputs").reply(200, { id: "s2", type: "http" });
      const data = await createSource(client(), "default", { id: "s2", type: "http" });
      expect(data.id).toBe("s2");
    });

    it("updateSource", async () => {
      nock(BASE).patch("/api/v1/m/default/system/inputs/s1").reply(200, { id: "s1", type: "syslog", port: 5514 });
      const data = await updateSource(client(), "default", "s1", { port: 5514 });
      expect(data.port).toBe(5514);
    });

    it("deleteSource", async () => {
      nock(BASE).delete("/api/v1/m/default/system/inputs/s1").reply(200);
      await expect(deleteSource(client(), "default", "s1")).resolves.toBeUndefined();
    });
  });

  // Destinations CRUD
  describe("destinations", () => {
    it("listDestinations", async () => {
      nock(BASE).get("/api/v1/m/default/system/outputs").reply(200, { items: [{ id: "d1", type: "s3" }] });
      const data = await listDestinations(client(), "default");
      expect(data.items[0].id).toBe("d1");
    });

    it("getDestination", async () => {
      nock(BASE).get("/api/v1/m/default/system/outputs/d1").reply(200, { items: [{ id: "d1", type: "s3" }] });
      const data = await getDestination(client(), "default", "d1");
      expect(data.id).toBe("d1");
    });

    it("createDestination", async () => {
      nock(BASE).post("/api/v1/m/default/system/outputs").reply(200, { id: "d2", type: "splunk" });
      const data = await createDestination(client(), "default", { id: "d2", type: "splunk" });
      expect(data.id).toBe("d2");
    });

    it("updateDestination", async () => {
      nock(BASE).patch("/api/v1/m/default/system/outputs/d1").reply(200, { id: "d1", type: "s3", bucket: "new" });
      const data = await updateDestination(client(), "default", "d1", { bucket: "new" });
      expect(data.bucket).toBe("new");
    });

    it("deleteDestination", async () => {
      nock(BASE).delete("/api/v1/m/default/system/outputs/d1").reply(200);
      await expect(deleteDestination(client(), "default", "d1")).resolves.toBeUndefined();
    });
  });

  // Routes CRUD
  describe("routes", () => {
    it("createRoute", async () => {
      nock(BASE).post("/api/v1/m/default/routes").reply(200, { id: "r1", name: "test" });
      const data = await createRoute(client(), "default", { id: "r1", name: "test" });
      expect(data.id).toBe("r1");
    });

    it("updateRoute", async () => {
      nock(BASE).patch("/api/v1/m/default/routes/r1").reply(200, { id: "r1", name: "updated" });
      const data = await updateRoute(client(), "default", "r1", { name: "updated" });
      expect(data.name).toBe("updated");
    });

    it("deleteRoute", async () => {
      nock(BASE).delete("/api/v1/m/default/routes/r1").reply(200);
      await expect(deleteRoute(client(), "default", "r1")).resolves.toBeUndefined();
    });
  });

  // Lookups create
  describe("lookups", () => {
    it("createLookup", async () => {
      nock(BASE).post("/api/v1/m/default/system/lookups").reply(200, { id: "geo" });
      const data = await createLookup(client(), "default", { id: "geo" });
      expect(data.id).toBe("geo");
    });
  });

  // Dashboards create
  describe("dashboards", () => {
    it("createDashboard", async () => {
      nock(BASE).post("/api/v1/m/default_search/search/dashboards").reply(200, { id: "dash1" });
      const data = await createDashboard(client(), { id: "dash1" });
      expect(data.id).toBe("dash1");
    });
  });

  // Credentials CRUD
  describe("credentials", () => {
    it("createCredential", async () => {
      nock(BASE).post("/api/v1/m/default/system/credentials").reply(200, { id: "cred1" });
      const data = await createCredential(client(), "default", { id: "cred1" });
      expect(data.id).toBe("cred1");
    });

    it("updateCredential", async () => {
      nock(BASE).patch("/api/v1/m/default/system/credentials/cred1").reply(200, { id: "cred1", description: "updated" });
      const data = await updateCredential(client(), "default", "cred1", { description: "updated" });
      expect(data.description).toBe("updated");
    });

    it("deleteCredential", async () => {
      nock(BASE).delete("/api/v1/m/default/system/credentials/cred1").reply(200);
      await expect(deleteCredential(client(), "default", "cred1")).resolves.toBeUndefined();
    });
  });

  // Workers get
  describe("workers", () => {
    it("getWorkerGroup", async () => {
      nock(BASE).get("/api/v1/master/groups/default").reply(200, { items: [{ id: "default", workerCount: 3 }] });
      const data = await getWorkerGroup(client(), "default");
      expect(data.id).toBe("default");
    });
  });

  // Notebooks get/delete
  describe("notebooks", () => {
    it("getNotebook", async () => {
      nock(BASE).get("/api/v1/m/default_search/search/notebooks/nb1").reply(200, { items: [{ id: "nb1" }] });
      const data = await getNotebook(client(), "nb1");
      expect(data.id).toBe("nb1");
    });

    it("deleteNotebook", async () => {
      nock(BASE).delete("/api/v1/m/default_search/search/notebooks/nb1").reply(200);
      await expect(deleteNotebook(client(), "nb1")).resolves.toBeUndefined();
    });
  });
});
