import { Link, useLocation } from "react-router-dom";
import { Moon, Sun, Cpu, Camera, Activity, UserPlus, LogOut, Brain } from "lucide-react";
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
  recognition_engine?: string;
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
            {saving ? "Adding\u2026" : "Add Visitor"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Status dot with optional pulse animation for active state
function StatusDot({ on }: { on: boolean }) {
  return (
    <span className="relative flex h-2 w-2 shrink-0">
      {on && (
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-60" />
      )}
      <span
        className={`relative inline-flex h-2 w-2 rounded-full ${on ? "bg-green-500" : "bg-red-500"}`}
      />
    </span>
  );
}

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

  const cameraOn = (status?.active_cameras ?? 0) > 0;
  const detectionOn = status?.running === true;
  const aiOn = status?.hailo_available === true;
  const arcfaceOn = status?.recognition_engine === "ArcFace";
  const engineLabel = arcfaceOn
    ? "InsightFace ArcFace (buffalo_sc) — deep learning recognition active, optimised for outdoor surveillance"
    : status?.recognition_engine === "HOG/LBP"
    ? "HOG/LBP fallback engine active — recognition accuracy is limited. Install InsightFace for better results."
    : "Recognition engine status unknown";

  const cameraLabel = cameraOn
    ? `${status!.active_cameras} camera${status!.active_cameras !== 1 ? "s" : ""} configured in config.ini`
    : "No cameras configured \u2014 add one in Settings \u2192 Cameras";
  const detectionLabel = detectionOn
    ? "Face detection app is running (seewhozthere service)"
    : "Face detection app is stopped \u2014 go to Settings \u2192 App Control to start it";
  const aiLabel = aiOn
    ? "Hailo AI HAT+ detected \u2014 hardware-accelerated face detection active"
    : "Hailo AI chip not detected \u2014 using software (OpenCV) detection";

  return (
    <>
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur-md shadow-sm">
        <div className="container flex h-16 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20 group-hover:bg-primary/15 transition-colors">
              <img src={logo} alt="SeeWhozThere\u00ae logo" className="h-6 w-6 object-contain" />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-[15px] font-extrabold tracking-tight">SeeWhozThere\u00ae</span>
              <span className="text-[10px] font-medium text-muted-foreground hidden sm:block tracking-wide uppercase">
                Smart Home Security
              </span>
            </div>
          </Link>

          <nav className="flex items-center gap-0.5">
            {/* Nav links */}
            {navItems.map((item) => (
              <Link key={item.path} to={item.path}>
                <Button
                  variant={location.pathname === item.path ? "secondary" : "ghost"}
                  size="sm"
                  className={
                    location.pathname === item.path
                      ? "font-semibold"
                      : "font-medium text-muted-foreground hover:text-foreground"
                  }
                >
                  {item.label}
                </Button>
              </Link>
            ))}

            {/* Add Known Visitor */}
            <Button
              variant="outline"
              size="sm"
              className="ml-2 hidden sm:flex items-center gap-1.5 border-primary/30 text-primary hover:bg-primary/5 hover:border-primary/50"
              onClick={() => setShowAddVisitor(true)}
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">Add Person</span>
            </Button>

            {/* Status indicators */}
            <TooltipProvider delayDuration={200}>
              <div className="flex items-center gap-2 ml-2 px-3 py-1.5 rounded-lg border bg-muted/40">
                {/* Camera */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 cursor-default">
                      <StatusDot on={cameraOn} />
                      <Camera className={`h-3.5 w-3.5 ${cameraOn ? "text-green-500" : "text-muted-foreground"}`} />
                      <span className={`text-[11px] font-semibold hidden md:inline ${cameraOn ? "text-green-600 dark:text-green-400" : "text-muted-foreground"}`}>
                        Cam
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs text-xs">
                    <p className="font-semibold mb-0.5">Camera Config</p>
                    <p>{cameraLabel}</p>
                  </TooltipContent>
                </Tooltip>

                <span className="w-px h-3.5 bg-border" />

                {/* Detection */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 cursor-default">
                      <StatusDot on={detectionOn} />
                      <Activity className={`h-3.5 w-3.5 ${detectionOn ? "text-green-500" : "text-red-500"}`} />
                      <span className={`text-[11px] font-semibold hidden md:inline ${detectionOn ? "text-green-600 dark:text-green-400" : "text-red-500"}`}>
                        {detectionOn ? "Live" : "Off"}
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs text-xs">
                    <p className="font-semibold mb-0.5">Detection App</p>
                    <p>{detectionLabel}</p>
                  </TooltipContent>
                </Tooltip>

                <span className="w-px h-3.5 bg-border" />

                {/* AI Engine (Hailo HAT+) */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 cursor-default">
                      <StatusDot on={aiOn} />
                      <Cpu className={`h-3.5 w-3.5 ${aiOn ? "text-purple-500" : "text-muted-foreground"}`} />
                      {aiOn && (
                        <Badge variant="outline" className="h-4 px-1 text-[9px] font-bold text-purple-500 border-purple-500/50 bg-purple-500/5">
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

                <span className="w-px h-3.5 bg-border" />

                {/* Recognition Engine */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 cursor-default">
                      <StatusDot on={arcfaceOn} />
                      <Brain className={`h-3.5 w-3.5 ${arcfaceOn ? "text-blue-500" : "text-amber-500"}`} />
                      <Badge
                        variant="outline"
                        className={`h-4 px-1 text-[9px] font-bold hidden md:inline-flex ${
                          arcfaceOn
                            ? "text-blue-500 border-blue-500/50 bg-blue-500/5"
                            : "text-amber-500 border-amber-500/50 bg-amber-500/5"
                        }`}
                      >
                        {arcfaceOn ? "ArcFace" : (status?.recognition_engine ?? "…")}
                      </Badge>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs text-xs">
                    <p className="font-semibold mb-0.5">Recognition Engine</p>
                    <p>{engineLabel}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </TooltipProvider>

            {/* Dark/Light toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={toggle}
              className="ml-1 text-muted-foreground hover:text-foreground"
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
