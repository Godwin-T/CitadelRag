const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("access_token");
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${baseUrl}${path}`, { ...options, headers });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await response.json();
      const detail = data?.detail;
      if (Array.isArray(detail)) {
        const messages = detail
          .map((item) => item?.msg)
          .filter(Boolean)
          .join("; ");
        throw new Error(messages || "Request failed.");
      }
      if (typeof detail === "string") {
        throw new Error(detail);
      }
      throw new Error(data?.message || "Request failed.");
    }
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}
