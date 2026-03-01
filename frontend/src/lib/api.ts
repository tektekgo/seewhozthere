// API service with mock data fallback for SeeWhozThere
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
    const res = await fetch(`${baseUrl}${endpoint}`, { signal: AbortSignal.timeout(3000) });
    return await res.json();
  } catch {
    return fallback;
  }
}

const defaultStatus = { running: false, hailo_available: false, active_cameras: 0 };

export const api = {
  getStats: () => fetchFromApi("/api/stats", mockStats),
  getHourlyActivity: () => fetchFromApi("/api/hourly", mockHourlyData),
  getKnownVsUnknown: () => fetchFromApi("/api/known-unknown", mockKnownVsUnknown),
  getWeeklyTrend: () => fetchFromApi("/api/weekly", mockWeeklyTrend),
  getCameraActivity: () => fetchFromApi("/api/cameras", mockCameraActivity),
  getTopVisitors: () => fetchFromApi("/api/top-visitors", mockTopVisitors),
  getTodayVisitors: () => fetchFromApi("/api/today-visitors", mockTodayVisitors),
  getHeatmapData: () => fetchFromApi("/api/heatmap", mockHeatmapData),
  getStatus: () => fetchFromApi("/api/status", defaultStatus),
};
