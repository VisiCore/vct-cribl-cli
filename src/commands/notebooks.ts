import { Command } from "commander";
import { getClient } from "../api/client.js";
import { listNotebooks, getNotebook, addToNotebook, deleteNotebook } from "../api/endpoints/notebooks.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

export function registerNotebooksCommand(program: Command): void {
  const notebooks = program.command("notebooks").description("Search notebooks");

  notebooks
    .command("list")
    .description("List search notebooks")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await listNotebooks(getClient(), opts.group);
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  notebooks
    .command("get")
    .description("Get a notebook by ID")
    .argument("<id>", "Notebook ID")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (id: string, opts) => {
      try {
        const data = await getNotebook(getClient(), id, opts.group);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  notebooks
    .command("add")
    .description("Add query to a notebook")
    .requiredOption("--notebook-id <id>", "Notebook ID")
    .requiredOption("--query <query>", "Search query to add")
    .option("--name <name>", "Name for the query entry")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const result = await addToNotebook(getClient(), {
          notebookId: opts.notebookId,
          query: opts.query,
          name: opts.name,
          group: opts.group,
        });
        console.log(formatOutput(result, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  notebooks
    .command("delete")
    .description("Delete a notebook")
    .argument("<id>", "Notebook ID")
    .option("-g, --group <name>", "Worker group name")
    .action(async (id: string, opts) => {
      try {
        await deleteNotebook(getClient(), id, opts.group);
        console.log(formatOutput({ message: `Notebook '${id}' deleted.` }));
      } catch (err) {
        handleError(err);
      }
    });
}
