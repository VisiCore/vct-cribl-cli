import type { AxiosInstance } from "axios";
import type { ApiListResponse, Source } from "../types.js";

function groupPath(group: string) {
  return `/api/v1/m/${encodeURIComponent(group)}`;
}

export async function listSources(
  client: AxiosInstance,
  group: string
): Promise<ApiListResponse<Source>> {
  const resp = await client.get<ApiListResponse<Source>>(
    `${groupPath(group)}/system/inputs`
  );
  return resp.data;
}

/** @deprecated Use listSources instead */
export const getSources = listSources;

export async function getSource(
  client: AxiosInstance,
  group: string,
  id: string
): Promise<Source> {
  const resp = await client.get<{ items: Source[] }>(
    `${groupPath(group)}/system/inputs/${encodeURIComponent(id)}`
  );
  return resp.data.items?.[0] ?? resp.data;
}

export async function createSource(
  client: AxiosInstance,
  group: string,
  source: Record<string, unknown>
): Promise<Source> {
  const resp = await client.post<Source>(
    `${groupPath(group)}/system/inputs`,
    source
  );
  return resp.data;
}

export async function updateSource(
  client: AxiosInstance,
  group: string,
  id: string,
  source: Record<string, unknown>
): Promise<Source> {
  const resp = await client.patch<Source>(
    `${groupPath(group)}/system/inputs/${encodeURIComponent(id)}`,
    source
  );
  return resp.data;
}

export async function deleteSource(
  client: AxiosInstance,
  group: string,
  id: string
): Promise<void> {
  await client.delete(
    `${groupPath(group)}/system/inputs/${encodeURIComponent(id)}`
  );
}
