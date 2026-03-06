import type { AxiosInstance } from "axios";
import type { ApiListResponse, Credential } from "../types.js";

function groupPath(group: string) {
  return `/api/v1/m/${encodeURIComponent(group)}`;
}

export async function listCredentials(client: AxiosInstance, group: string): Promise<ApiListResponse<Credential>> {
  const resp = await client.get<ApiListResponse<Credential>>(`${groupPath(group)}/system/credentials`);
  return resp.data;
}

export async function getCredential(client: AxiosInstance, group: string, id: string): Promise<Credential> {
  const resp = await client.get<{ items: Credential[] }>(`${groupPath(group)}/system/credentials/${encodeURIComponent(id)}`);
  return resp.data.items?.[0] ?? resp.data;
}

export async function createCredential(client: AxiosInstance, group: string, credential: Record<string, unknown>): Promise<Credential> {
  const resp = await client.post<Credential>(`${groupPath(group)}/system/credentials`, credential);
  return resp.data;
}

export async function updateCredential(client: AxiosInstance, group: string, id: string, credential: Record<string, unknown>): Promise<Credential> {
  const resp = await client.patch<Credential>(`${groupPath(group)}/system/credentials/${encodeURIComponent(id)}`, credential);
  return resp.data;
}

export async function deleteCredential(client: AxiosInstance, group: string, id: string): Promise<void> {
  await client.delete(`${groupPath(group)}/system/credentials/${encodeURIComponent(id)}`);
}
