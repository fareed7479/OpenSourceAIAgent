const BASE_URL = "http://localhost:8000/api/v1";

export interface ApiResponse<T = any> {
  data: T;
  status: number;
}

async function request<T = any>(
  endpoint: string,
  method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
  body: any = null
): Promise<T> {
  const token = localStorage.getItem("token");
  
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  const config: RequestInit = {
    method,
    headers,
  };
  
  if (body) {
    config.body = JSON.stringify(body);
  }
  
  const response = await fetch(`${BASE_URL}${endpoint}`, config);
  
  if (response.status === 204) {
    return null as any;
  }
  
  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong");
  }
  
  return data as T;
}

export const api = {
  get: <T = any>(endpoint: string) => request<T>(endpoint, "GET"),
  post: <T = any>(endpoint: string, body?: any) => request<T>(endpoint, "POST", body),
  put: <T = any>(endpoint: string, body?: any) => request<T>(endpoint, "PUT", body),
  delete: <T = any>(endpoint: string) => request<T>(endpoint, "DELETE"),
};
