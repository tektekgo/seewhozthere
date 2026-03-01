import { Link, useLocation } from "react-router-dom";
import { Moon, Sun, Cpu, Wifi, WifiOff, UserPlus } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import logo from "@/assets/logo.png";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";

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

export function Navbar() {
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

  const isOnline = status?.running === true;
  const hasHailo = status?.hailo_available === true;

  return (
    <>
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

            {/* Add Known Visitor — quick access from anywhere */}
            <Button
              variant="outline"
              size="sm"
              className="ml-2 hidden sm:flex items-center gap-1.5"
              onClick={() => setShowAddVisitor(true)}
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span className="text-xs">Add Person</span>
            </Button>

            {/* System Status */}
            <div className="flex items-center gap-1.5 ml-2 px-2 py-1 rounded-md border bg-background/50">
              {isOnline ? (
                <Wifi className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <WifiOff className="h-3.5 w-3.5 text-red-500" />
              )}
              <span className={`text-xs font-medium ${isOnline ? "text-green-500" : "text-red-500"}`}>
                {isOnline ? "Online" : "Offline"}
              </span>
              {hasHailo && (
                <Badge variant="outline" className="h-4 px-1 text-[9px] font-bold text-purple-500 border-purple-500/50 ml-0.5">
                  <Cpu className="h-2.5 w-2.5 mr-0.5" />AI
                </Badge>
              )}
            </div>

            {/* Dark/Light toggle with accessible label */}
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
          </nav>
        </div>
      </header>

      <AddVisitorDialog open={showAddVisitor} onClose={() => setShowAddVisitor(false)} />
    </>
  );
}
