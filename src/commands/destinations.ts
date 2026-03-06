import { Command } from "commander";
import { getClient } from "../api/client.js";
import { listDestinations, getDestination, createDestination, updateDestination, deleteDestination } from "../api/endpoints/destinations.js";
import { resolveGroup } from "../utils/group-resolver.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

export function registerDestinationsCommand(program: Command): void {
  const cmd = program.command("destinations").description("Manage destinations");

  cmd
    .command("list")
    .description("List destination configurations")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await listDestinations(client, group);
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("get")
    .description("Get a destination by ID")
    .argument("<id>", "Destination ID")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (id: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await getDestination(client, group, id);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("create")
    .description("Create a new destination")
    .requiredOption("-t, --type <type>", "Destination type (e.g. s3, splunk, syslog)")
    .requiredOption("--id <id>", "Destination ID")
    .option("-g, --group <name>", "Worker group name")
    .option("--disabled", "Create destination in disabled state")
    .option("--json-config <json>", "Full JSON config (overrides other options)")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);

        let destConfig: Record<string, unknown>;
        if (opts.jsonConfig) {
          destConfig = JSON.parse(opts.jsonConfig);
        } else {
          destConfig = {
            id: opts.id,
            type: opts.type,
            disabled: opts.disabled ?? false,
          };
        }

        const result = await createDestination(client, group, destConfig);
        console.log(formatOutput(result, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("update")
    .description("Update a destination")
    .argument("<id>", "Destination ID")
    .argument("<json>", "Destination JSON config")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, json: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await updateDestination(client, group, id, JSON.parse(json));
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("delete")
    .description("Delete a destination")
    .argument("<id>", "Destination ID")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        await deleteDestination(client, group, id);
        console.log(formatOutput({ message: `Destination '${id}' deleted.` }));
      } catch (err) {
        handleError(err);
      }
    });
}
