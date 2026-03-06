import type { AxiosInstance } from "axios";
import type { ApiListResponse, Destination } from "../types.js";

function groupPath(group: string) {
  return `/api/v1/m/${encodeURIComponent(group)}`;
}

export async function listDestinations(
  client: AxiosInstance,
  group: string
): Promise<ApiListResponse<Destination>> {
  const resp = await client.get<ApiListResponse<Destination>>(
    `${groupPath(group)}/system/outputs`
  );
  return resp.data;
}

/** @deprecated Use listDestinations instead */
export const getDestinations = listDestinations;

export async function getDestination(
  client: AxiosInstance,
  group: string,
  id: string
): Promise<Destination> {
  const resp = await client.get<{ items: Destination[] }>(
    `${groupPath(group)}/system/outputs/${encodeURIComponent(id)}`
  );
  return resp.data.items?.[0] ?? resp.data;
}

export async function createDestination(
  client: AxiosInstance,
  group: string,
  destination: Record<string, unknown>
): Promise<Destination> {
  const resp = await client.post<Destination>(
    `${groupPath(group)}/system/outputs`,
    destination
  );
  return resp.data;
}

export async function updateDestination(
  client: AxiosInstance,
  group: string,
  id: string,
  destination: Record<string, unknown>
): Promise<Destination> {
  const resp = await client.patch<Destination>(
    `${groupPath(group)}/system/outputs/${encodeURIComponent(id)}`,
    destination
  );
  return resp.data;
}

export async function deleteDestination(
  client: AxiosInstance,
  group: string,
  id: string
): Promise<void> {
  await client.delete(
    `${groupPath(group)}/system/outputs/${encodeURIComponent(id)}`
  );
}
