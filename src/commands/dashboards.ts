import { Command } from "commander";
import { getClient } from "../api/client.js";
import { listDashboards, getDashboard, createDashboard, deleteDashboard } from "../api/endpoints/dashboards.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

export function registerDashboardsCommand(program: Command): void {
  const cmd = program.command("dashboards").description("Search dashboards");

  cmd
    .command("list")
    .description("List dashboards")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await listDashboards(getClient(), opts.group);
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("get")
    .description("Get a dashboard by ID")
    .argument("<id>", "Dashboard ID")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (id: string, opts) => {
      try {
        const data = await getDashboard(getClient(), id, opts.group);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("create")
    .description("Create a dashboard from JSON")
    .argument("<json>", "Dashboard JSON config")
    .option("-g, --group <name>", "Worker group name")
    .action(async (json: string, opts) => {
      try {
        const data = await createDashboard(getClient(), JSON.parse(json), opts.group);
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("delete")
    .description("Delete a dashboard")
    .argument("<id>", "Dashboard ID")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, opts) => {
      try {
        await deleteDashboard(getClient(), id, opts.group);
        console.log(formatOutput({ message: `Dashboard '${id}' deleted.` }));
      } catch (err) {
        handleError(err);
      }
    });
}
