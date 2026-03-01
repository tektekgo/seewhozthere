import { Link, useLocation } from "react-router-dom";
import { Moon, Sun, Cpu, Wifi, WifiOff } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import logo from "@/assets/logo.png";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const navItems = [
  { label: "Dashboard", path: "/" },
  { label: "History", path: "/history" },
  { label: "Settings", path: "/settings" },
];

interface SystemStatus {
  running: boolean;
  hailo_available: boolean;
  active_cameras: number;
}

export function Navbar() {
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    const fetchStatus = () => {
      api.getStatus().then(setStatus).catch(() => setStatus(null));
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const isOnline = status?.running === true;
  const hasHailo = status?.hailo_available === true;

  return (
    <header className="sticky top-0 z-50 border-b bg-card/80 backdrop-blur-md">
      <div className="container flex h-14 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-bold text-lg">
          <img src={logo} alt="SeeWhozThere logo" className="h-7 w-7 rounded" />
          <div className="flex flex-col leading-tight">
            <span className="text-base font-bold">SeeWhozThere</span>
            <span className="text-[10px] font-normal text-muted-foreground hidden sm:block">Smart Home Security</span>
          </div>
        </Link>

        <nav className="flex items-center gap-1">
          {navItems.map((item) => (
            <Link key={item.path} to={item.path}>
              <Button
                variant={location.pathname === item.path ? "secondary" : "ghost"}
                size="sm"
              >
                {item.label}
              </Button>
            </Link>
          ))}

          {/* System Status */}
          <div className="flex items-center gap-1.5 ml-3 px-2 py-1 rounded-md border bg-background/50">
            {isOnline ? (
              <Wifi className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <WifiOff className="h-3.5 w-3.5 text-red-500" />
            )}
            <span className={`text-xs font-medium ${isOnline ? 'text-green-500' : 'text-red-500'}`}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
            {hasHailo && (
              <Badge variant="outline" className="h-4 px-1 text-[9px] font-bold text-purple-500 border-purple-500/50 ml-0.5">
                <Cpu className="h-2.5 w-2.5 mr-0.5" />AI
              </Badge>
            )}
          </div>

          <Button variant="ghost" size="icon" onClick={toggle} className="ml-1">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </nav>
      </div>
    </header>
  );
}
