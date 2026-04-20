import { getFrontendEnv } from "@/shared/config/env";

type RequestOptions = RequestInit & {
  path: string;
};

export async function requestJson<T>({ path, ...init }: RequestOptions): Promise<T> {
  const response = await fetch(`${getFrontendEnv().apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}
