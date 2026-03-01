import { useState } from "react";
import logo from "@/assets/logo.png";

interface LoginProps {
  onSuccess: () => void;
  defaultPassphrase: boolean;
}

export default function Login({ onSuccess, defaultPassphrase }: LoginProps) {
  const [passphrase, setPassphrase] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ passphrase }),
      });
      const data = await res.json();

      if (data.success) {
        onSuccess();
      } else {
        setError("Incorrect passphrase. Please try again.");
        setPassphrase("");
      }
    } catch {
      setError("Could not connect to the server. Is it running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-8">

        {/* Logo + branding */}
        <div className="flex flex-col items-center gap-4">
          <img
            src={logo}
            alt="SeeWhozThere"
            className="h-24 w-24 object-contain drop-shadow-lg"
          />
          <div className="text-center space-y-1">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              SeeWhozThere
            </h1>
            <p className="text-sm text-muted-foreground">Smart Home Security</p>
          </div>
        </div>

        {/* Default passphrase warning */}
        {defaultPassphrase && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-xs text-amber-600 dark:text-amber-400 space-y-1">
            <p className="font-semibold">⚠ Default passphrase in use</p>
            <p>
              You are using the default passphrase{" "}
              <code className="bg-black/10 dark:bg-white/10 px-1 rounded">changeme</code>.
              Update it in <code className="bg-black/10 dark:bg-white/10 px-1 rounded">config.ini</code>{" "}
              under <code className="bg-black/10 dark:bg-white/10 px-1 rounded">[SECURITY]</code> before
              sharing this app.
            </p>
          </div>
        )}

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="passphrase"
              className="block text-sm font-medium text-foreground"
            >
              Passphrase
            </label>
            <input
              id="passphrase"
              type="password"
              autoComplete="current-password"
              autoFocus
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              placeholder="Enter your passphrase"
              className="w-full rounded-lg border border-input bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition"
              required
            />
          </div>

          {error && (
            <p className="text-xs text-red-500 font-medium">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !passphrase}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        {/* Footer */}
        <p className="text-center text-[11px] text-muted-foreground">
          SeeWhozThere &middot; Smart Home Security &middot;{" "}
          <a
            href="https://github.com/tektekgo/seewhozthere"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-foreground"
          >
            GitHub
          </a>
        </p>
      </div>
    </div>
  );
}
