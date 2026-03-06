import { Command } from "commander";
import { getClient } from "../api/client.js";
import { listPipelines, getPipeline, createPipeline, updatePipeline, deletePipeline } from "../api/endpoints/pipelines.js";
import { resolveGroup } from "../utils/group-resolver.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

export function registerPipelinesCommand(program: Command): void {
  const cmd = program.command("pipelines").description("Manage pipelines");

  cmd
    .command("list")
    .description("List pipelines")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await listPipelines(client, group);
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("get")
    .description("Get a pipeline by ID")
    .argument("<id>", "Pipeline ID")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (id: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await getPipeline(client, group, id);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("create")
    .description("Create a pipeline from JSON")
    .argument("<json>", "Pipeline JSON config")
    .option("-g, --group <name>", "Worker group name")
    .action(async (json: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await createPipeline(client, group, JSON.parse(json));
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("update")
    .description("Update a pipeline")
    .argument("<id>", "Pipeline ID")
    .argument("<json>", "Pipeline JSON config")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, json: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await updatePipeline(client, group, id, JSON.parse(json));
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("clone")
    .description("Clone a pipeline from one worker group to another")
    .argument("<id>", "Pipeline ID to clone")
    .requiredOption("--from <group>", "Source worker group")
    .requiredOption("--to <group>", "Target worker group")
    .option("--new-id <id>", "New pipeline ID (defaults to original)")
    .action(async (id: string, opts) => {
      try {
        const client = getClient();
        const pipeline = await getPipeline(client, opts.from, id);
        const pipelineData = { ...pipeline } as Record<string, unknown>;
        if (opts.newId) pipelineData.id = opts.newId;
        const result = await createPipeline(client, opts.to, pipelineData);
        console.log(formatOutput(result));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("delete")
    .description("Delete a pipeline")
    .argument("<id>", "Pipeline ID")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        await deletePipeline(client, group, id);
        console.log(formatOutput({ message: `Pipeline '${id}' deleted.` }));
      } catch (err) {
        handleError(err);
      }
    });
}
