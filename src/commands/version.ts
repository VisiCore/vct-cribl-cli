import { Command } from "commander";
import { getClient } from "../api/client.js";
import {
  getVersionInfo, getVersionStatus, getVersionDiff,
  commitVersion, pushVersion, syncVersion,
  listBranches, getCurrentBranch,
} from "../api/endpoints/version.js";
import { resolveGroup } from "../utils/group-resolver.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

export function registerVersionCommand(program: Command): void {
  const cmd = program.command("version").description("Version control operations");

  cmd
    .command("info")
    .description("Get version info")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await getVersionInfo(client, group);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("status")
    .description("Get version status")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await getVersionStatus(client, group);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("diff")
    .description("Get version diff")
    .option("-g, --group <name>", "Worker group name")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await getVersionDiff(client, group);
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("commit")
    .description("Commit changes")
    .argument("<message>", "Commit message")
    .option("-g, --group <name>", "Worker group name")
    .action(async (message: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await commitVersion(client, group, message);
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("push")
    .description("Push committed changes")
    .option("-g, --group <name>", "Worker group name")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await pushVersion(client, group);
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("sync")
    .description("Sync with remote")
    .option("-g, --group <name>", "Worker group name")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await syncVersion(client, group);
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("branches")
    .description("List branches")
    .option("-g, --group <name>", "Worker group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await listBranches(client, group);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("deploy")
    .description("Commit and push changes in one step")
    .argument("<message>", "Commit message")
    .option("-g, --group <name>", "Worker group name")
    .action(async (message: string, opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const commitResult = await commitVersion(client, group, message);
        console.log(formatOutput({ step: "commit", result: commitResult }));
        const pushResult = await pushVersion(client, group);
        console.log(formatOutput({ step: "push", result: pushResult }));
        console.log(formatOutput({ message: "Deploy complete: committed and pushed." }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("current-branch")
    .description("Get current branch")
    .option("-g, --group <name>", "Worker group name")
    .action(async (opts) => {
      try {
        const client = getClient();
        const group = await resolveGroup(client, opts.group);
        const data = await getCurrentBranch(client, group);
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });
}
