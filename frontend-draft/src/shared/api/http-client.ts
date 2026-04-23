import { getFrontendEnv } from "@/shared/config/env";

type RequestOptions = RequestInit & {
  path: string;
};

type ApiErrorEnvelope = {
  ok: false;
  error?: {
    message?: unknown;
    code?: unknown;
    category?: unknown;
    details?: unknown;
  };
};

export class ApiRequestError extends Error {
  status: number;
  code: string | null;
  category: string | null;
  details: unknown;

  constructor(
    message: string,
    options: {
      status: number;
      code?: string | null;
      category?: string | null;
      details?: unknown;
    },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status;
    this.code = options.code ?? null;
    this.category = options.category ?? null;
    this.details = options.details ?? null;
  }
}

export async function requestJson<T>({ path, ...init }: RequestOptions): Promise<T> {
  const response = await fetch(`${getFrontendEnv().apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let payload: ApiErrorEnvelope | null = null;
    try {
      payload = (await response.json()) as ApiErrorEnvelope;
    } catch {
      payload = null;
    }
    const message =
      typeof payload?.error?.message === "string"
        ? payload.error.message
        : `Request failed with status ${response.status}`;
    throw new ApiRequestError(message, {
      status: response.status,
      code: typeof payload?.error?.code === "string" ? payload.error.code : null,
      category: typeof payload?.error?.category === "string" ? payload.error.category : null,
      details: payload?.error?.details ?? null,
    });
  }

  return (await response.json()) as T;
}
