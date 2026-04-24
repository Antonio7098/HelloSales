import { getFrontendEnv } from "@/shared/config/env";

type RequestOptions = RequestInit & {
  path: string;
};

export class HttpRequestError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "HttpRequestError";
    this.status = status;
    this.payload = payload;
  }
}

export async function requestJson<T>({ path, ...init }: RequestOptions): Promise<T> {
  const response = await fetch(`${getFrontendEnv().apiBaseUrl}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new HttpRequestError(`Request failed with status ${response.status}`, response.status, payload);
  }

  return (await response.json()) as T;
}
