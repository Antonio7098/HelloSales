type FrontendEnv = {
  apiBaseUrl: string;
};

export function getFrontendEnv(): FrontendEnv {
  return {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "/api",
  };
}
