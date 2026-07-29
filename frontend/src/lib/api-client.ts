export interface ApiUser {
  id: number;
  username: string;
  is_admin: boolean;
}

export interface ApiApp {
  name: string;
  domain: string;
  status: string;
  replicas: number;
}

export interface AdminApp {
  name: string;
  domain: string;
  status: string;
  owner_id: number;
  owner_username: string;
  replica_count: number;
  created_at: string;
}

export interface ReplicaMetric {
  replica_num: number;
  port: number;
  status: string;
  cpu: string | null;
  memory: string | null;
}

export interface AppDeployment {
  status: string;
  message: string;
  created_at: string;
}

export interface AppConfig {
  key: string;
  value: string;
}

// Client-side helper that hits Next.js API proxy routes
export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const isClient = typeof window !== 'undefined';
  const url = isClient ? `/api/proxy${endpoint}` : `http://127.0.0.1:5000/api${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `API Request failed with status ${response.status}`);
  }

  return data as T;
}
