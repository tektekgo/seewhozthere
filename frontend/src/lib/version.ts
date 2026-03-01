// App version — bump the patch number for each release
export const APP_VERSION = "2.0.0";

// Build number — set by build_frontend.sh at build time (format: YYYYMMDD.NNN)
export const BUILD_NUMBER = import.meta.env.VITE_BUILD_NUMBER || "dev";

// Build date — set by build_frontend.sh at build time
export const BUILD_DATE = import.meta.env.VITE_BUILD_DATE || new Date().toISOString().split("T")[0];
