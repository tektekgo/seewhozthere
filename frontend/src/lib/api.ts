// SeeWhozThere API client
import {
  mockStats,
  mockHourlyData,
  mockKnownVsUnknown,
  mockWeeklyTrend,
  mockCameraActivity,
  mockTopVisitors,
  mockTodayVisitors,
  mockHeatmapData,
} from "./mock-data";

const API_URL_KEY = "seewhozhere_api_url";

export function getApiUrl(): string {
  return localStorage.getItem(API_URL_KEY) || "";
}

export function setApiUrl(url: string) {
  localStorage.setItem(API_URL_KEY, url);
}

async function fetchFromApi<T>(endpoint: string, fallback: T): Promise<T> {
  const baseUrl = getApiUrl();
  try {
    const res = await fetch(`${baseUrl}${endpoint}`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

const defaultStatus = { running: false, hailo_available: false, active_cameras: 0, known_people: 0 };

export const api = {
  // --- Analytics ---
  getStats: () => fetchFromApi("/api/stats", mockStats),
  getHourlyActivity: () => fetchFromApi("/api/hourly", mockHourlyData),
  getKnownVsUnknown: () => fetchFromApi("/api/known-unknown", mockKnownVsUnknown),
  getWeeklyTrend: () => fetchFromApi("/api/weekly", mockWeeklyTrend),
  getCameraActivity: () => fetchFromApi("/api/cameras", mockCameraActivity),
  getTopVisitors: () => fetchFromApi("/api/top-visitors", { visitors: mockTopVisitors }),
  getTodayVisitors: () => fetchFromApi("/api/today-visitors", mockTodayVisitors),
  getHeatmapData: () => fetchFromApi("/api/heatmap", mockHeatmapData),

  // --- System status ---
  getStatus: () => fetchFromApi("/api/status", defaultStatus),

  // --- Known visitors ---
  getVisitors: () => fetchFromApi("/api/visitors", { visitors: [] }),
  addVisitor: async (name: string, photo?: File) => {
    const baseUrl = getApiUrl();
    const form = new FormData();
    form.append("name", name);
    if (photo) form.append("photo", photo);
    const res = await fetch(`${baseUrl}/api/visitors`, { method: "POST", body: form });
    return res.json();
  },
  deleteVisitor: async (id: number) => {
    const baseUrl = getApiUrl();
    const res = await fetch(`${baseUrl}/api/visitors/${id}`, { method: "DELETE" });
    return res.json();
  },
  updateVisitor: async (id: number, name?: string, photo?: File) => {
    const baseUrl = getApiUrl();
    const form = new FormData();
    if (name) form.append("name", name);
    if (photo) form.append("photo", photo);
    const res = await fetch(`${baseUrl}/api/visitors/${id}`, { method: "PUT", body: form });
    return res.json();
  },

  // --- Sightings (detection events) ---
  getUnknownSightings: (limit = 50) =>
    fetchFromApi(`/api/unknown-sightings?limit=${limit}`, { sightings: [] }),
  getAllSightings: (limit = 100) =>
    fetchFromApi(`/api/sightings?limit=${limit}`, { sightings: [] }),
  identifySighting: async (sightingId: number, visitorId: number) => {
    const baseUrl = getApiUrl();
    const form = new FormData();
    form.append("visitor_id", String(visitorId));
    const res = await fetch(`${baseUrl}/api/sightings/${sightingId}/identify`, {
      method: "POST",
      body: form,
    });
    return res.json();
  },
  deleteSighting: async (sightingId: number) => {
    const baseUrl = getApiUrl();
    const res = await fetch(`${baseUrl}/api/sightings/${sightingId}`, { method: "DELETE" });
    return res.json();
  },
  bulkDeleteSightings: async (ids: number[]) => {
    const baseUrl = getApiUrl();
    const res = await fetch(`${baseUrl}/api/sightings`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    return res.json();
  },

  // --- Camera config ---
  getCamerasConfig: () => fetchFromApi("/api/config/cameras", { cameras: {} }),
  saveCamerasConfig: async (cameras: Record<string, string>) => {
    const baseUrl = getApiUrl();
    const res = await fetch(`${baseUrl}/api/config/cameras`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cameras }),
    });
    return res.json();
  },

  // --- Service control ---
  getServiceStatus: () =>
    fetchFromApi("/api/service/status", { active: false, installed: false, status: "unknown" }),
  serviceAction: async (action: "start" | "stop" | "restart") => {
    const baseUrl = getApiUrl();
    const res = await fetch(`${baseUrl}/api/service/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    return res.json();
  },
};
