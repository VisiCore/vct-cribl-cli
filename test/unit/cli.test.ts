import { describe, it, expect } from "vitest";
import { buildProgram } from "../../src/cli.js";

describe("CLI program", () => {
  it("should have all expected command groups", () => {
    const program = buildProgram();
    const commandNames = program.commands.map((c) => c.name());

    const expected = [
      "config", "workers", "sources", "destinations", "metrics",
      "search", "datasets", "notebooks", "alerts",
      "pipelines", "routes", "packs", "lookups", "jobs",
      "users", "roles", "secrets", "version", "system",
      "dashboards", "edge",
      "event-breakers", "parsers", "global-vars", "schemas",
      "regex", "grok", "db-connections", "functions",
      "certificates", "credentials", "samples", "scripts",
      "licenses", "teams", "policies", "notification-targets",
      // Batch 1.3 - Search-scoped
      "dataset-providers", "macros", "dashboard-categories",
      "trust-policies", "usage-groups", "datatypes",
      // Batch 3 - Lake
      "lake-datasets", "storage-locations",
      // Batch 1.1 - Group-scoped
      "collectors", "conditions", "executors", "parquet-schemas",
      "protobuf-libs", "hmac-functions", "sds-rules", "sds-rulesets",
      "appscope", "preview", "logger", "profiler",
      // Batch 1.2 - Global
      "banners", "encryption-keys", "messages", "subscriptions",
      "kms", "feature-flags", "auth-settings", "git-settings",
      "ai-settings", "workspaces", "outposts",
    ];
    for (const name of expected) {
      expect(commandNames).toContain(name);
    }
    expect(commandNames).toHaveLength(expected.length);
  });

  it("search should have run, jobs, results, saved, and job detail subcommands", () => {
    const program = buildProgram();
    const search = program.commands.find((c) => c.name() === "search")!;
    const subNames = search.commands.map((c) => c.name());

    expect(subNames).toContain("run");
    expect(subNames).toContain("jobs");
    expect(subNames).toContain("results");
    expect(subNames).toContain("saved");
    expect(subNames).toContain("timeline");
    expect(subNames).toContain("field-summary");
    expect(subNames).toContain("job-logs");
    expect(subNames).toContain("job-metrics");
    expect(subNames).toContain("job-diag");
  });

  it("config should have set, show, use subcommands", () => {
    const program = buildProgram();
    const config = program.commands.find((c) => c.name() === "config")!;
    const subNames = config.commands.map((c) => c.name());

    expect(subNames).toContain("set");
    expect(subNames).toContain("show");
    expect(subNames).toContain("use");
  });

  it("pipelines should have CRUD subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "pipelines")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("create");
    expect(subNames).toContain("update");
    expect(subNames).toContain("delete");
  });

  it("jobs should have list, get, run, cancel, pause, resume, configs", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "jobs")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("run");
    expect(subNames).toContain("cancel");
    expect(subNames).toContain("pause");
    expect(subNames).toContain("resume");
    expect(subNames).toContain("configs");
  });

  it("system should have extended subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "system")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("info");
    expect(subNames).toContain("logs");
    expect(subNames).toContain("log");
    expect(subNames).toContain("diag");
    expect(subNames).toContain("diag-send");
    expect(subNames).toContain("restart");
    expect(subNames).toContain("reload");
    expect(subNames).toContain("upgrade");
  });

  it("edge should have extended subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "edge")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("containers");
    expect(subNames).toContain("processes");
    expect(subNames).toContain("events");
    expect(subNames).toContain("files");
    expect(subNames).toContain("ls");
    expect(subNames).toContain("kube-logs");
  });

  it("version should have info, status, diff, commit, push, sync, branches, deploy", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "version")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("info");
    expect(subNames).toContain("status");
    expect(subNames).toContain("diff");
    expect(subNames).toContain("commit");
    expect(subNames).toContain("push");
    expect(subNames).toContain("sync");
    expect(subNames).toContain("branches");
    expect(subNames).toContain("deploy");
  });

  it("sources should have full CRUD subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "sources")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("create");
    expect(subNames).toContain("update");
    expect(subNames).toContain("delete");
  });

  it("destinations should have full CRUD subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "destinations")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("create");
    expect(subNames).toContain("update");
    expect(subNames).toContain("delete");
  });

  it("routes should have full CRUD subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "routes")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("create");
    expect(subNames).toContain("update");
    expect(subNames).toContain("delete");
  });

  it("credentials should have full CRUD subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "credentials")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("create");
    expect(subNames).toContain("update");
    expect(subNames).toContain("delete");
  });

  it("lookups should have create subcommand", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "lookups")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("create");
    expect(subNames).toContain("delete");
  });

  it("dashboards should have create subcommand", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "dashboards")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("create");
    expect(subNames).toContain("delete");
  });

  it("pipelines should have clone subcommand", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "pipelines")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("clone");
  });

  it("workers should have get subcommand", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "workers")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
  });

  it("notebooks should have get and delete subcommands", () => {
    const program = buildProgram();
    const cmd = program.commands.find((c) => c.name() === "notebooks")!;
    const subNames = cmd.commands.map((c) => c.name());

    expect(subNames).toContain("list");
    expect(subNames).toContain("get");
    expect(subNames).toContain("add");
    expect(subNames).toContain("delete");
  });
});
