import { Command } from "commander";
import { getClient } from "../api/client.js";
import { listContainers, listProcesses, getEdgeLogs, getEdgeMetadata, getEdgeEvents, getEdgeFile, listEdgeFiles, getEdgeKubeLogs } from "../api/endpoints/edge.js";
import { listEdgeNodes, findEdgeNode, getEdgeNodeSystemInfo, getEdgeNodeInputs, getEdgeNodeOutputs, getNodeMetrics, getEdgeNodeFileInspect, listEdgeNodeFiles, searchEdgeNodeFile } from "../api/endpoints/edge-nodes.js";
import { formatOutput } from "../output/formatter.js";
import { handleError } from "../utils/errors.js";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const parts: string[] = [];
  if (d > 0) parts.push(`${d}d`);
  if (h > 0) parts.push(`${h}h`);
  parts.push(`${m}m`);
  return parts.join(" ");
}

export function registerEdgeCommand(program: Command): void {
  const cmd = program.command("edge").description("Cribl Edge fleet management");

  cmd
    .command("containers")
    .description("List containers on edge nodes")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await listContainers(getClient(), opts.fleet);
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("processes")
    .description("List processes on edge nodes")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await listProcesses(getClient(), opts.fleet);
        console.log(formatOutput(data.items, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("logs")
    .description("Get edge node logs")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .action(async (opts) => {
      try {
        const data = await getEdgeLogs(getClient(), opts.fleet);
        console.log(formatOutput(data));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("metadata")
    .description("Get edge node metadata")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await getEdgeMetadata(getClient(), opts.fleet);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("events")
    .description("Get edge events")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await getEdgeEvents(getClient(), opts.fleet);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("files")
    .description("Browse edge files")
    .argument("<path>", "File path")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (filePath: string, opts) => {
      try {
        const data = await getEdgeFile(getClient(), opts.fleet, filePath);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("ls")
    .description("List edge directory contents")
    .argument("<path>", "Directory path")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (dirPath: string, opts) => {
      try {
        const data = await listEdgeFiles(getClient(), opts.fleet, dirPath);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("kube-logs")
    .description("Get Kubernetes logs")
    .requiredOption("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const data = await getEdgeKubeLogs(getClient(), opts.fleet);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("nodes")
    .description("List edge nodes (optionally filtered by fleet)")
    .option("-f, --fleet <name>", "Fleet/group name")
    .option("--table", "Table output")
    .action(async (opts) => {
      try {
        const nodes = await listEdgeNodes(getClient(), opts.fleet);
        const summary = nodes.map((n) => ({
          id: n.id,
          hostname: n.hostname,
          status: n.status,
          fleet: n.group,
          cpus: n.cpus,
          memory: formatBytes(n.totalmem),
          platform: n.platform,
          version: n.version,
        }));
        console.log(formatOutput(summary, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("system-info")
    .description("Get system info for an edge node (CPU, memory, disk, network)")
    .argument("<node>", "Node hostname or ID")
    .option("--table", "Table output")
    .action(async (node: string, opts) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          const all = await listEdgeNodes(client);
          const names = all.map((n) => n.hostname || n.id).join(", ");
          console.error(`Node "${node}" not found. Available nodes: ${names}`);
          process.exit(1);
        }
        const info = await getEdgeNodeSystemInfo(client, found.id);
        const totalCpuTimes = info.cpus.reduce(
          (acc, c) => {
            acc.user += c.times.user;
            acc.sys += c.times.sys;
            acc.idle += c.times.idle;
            return acc;
          },
          { user: 0, sys: 0, idle: 0 }
        );
        const totalTime = totalCpuTimes.user + totalCpuTimes.sys + totalCpuTimes.idle;
        const summary = {
          hostname: info.hostname,
          os: `${info.os.type} ${info.os.arch} ${info.os.release}`,
          uptime: formatUptime(info.uptime),
          cpu: {
            cores: info.cpus.length,
            model: info.cpus[0]?.model ?? "unknown",
            speed_mhz: info.cpus[0]?.speed ?? 0,
            user_pct: `${((totalCpuTimes.user / totalTime) * 100).toFixed(2)}%`,
            sys_pct: `${((totalCpuTimes.sys / totalTime) * 100).toFixed(2)}%`,
            idle_pct: `${((totalCpuTimes.idle / totalTime) * 100).toFixed(2)}%`,
          },
          load_avg: {
            "1min": info.loadavg[0],
            "5min": info.loadavg[1],
            "15min": info.loadavg[2],
          },
          memory: {
            total: formatBytes(info.memory.total),
            free: formatBytes(info.memory.free),
            used: formatBytes(info.memory.total - info.memory.free),
            used_pct: `${(((info.memory.total - info.memory.free) / info.memory.total) * 100).toFixed(1)}%`,
          },
          disk: {
            path: info.diskUsage.diskPath,
            total: formatBytes(info.diskUsage.totalDiskSize),
            used: formatBytes(info.diskUsage.bytesUsed),
            available: formatBytes(info.diskUsage.bytesAvailable),
            used_pct: `${((info.diskUsage.bytesUsed / info.diskUsage.totalDiskSize) * 100).toFixed(1)}%`,
          },
        };
        console.log(formatOutput(summary, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("system-info-raw")
    .description("Get raw system info JSON for an edge node")
    .argument("<node>", "Node hostname or ID")
    .action(async (node: string) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          const all = await listEdgeNodes(client);
          const names = all.map((n) => n.hostname || n.id).join(", ");
          console.error(`Node "${node}" not found. Available nodes: ${names}`);
          process.exit(1);
        }
        const info = await getEdgeNodeSystemInfo(client, found.id);
        console.log(formatOutput(info));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("inputs")
    .description("Get inputs/sources for an edge node")
    .argument("<node>", "Node hostname or ID")
    .option("--table", "Table output")
    .action(async (node: string, opts) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          console.error(`Node "${node}" not found.`);
          process.exit(1);
        }
        const data = await getEdgeNodeInputs(client, found.id);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("outputs")
    .description("Get outputs/destinations for an edge node")
    .argument("<node>", "Node hostname or ID")
    .option("--table", "Table output")
    .action(async (node: string, opts) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          console.error(`Node "${node}" not found.`);
          process.exit(1);
        }
        const data = await getEdgeNodeOutputs(client, found.id);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("fileinspect")
    .description("Inspect a file on an edge node (stat, hashes, head, hexdump)")
    .argument("<node>", "Node hostname or ID")
    .argument("<path>", "File path on the node")
    .option("--table", "Table output")
    .action(async (node: string, filePath: string, opts) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          console.error(`Node "${node}" not found.`);
          process.exit(1);
        }
        const data = await getEdgeNodeFileInspect(client, found.id, filePath);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("node-ls")
    .description("List directory contents on a specific edge node")
    .argument("<node>", "Node hostname or ID")
    .argument("<path>", "Directory path on the node")
    .option("--stats", "Include file stats (size, permissions, timestamps)")
    .option("--table", "Table output")
    .action(async (node: string, dirPath: string, opts) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          console.error(`Node "${node}" not found.`);
          process.exit(1);
        }
        const data = await listEdgeNodeFiles(client, found.id, dirPath, opts.stats);
        console.log(formatOutput(data, { table: opts.table }));
      } catch (err) {
        handleError(err);
      }
    });

  cmd
    .command("file-search")
    .description("Search or read file contents on an edge node")
    .argument("<node>", "Node hostname or ID")
    .argument("<path>", "File path on the node")
    .option("-q, --query <query>", "Search string (omit to read all lines)")
    .option("-l, --limit <n>", "Max lines to return", "50")
    .option("-o, --offset <n>", "Offset (for pagination)", "0")
    .option("--raw", "Print only _raw lines (file content)")
    .option("--table", "Table output")
    .action(async (node: string, filePath: string, opts) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          console.error(`Node "${node}" not found.`);
          process.exit(1);
        }
        const data = await searchEdgeNodeFile(
          client, found.id, filePath, opts.query,
          parseInt(opts.limit, 10), parseInt(opts.offset, 10)
        );
        if (opts.raw) {
          const items = (data as Record<string, unknown>).items as Record<string, unknown>[] ?? [];
          const events = (items[0]?.items as Record<string, unknown>[]) ?? [];
          for (const e of events) {
            console.log(e._raw);
          }
        } else {
          console.log(formatOutput(data, { table: opts.table }));
        }
      } catch (err) {
        handleError(err);
      }
    });

  const durMap: Record<string, number> = {
    "5m": 300, "10m": 600, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "12h": 43200, "1d": 86400,
  };

  cmd
    .command("metrics")
    .description("Get historical metrics (CPU, memory, disk, load) for a node")
    .argument("<node>", "Node hostname or ID")
    .option("-d, --duration <duration>", "Time range: 5m, 10m, 15m, 30m, 1h, 4h, 12h, 1d", "1h")
    .option("--summary", "Show min/max/avg summary instead of time series")
    .option("--table", "Table output")
    .action(async (node: string, opts) => {
      try {
        const client = getClient();
        const found = await findEdgeNode(client, node);
        if (!found) {
          const all = await listEdgeNodes(client);
          const names = all.map((n) => n.hostname || n.id).join(", ");
          console.error(`Node "${node}" not found. Available nodes: ${names}`);
          process.exit(1);
        }
        const seconds = durMap[opts.duration];
        if (!seconds) {
          console.error(`Invalid duration "${opts.duration}". Use: ${Object.keys(durMap).join(", ")}`);
          process.exit(1);
        }
        const points = await getNodeMetrics(client, found.id, seconds);
        if (points.length === 0) {
          console.error("No metrics data available for this time range.");
          process.exit(1);
        }

        if (opts.summary) {
          const cpus = points.map((p) => p.cpu_perc).filter((v): v is number => v != null);
          const mems = points.map((p) => p.mem_used_pct).filter((v): v is number => v != null);
          const loads = points.map((p) => p.load_avg).filter((v): v is number => v != null);
          const disks = points.map((p) => p.disk_used_pct).filter((v): v is number => v != null);
          const agg = (arr: number[]) => ({
            min: `${Math.min(...arr).toFixed(1)}%`,
            max: `${Math.max(...arr).toFixed(1)}%`,
            avg: `${(arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1)}%`,
          });
          const aggLoad = (arr: number[]) => ({
            min: Math.min(...arr).toFixed(2),
            max: Math.max(...arr).toFixed(2),
            avg: (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2),
          });
          const summary = {
            hostname: found.hostname,
            duration: opts.duration as string,
            data_points: points.length,
            from: points[0].time,
            to: points[points.length - 1].time,
            cpu_perc: cpus.length ? agg(cpus) : null,
            mem_used_pct: mems.length ? agg(mems) : null,
            disk_used_pct: disks.length ? agg(disks) : null,
            load_avg: loads.length ? aggLoad(loads) : null,
          };
          console.log(formatOutput(summary, { table: opts.table }));
        } else {
          const series = points.map((p) => ({
            time: p.time,
            cpu_pct: p.cpu_perc != null ? `${p.cpu_perc.toFixed(1)}%` : "-",
            mem_used: p.mem_used_bytes != null ? formatBytes(p.mem_used_bytes) : "-",
            mem_pct: p.mem_used_pct != null ? `${p.mem_used_pct.toFixed(1)}%` : "-",
            disk_pct: p.disk_used_pct != null ? `${p.disk_used_pct.toFixed(1)}%` : "-",
            load: p.load_avg != null ? p.load_avg.toFixed(2) : "-",
          }));
          console.log(formatOutput(series, { table: opts.table }));
        }
      } catch (err) {
        handleError(err);
      }
    });
}
