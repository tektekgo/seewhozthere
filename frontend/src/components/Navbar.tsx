import { Link, useLocation } from "react-router-dom";
import { Moon, Sun, Cpu, Camera, Activity, UserPlus, LogOut } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import logo from "@/assets/logo.png";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";

const navItems = [
  { label: "Dashboard", path: "/" },
  { label: "History", path: "/history" },
  { label: "People", path: "/people" },
  { label: "Settings", path: "/settings" },
];

interface SystemStatus {
  running: boolean;
  hailo_available: boolean;
  active_cameras: number;
  camera_names?: string[];
}

function AddVisitorDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const res = await api.addVisitor(name.trim(), photo ?? undefined);
      if (res.id) {
        toast.success(`${name.trim()} added as a known visitor`);
        setName(""); setPhoto(null);
        onClose();
      } else {
        toast.error(res.detail ?? "Failed to add visitor");
      }
    } catch {
      toast.error("An error occurred");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Add Known Visitor</DialogTitle>
          <DialogDescription>
            Register a person so the system can recognise them in future detections.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium mb-1 block">Full name</label>
            <Input
              placeholder="e.g. Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">
              Reference photo{" "}
              <span className="text-muted-foreground font-normal">(optional — improves recognition)</span>
            </label>
            <Input type="file" accept="image/*" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? "Adding…" : "Add Visitor"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Status dot ───────────────────────────────────────────────────────────────

function StatusDot({ on }: { on: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full shrink-0 ${
        on ? "bg-green-500" : "bg-red-500"
      }`}
    />
  );
}

// ─── Navbar ───────────────────────────────────────────────────────────────────

export function Navbar({ onLogout }: { onLogout?: () => void }) {
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [showAddVisitor, setShowAddVisitor] = useState(false);

  useEffect(() => {
    const fetchStatus = () => {
      api.getStatus().then(setStatus).catch(() => setStatus(null));
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  // Three distinct status signals
  const cameraOn = (status?.active_cameras ?? 0) > 0;
  const detectionOn = status?.running === true;
  const aiOn = status?.hailo_available === true;

  const cameraLabel = cameraOn
    ? `${status!.active_cameras} camera${status!.active_cameras !== 1 ? "s" : ""} configured in config.ini`
    : "No cameras configured — add one in Settings → Cameras";
  const detectionLabel = detectionOn
    ? "Face detection app is running (seewhozthere service)"
    : "Face detection app is stopped — go to Settings → App Control to start it";
  const aiLabel = aiOn
    ? "Hailo AI HAT+ detected — hardware-accelerated face detection active"
    : "Hailo AI chip not detected — using software (OpenCV) detection";

  return (
    <>
      <header className="sticky top-0 z-50 border-b bg-card/80 backdrop-blur-md">
        <div className="container flex h-14 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 font-bold text-lg">
            <img src={logo} alt="SeeWhozThere™ logo" className="h-8 w-8 object-contain" />
            <div className="flex flex-col leading-tight">
              <span className="text-base font-bold">SeeWhozThere™</span>
              <span className="text-[10px] font-normal text-muted-foreground hidden sm:block">Smart Home Security</span>
            </div>
          </Link>

          <nav className="flex items-center gap-1">
            {/* Nav links */}
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

            {/* Add Known Visitor */}
            <Button
              variant="outline"
              size="sm"
              className="ml-2 hidden sm:flex items-center gap-1.5"
              onClick={() => setShowAddVisitor(true)}
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span className="text-xs">Add Person</span>
            </Button>

            {/* ── Status indicators ── */}
            <TooltipProvider delayDuration={200}>
              <div className="flex items-center gap-2 ml-2 px-2.5 py-1 rounded-md border bg-background/50">

                {/* Camera */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1 cursor-default">
                      <StatusDot on={cameraOn} />
                      <Camera className={`h-3.5 w-3.5 ${cameraOn ? "text-green-500" : "text-muted-foreground"}`} />
                      <span className={`text-[11px] font-medium hidden md:inline ${cameraOn ? "text-green-500" : "text-muted-foreground"}`}>
                        Cam
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs text-xs">
                    <p className="font-semibold mb-0.5">Camera Config</p>
                    <p>{cameraLabel}</p>
                  </TooltipContent>
                </Tooltip>

                <span className="text-border">|</span>

                {/* Detection */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1 cursor-default">
                      <StatusDot on={detectionOn} />
                      <Activity className={`h-3.5 w-3.5 ${detectionOn ? "text-green-500" : "text-red-500"}`} />
                      <span className={`text-[11px] font-medium hidden md:inline ${detectionOn ? "text-green-500" : "text-red-500"}`}>
                        {detectionOn ? "Running" : "Stopped"}
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs text-xs">
                    <p className="font-semibold mb-0.5">Detection App</p>
                    <p>{detectionLabel}</p>
                  </TooltipContent>
                </Tooltip>

                <span className="text-border">|</span>

                {/* AI Engine */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1 cursor-default">
                      <StatusDot on={aiOn} />
                      <Cpu className={`h-3.5 w-3.5 ${aiOn ? "text-purple-500" : "text-muted-foreground"}`} />
                      {aiOn && (
                        <Badge variant="outline" className="h-4 px-1 text-[9px] font-bold text-purple-500 border-purple-500/50">
                          HAT+
                        </Badge>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs text-xs">
                    <p className="font-semibold mb-0.5">AI Engine</p>
                    <p>{aiLabel}</p>
                  </TooltipContent>
                </Tooltip>

              </div>
            </TooltipProvider>

            {/* Dark/Light toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={toggle}
              className="ml-1"
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>

            {/* Sign Out */}
            {onLogout && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onLogout}
                    className="ml-0.5 text-muted-foreground hover:text-red-500"
                    aria-label="Sign out"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs">
                  Sign out
                </TooltipContent>
              </Tooltip>
            )}
          </nav>
        </div>
      </header>

      <AddVisitorDialog open={showAddVisitor} onClose={() => setShowAddVisitor(false)} />
    </>
  );
}
