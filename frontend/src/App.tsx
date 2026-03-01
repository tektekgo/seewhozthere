import { useState, useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { ThemeProvider } from "@/hooks/use-theme";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import Index from "./pages/Index";
import History from "./pages/History";
import Settings from "./pages/Settings";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

// ─── Auth context ────────────────────────────────────────────────────────────

interface AuthState {
  checked: boolean;   // has the initial auth-status check completed?
  authed: boolean;    // is the user authenticated?
  loginEnabled: boolean;
  defaultPassphrase: boolean;
}

// ─── Protected layout (wraps all real pages) ─────────────────────────────────

function ProtectedLayout({
  auth,
  onLogout,
}: {
  auth: AuthState;
  onLogout: () => void;
}) {
  const navigate = useNavigate();

  // While we haven't finished the initial check, show nothing (avoids flash)
  if (!auth.checked) return null;

  // Not authenticated → send to login
  if (auth.loginEnabled && !auth.authed) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar onLogout={onLogout} />
      <div className="flex-1">
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
      <Footer />
    </div>
  );
}

// ─── Root app ────────────────────────────────────────────────────────────────

const AppInner = () => {
  const [auth, setAuth] = useState<AuthState>({
    checked: false,
    authed: false,
    loginEnabled: true,
    defaultPassphrase: false,
  });

  // Check auth status on mount
  useEffect(() => {
    fetch("/api/auth-status", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        setAuth({
          checked: true,
          authed: data.authenticated,
          loginEnabled: data.login_enabled,
          defaultPassphrase: data.default_passphrase,
        });
      })
      .catch(() => {
        // If the server is unreachable, allow access (avoids login loop on local network)
        setAuth({ checked: true, authed: true, loginEnabled: false, defaultPassphrase: false });
      });
  }, []);

  const handleLogout = async () => {
    await fetch("/api/logout", { method: "POST", credentials: "include" });
    setAuth((prev) => ({ ...prev, authed: false }));
  };

  const handleLoginSuccess = () => {
    setAuth((prev) => ({ ...prev, authed: true }));
  };

  if (!auth.checked) return null; // wait for initial auth check

  return (
    <Routes>
      {/* Login page — outside the protected layout, no Navbar */}
      <Route
        path="/login"
        element={
          auth.authed || !auth.loginEnabled ? (
            <Navigate to="/" replace />
          ) : (
            <Login
              onSuccess={handleLoginSuccess}
              defaultPassphrase={auth.defaultPassphrase}
            />
          )
        }
      />

      {/* All other routes are protected */}
      <Route
        path="/*"
        element={<ProtectedLayout auth={auth} onLogout={handleLogout} />}
      />
    </Routes>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter basename="/dashboard">
          <AppInner />
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
