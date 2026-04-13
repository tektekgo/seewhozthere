// Git commit hash — injected by vite.config.ts at build time via execSync('git rev-parse --short HEAD')
// This lets you trace exactly which commit is running on the Pi by checking GitHub.
export const GIT_HASH: string = import.meta.env.VITE_GIT_HASH || "dev";

// Build date — injected by vite.config.ts at build time
export const BUILD_DATE: string =
  import.meta.env.VITE_BUILD_DATE ||
  new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
