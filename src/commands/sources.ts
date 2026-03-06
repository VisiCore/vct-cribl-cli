import { Command } from "commander";
import { getClient } from "../api/client.js";
import { listSources, getSource, createSource, updateSource, deleteSource } from "../api/endpoints/sources.js";
import { resolveGroup } from "../utils/group-resolver.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

export function registerSourcesCommand(program: Command): void {
  const cmd = program.command("sources").description("Manage sources");

  cmd
    .command("list")
    .description("List source configurations")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await listSources(client, group);
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("get")
    .description("Get a source by ID")
    .argument("<id>", "Source ID")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (id: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await getSource(client, group, id);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("create")
    .description("Create a new source")
    .requiredOption("-t, --type <type>", "Source type (e.g. syslog, http, tcp)")
    .requiredOption("--id <id>", "Source ID")
    .option("-g, --group <name>", "Worker group name")
    .option("--host <host>", "Listen host", "0.0.0.0")
    .option("--port <port>", "Listen port")
    .option("--disabled", "Create source in disabled state")
    .option("--json-config <json>", "Full JSON config (overrides other options)")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);

        let sourceConfig: Record<string, unknown>;
        if (opts.jsonConfig) {
          sourceConfig = JSON.parse(opts.jsonConfig);
        } else {
          sourceConfig = {
            id: opts.id,
            type: opts.type,
            disabled: opts.disabled ?? false,
          };
          if (opts.host) sourceConfig.host = opts.host;
          if (opts.port) sourceConfig.port = parseInt(opts.port, 10);
        }

        const result = await createSource(client, group, sourceConfig);
        console.log(formatOutput(result, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("update")
    .description("Update a source")
    .argument("<id>", "Source ID")
    .argument("<json>", "Source JSON config")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, json: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await updateSource(client, group, id, JSON.parse(json));
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("delete")
    .description("Delete a source")
    .argument("<id>", "Source ID")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        await deleteSource(client, group, id);
        console.log(formatOutput({ message: `Source '${id}' deleted.` }));
      } catch (err) {
        handleError(err);
      }
    });
}
