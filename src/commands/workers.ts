import { Command } from "commander";
import { getClient } from "../api/client.js";
import { listWorkerGroups, getWorkerGroup, deployGroup } from "../api/endpoints/workers.js";
import { resolveGroup } from "../utils/group-resolver.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

export function registerWorkersCommand(program: Command): void {
  const workers = program.command("workers").description("Manage worker groups");

  workers
    .command("list")
    .description("List worker groups")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await listWorkerGroups(getClient());
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  workers
    .command("get")
    .description("Get a worker group by ID")
    .argument("<id>", "Worker group ID")
    .option("--table", "Table output")
    .action(async (id: string, opts) => {
      try {
        const data = await getWorkerGroup(getClient(), id);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  workers
    .command("deploy")
    .description("Deploy committed config to worker group")
    .option("-g, --group <name>", "Worker group name")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await deployGroup(client, group);
        console.log(formatOutput(data ?? { message: `Config deployed to '${group}'.` }));
      } catch (err) {
        handleError(err);
      }
    });
}
