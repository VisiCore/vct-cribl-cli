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

export async function deployGroup(
  client: AxiosInstance,
  group: string
): Promise<unknown> {
  const groupResp = await client.get<{ items: WorkerGroup[] }>(
    `/api/v1/master/groups/${encodeURIComponent(group)}`
  );
  const groupData = groupResp.data.items?.[0] ?? groupResp.data;
  const version = (groupData as Record<string, unknown>).configVersion;

  const resp = await client.patch(
    `/api/v1/master/groups/${encodeURIComponent(group)}/deploy`,
    { version }
  );
  return resp.data;
}
