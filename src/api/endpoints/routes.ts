import type { AxiosInstance } from "axios";
import type { Route } from "../types.js";

function groupPath(group: string) {
  return `/api/v1/m/${encodeURIComponent(group)}`;
}

export async function listRoutes(
  client: AxiosInstance,
  group: string
): Promise<Route> {
  const resp = await client.get<Route>(`${groupPath(group)}/routes`);
  return resp.data;
}

export async function getRoute(
  client: AxiosInstance,
  group: string,
  id: string
): Promise<Route> {
  const resp = await client.get<Route>(
    `${groupPath(group)}/routes/${encodeURIComponent(id)}`
  );
  return resp.data;
}

export async function createRoute(
  client: AxiosInstance,
  group: string,
  route: Record<string, unknown>
): Promise<Route> {
  const resp = await client.post<Route>(
    `${groupPath(group)}/routes`,
    route
  );
  return resp.data;
}

export async function updateRoute(
  client: AxiosInstance,
  group: string,
  id: string,
  route: Record<string, unknown>
): Promise<Route> {
  const resp = await client.patch<Route>(
    `${groupPath(group)}/routes/${encodeURIComponent(id)}`,
    route
  );
  return resp.data;
}

export async function deleteRoute(
  client: AxiosInstance,
  group: string,
  id: string
): Promise<void> {
  await client.delete(
    `${groupPath(group)}/routes/${encodeURIComponent(id)}`
  );
}
