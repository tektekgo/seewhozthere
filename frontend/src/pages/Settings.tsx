import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { Camera, Plus, Trash2, Save, RefreshCw, Cpu, Wifi, WifiOff, Info } from "lucide-react";
import { toast } from "sonner";

interface CameraEntry {
  id: string;
  name: string;
  url: string;
}

interface SystemStatus {
  running: boolean;
  hailo_available: boolean;
  active_cameras: number;
  camera_names: string[];
  known_people: number;
  face_detector?: string;
}

const Settings = () => {
  const [cameras, setCameras] = useState<CameraEntry[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [camData, statusData] = await Promise.all([api.getCamerasConfig(), api.getStatus()]);
      const camArray: CameraEntry[] = Object.entries(camData.cameras || {}).map(
        ([name, url], idx) => ({ id: String(idx), name, url: url as string })
      );
      setCameras(camArray.length > 0 ? camArray : [{ id: "0", name: "", url: "" }]);
      setStatus(statusData);
    } catch { toast.error("Failed to load settings"); }
    finally { setLoading(false); }
  };

  const addCamera = () => setCameras(prev => [...prev, { id: String(Date.now()), name: "", url: "" }]);
  const removeCamera = (id: string) => setCameras(prev => prev.filter(c => c.id !== id));
  const updateCamera = (id: string, field: "name" | "url", value: string) =>
    setCameras(prev => prev.map(c => c.id === id ? { ...c, [field]: value } : c));

  const saveCameras = async () => {
    setSaving(true);
    try {
      const cameraObj: Record<string, string> = {};
      for (const cam of cameras) {
        if (cam.name.trim() && cam.url.trim()) cameraObj[cam.name.trim()] = cam.url.trim();
      }
      const result = await api.saveCamerasConfig(cameraObj);
      toast.success(result.message || "Cameras saved!");
    } catch { toast.error("Failed to save cameras"); }
    finally { setSaving(false); }
  };

  const refreshStatus = async () => {
    try { const s = await api.getStatus(); setStatus(s); toast.success("Status refreshed"); }
    catch { toast.error("Failed to refresh status"); }
  };

  return (
    <main className="container py-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">Configure cameras, system preferences, and view system info</p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2"><Info className="h-4 w-4" />System Status</CardTitle>
            <Button variant="ghost" size="sm" onClick={refreshStatus}><RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh</Button>
          </div>
        </CardHeader>
        <CardContent>
          {status ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Service</p>
                <div className="flex items-center gap-1.5">
                  {status.running
                    ? <><Wifi className="h-3.5 w-3.5 text-green-500" /><span className="text-sm font-medium text-green-500">Online</span></>
                    : <><WifiOff className="h-3.5 w-3.5 text-red-500" /><span className="text-sm font-medium text-red-500">Offline</span></>}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">AI Engine</p>
                <div className="flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-purple-500" />
                  <span className="text-sm font-medium">{status.hailo_available ? "Hailo AI" : "OpenCV"}</span>
                  {status.hailo_available && <Badge variant="outline" className="text-[9px] px-1 h-4 text-purple-500 border-purple-500/50">HAT+</Badge>}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Active Cameras</p>
                <p className="text-sm font-medium">{status.active_cameras}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Known People</p>
                <p className="text-sm font-medium">{status.known_people}</p>
              </div>
            </div>
          ) : <p className="text-sm text-muted-foreground">Loading status...</p>}
          {status && !status.running && (
            <div className="mt-3 p-3 rounded-md bg-amber-500/10 border border-amber-500/20 text-xs text-amber-600 dark:text-amber-400">
              <strong>Detection service is not running.</strong> Start it with:{" "}
              <code className="font-mono bg-amber-500/10 px-1 rounded">python3 run_service.py</code>
              {" "}or{" "}
              <code className="font-mono bg-amber-500/10 px-1 rounded">sudo systemctl start seewhozthere</code>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2"><Camera className="h-4 w-4" />Camera Configuration</CardTitle>
          <CardDescription className="text-xs">
            Add your RTSP camera streams. Format: <code className="bg-muted px-1 rounded">rtsp://username:password@ip:port/stream</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? <p className="text-sm text-muted-foreground">Loading cameras...</p> : (
            <>
              {cameras.map((cam, idx) => (
                <div key={cam.id} className="flex gap-2 items-center">
                  <span className="w-5 text-xs text-muted-foreground font-mono shrink-0">{idx + 1}</span>
                  <Input placeholder="Name (e.g. front_door)" value={cam.name}
                    onChange={e => updateCamera(cam.id, "name", e.target.value)} className="w-36 shrink-0 text-sm" />
                  <Input placeholder="rtsp://user:pass@192.168.1.100:554/stream1" value={cam.url}
                    onChange={e => updateCamera(cam.id, "url", e.target.value)} className="flex-1 text-xs font-mono" />
                  <Button variant="ghost" size="icon" onClick={() => removeCamera(cam.id)}
                    className="shrink-0 text-muted-foreground hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <div className="flex gap-2 pt-1">
                <Button variant="outline" size="sm" onClick={addCamera}><Plus className="h-3.5 w-3.5 mr-1" />Add Camera</Button>
                <Button size="sm" onClick={saveCameras} disabled={saving}>
                  <Save className="h-3.5 w-3.5 mr-1" />{saving ? "Saving..." : "Save Cameras"}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">After saving, restart the detection service for changes to take effect.</p>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-dashed border-primary/30 bg-primary/5">
        <CardContent className="pt-4 pb-4">
          <p className="text-xs font-semibold text-primary mb-1">💡 Your Tapo Camera RTSP URL</p>
          <code className="text-xs font-mono text-muted-foreground break-all">rtsp://username:password@192.168.9.130:554/stream1</code>
          <p className="text-xs text-muted-foreground mt-1">
            Replace <strong>username</strong> and <strong>password</strong> with your Tapo camera credentials (set in the Tapo app).
          </p>
        </CardContent>
      </Card>
    </main>
  );
};

export default Settings;
