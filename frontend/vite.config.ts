import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { execSync } from "child_process";

// Bake git info into the build at compile time so the footer always shows
// exactly which commit is running on the Pi.
function getGitInfo() {
  try {
    const hash = execSync("git rev-parse --short HEAD", { cwd: path.resolve(__dirname, "..") })
      .toString()
      .trim();
    const date = new Date().toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    return { hash, date };
  } catch {
    return { hash: "unknown", date: new Date().toISOString().split("T")[0] };
  }
}

const { hash: GIT_HASH, date: BUILD_DATE } = getGitInfo();

// https://vitejs.dev/config/
export default defineConfig(() => ({
  base: "/dashboard/",
  server: {
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
  },
  define: {
    // Injected at build time — available as import.meta.env.VITE_GIT_HASH etc.
    "import.meta.env.VITE_GIT_HASH": JSON.stringify(GIT_HASH),
    "import.meta.env.VITE_BUILD_DATE": JSON.stringify(BUILD_DATE),
  },
  plugins: [react()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // Use stable filenames so a git pull + service restart is all that's needed
    // (no more hash-mismatch 404s when the Pi serves a cached index.html)
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith(".css")) return "assets/index.css";
          return "assets/[name][extname]";
        },
      },
    },
  },
}));
