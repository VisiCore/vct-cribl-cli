import type { AxiosInstance } from "axios";
import type { ApiListResponse, WorkerGroup } from "../types.js";

export async function listWorkerGroups(
  client: AxiosInstance
): Promise<ApiListResponse<WorkerGroup>> {
  const resp = await client.get<ApiListResponse<WorkerGroup>>("/api/v1/master/groups");
  return resp.data;
}

export async function getWorkerGroup(
  client: AxiosInstance,
  id: string
): Promise<WorkerGroup> {
  const resp = await client.get<{ items: WorkerGroup[] }>(
    `/api/v1/master/groups/${encodeURIComponent(id)}`
  );
  return resp.data.items?.[0] ?? resp.data;
}
