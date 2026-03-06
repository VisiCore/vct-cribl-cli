import type { AxiosInstance } from "axios";

export interface EdgeNode {
  id: string;
  status: string;
  group: string;
  hostname: string;
  cpus: number;
  totalmem: number;
  platform: string;
  version: string;
  [key: string]: unknown;
}

export interface EdgeNodeSystemInfo {
  hostname: string;
  loadavg: number[];
  memory: { free: number; total: number };
  diskUsage: { diskPath: string; totalDiskSize: number; bytesAvailable: number; bytesUsed: number };
  cpus: Array<{ model: string; speed: number; times: { user: number; nice: number; sys: number; idle: number; irq: number } }>;
  os: { platform: string; arch: string; release: string; type: string };
  uptime: number;
  net: Record<string, unknown[]>;
  [key: string]: unknown;
}

export async function listEdgeNodes(
  client: AxiosInstance,
  fleet?: string
): Promise<EdgeNode[]> {
  const resp = await client.get<{ items: Record<string, unknown>[] }>(
    "/api/v1/master/workers",
    { params: { product: "edge" } }
  );
  const items = resp.data.items ?? [];
  const nodes = items
    .filter((w) => !fleet || w.group === fleet)
    .map((w) => {
      const info = (w.info ?? {}) as Record<string, unknown>;
      const cribl = (info.cribl ?? {}) as Record<string, unknown>;
      return {
        id: w.id as string,
        status: w.status as string,
        group: w.group as string,
        hostname: (info.hostname as string) ?? "",
        cpus: (info.cpus as number) ?? 0,
        totalmem: (info.totalmem as number) ?? 0,
        platform: (info.platform as string) ?? "",
        version: (cribl.version as string) ?? "",
      };
    });
  return nodes;
}

export async function findEdgeNode(
  client: AxiosInstance,
  nameOrId: string
): Promise<EdgeNode | undefined> {
  const all = await listEdgeNodes(client);
  return all.find(
    (n) =>
      n.id === nameOrId ||
      n.hostname === nameOrId ||
      n.hostname.toLowerCase() === nameOrId.toLowerCase()
  );
}

export async function getEdgeNodeSystemInfo(
  client: AxiosInstance,
  nodeId: string
): Promise<EdgeNodeSystemInfo> {
  const resp = await client.get<{ items: EdgeNodeSystemInfo[] }>(
    `/api/v1/w/${encodeURIComponent(nodeId)}/system/info`,
    { params: { fields: "os" } }
  );
  return resp.data.items[0];
}

export async function getEdgeNodeInputs(
  client: AxiosInstance,
  nodeId: string
): Promise<unknown> {
  const resp = await client.get(
    `/api/v1/w/${encodeURIComponent(nodeId)}/system/inputs`
  );
  return resp.data;
}

export async function getEdgeNodeOutputs(
  client: AxiosInstance,
  nodeId: string
): Promise<unknown> {
  const resp = await client.get(
    `/api/v1/w/${encodeURIComponent(nodeId)}/system/outputs`
  );
  return resp.data;
}

export interface MetricsDataPoint {
  time: string;
  cpu_perc?: number;
  mem_used_bytes?: number;
  mem_total_bytes?: number;
  mem_used_pct?: number;
  disk_used_bytes?: number;
  disk_total_bytes?: number;
  disk_used_pct?: number;
  load_avg?: number;
  [key: string]: unknown;
}

export async function getNodeMetrics(
  client: AxiosInstance,
  nodeId: string,
  durationSeconds: number = 3600
): Promise<MetricsDataPoint[]> {
  const now = Math.floor(Date.now() / 1000);
  const earliest = now - durationSeconds;
  const resp = await client.get(
    `/api/v1/w/${encodeURIComponent(nodeId)}/system/metrics`,
    { params: { earliest, latest: now } }
  );
  const entries = resp.data.results?.metrics ?? [];
  return entries
    .filter((e: Record<string, unknown>) => e['system.cpu_perc'])
    .map((e: Record<string, unknown>) => {
      const timeArr = e._time as Array<{ val: number }>;
      const ts = timeArr?.[0]?.val ?? 0;
      const cpu = (e['system.cpu_perc'] as Array<{ val: number }>)?.[0]?.val;
      const freeMem = (e['system.free_mem'] as Array<{ val: number }>)?.[0]?.val;
      const totalMem = (e['system.total_mem'] as Array<{ val: number }>)?.[0]?.val;
      const diskUsed = (e['system.disk_used'] as Array<{ val: number }>)?.[0]?.val;
      const totalDisk = (e['system.total_disk'] as Array<{ val: number }>)?.[0]?.val;
      const loadAvg = (e['system.load_avg'] as Array<{ val: number }>)?.[0]?.val;
      const memUsed = totalMem != null && freeMem != null ? totalMem - freeMem : undefined;
      return {
        time: new Date(ts * 1000).toISOString(),
        cpu_perc: cpu,
        mem_used_bytes: memUsed,
        mem_total_bytes: totalMem,
        mem_used_pct: memUsed != null && totalMem ? (memUsed / totalMem) * 100 : undefined,
        disk_used_bytes: diskUsed,
        disk_total_bytes: totalDisk,
        disk_used_pct: diskUsed != null && totalDisk ? (diskUsed / totalDisk) * 100 : undefined,
        load_avg: loadAvg,
      };
    });
}
