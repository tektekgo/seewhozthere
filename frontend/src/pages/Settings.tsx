import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import {
  Camera, Plus, Trash2, Save, RefreshCw, Cpu, Wifi, WifiOff,
  Info, Play, Square, RotateCcw, Terminal, CheckCircle2, XCircle,
  Settings2, Shield
} from "lucide-react";
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

interface ServiceStatus {
  active: boolean;
  installed: boolean;
  status: string;
}

const Settings = () => {
  const [cameras, setCameras] = useState<CameraEntry[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [serviceLoading, setServiceLoading] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [camData, statusData, svcData] = await Promise.all([
        api.getCamerasConfig(),
        api.getStatus(),
        api.getServiceStatus(),
      ]);
      const camArray: CameraEntry[] = Object.entries(camData.cameras || {}).map(
        ([name, url], idx) => ({ id: String(idx), name, url: url as string })
      );
      setCameras(camArray.length > 0 ? camArray : [{ id: "0", name: "", url: "" }]);
      setStatus(statusData);
      setServiceStatus(svcData);
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
    try {
      const [s, svc] = await Promise.all([api.getStatus(), api.getServiceStatus()]);
      setStatus(s);
      setServiceStatus(svc);
      toast.success("Status refreshed");
    } catch { toast.error("Failed to refresh status"); }
  };

  const handleServiceAction = async (action: "start" | "stop" | "restart") => {
    setServiceLoading(true);
    try {
      const result = await api.serviceAction(action);
      if (result.success) {
        toast.success(`Service ${action} succeeded`);
        // Refresh status after a short delay
        setTimeout(async () => {
          const svc = await api.getServiceStatus();
          setServiceStatus(svc);
          const s = await api.getStatus();
          setStatus(s);
        }, 2000);
      } else {
        toast.error(result.message || `Service ${action} failed`);
      }
    } catch { toast.error(`Failed to ${action} service`); }
    finally { setServiceLoading(false); }
  };

  return (
    <main className="container py-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">Configure cameras, manage services, and view system information</p>
      </div>

      {/* System Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Info className="h-4 w-4" />System Status
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={refreshStatus}>
              <RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {status ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Detection App</p>
                <div className="flex items-center gap-1.5">
                  {status.running
                    ? <><Wifi className="h-3.5 w-3.5 text-green-500" /><span className="text-sm font-medium text-green-500">Running</span></>
                    : <><WifiOff className="h-3.5 w-3.5 text-red-500" /><span className="text-sm font-medium text-red-500">Stopped</span></>}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">AI Engine</p>
                <div className="flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-purple-500" />
                  <span className="text-sm font-medium">{status.hailo_available ? "Hailo AI" : "OpenCV"}</span>
                  {status.hailo_available && (
                    <Badge variant="outline" className="text-[9px] px-1 h-4 text-purple-500 border-purple-500/50">HAT+</Badge>
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Cameras Configured</p>
                <p className="text-sm font-medium">{status.active_cameras}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Known People</p>
                <p className="text-sm font-medium">{status.known_people}</p>
              </div>
            </div>
          ) : <p className="text-sm text-muted-foreground">Loading status...</p>}
        </CardContent>
      </Card>

      <Tabs defaultValue="cameras">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="cameras" className="flex items-center gap-1.5">
            <Camera className="h-3.5 w-3.5" />Cameras
          </TabsTrigger>
          <TabsTrigger value="service" className="flex items-center gap-1.5">
            <Terminal className="h-3.5 w-3.5" />App Control
          </TabsTrigger>
          <TabsTrigger value="about" className="flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5" />About
          </TabsTrigger>
        </TabsList>

        {/* Cameras Tab */}
        <TabsContent value="cameras" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Camera className="h-4 w-4" />Camera Configuration
              </CardTitle>
              <CardDescription className="text-xs">
                Add your RTSP camera streams. Format:{" "}
                <code className="bg-muted px-1 rounded">rtsp://username:password@ip:port/stream</code>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading ? <p className="text-sm text-muted-foreground">Loading cameras...</p> : (
                <>
                  {cameras.map((cam, idx) => (
                    <div key={cam.id} className="flex gap-2 items-center">
                      <span className="w-5 text-xs text-muted-foreground font-mono shrink-0">{idx + 1}</span>
                      <Input
                        placeholder="Name (e.g. front_door)"
                        value={cam.name}
                        onChange={e => updateCamera(cam.id, "name", e.target.value)}
                        className="w-36 shrink-0 text-sm"
                      />
                      <Input
                        placeholder="rtsp://user:pass@192.168.1.100:554/stream1"
                        value={cam.url}
                        onChange={e => updateCamera(cam.id, "url", e.target.value)}
                        className="flex-1 text-xs font-mono"
                      />
                      <Button
                        variant="ghost" size="icon"
                        onClick={() => removeCamera(cam.id)}
                        className="shrink-0 text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <div className="flex gap-2 pt-1">
                    <Button variant="outline" size="sm" onClick={addCamera}>
                      <Plus className="h-3.5 w-3.5 mr-1" />Add Camera
                    </Button>
                    <Button size="sm" onClick={saveCameras} disabled={saving}>
                      <Save className="h-3.5 w-3.5 mr-1" />{saving ? "Saving..." : "Save Cameras"}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    After saving, restart the detection service for changes to take effect.
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card className="border-dashed border-primary/30 bg-primary/5">
            <CardContent className="pt-4 pb-4">
              <p className="text-xs font-semibold text-primary mb-1">💡 Your Tapo Camera RTSP URL</p>
              <code className="text-xs font-mono text-muted-foreground break-all">
                rtsp://username:password@192.168.9.130:554/stream1
              </code>
              <p className="text-xs text-muted-foreground mt-1">
                Replace <strong>username</strong> and <strong>password</strong> with your Tapo camera credentials (set in the Tapo app).
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Service Management Tab */}
        <TabsContent value="service" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Terminal className="h-4 w-4" />Detection App Control
              </CardTitle>
              <CardDescription className="text-xs">
                Start, stop, or restart the face detection app. It runs as a background service (systemd unit: <code className="bg-muted px-1 rounded">seewhozthere</code>). Install it first via <code className="bg-muted px-1 rounded">./install_service.sh</code>.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Service Status */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">Detection App</p>
                  <p className="text-xs text-muted-foreground">seewhozthere (systemd service)</p>
                </div>
                <div className="flex items-center gap-2">
                  {serviceStatus ? (
                    <>
                      {serviceStatus.installed ? (
                        serviceStatus.active
                          ? <><CheckCircle2 className="h-4 w-4 text-green-500" /><Badge className="bg-green-500/10 text-green-600 border-green-500/30 text-xs">Active</Badge></>
                          : <><XCircle className="h-4 w-4 text-red-500" /><Badge variant="outline" className="text-red-500 border-red-500/30 text-xs">Stopped</Badge></>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground text-xs">Not Installed</Badge>
                      )}
                    </>
                  ) : (
                    <Badge variant="outline" className="text-xs">Checking...</Badge>
                  )}
                </div>
              </div>

              {/* Service Control Buttons */}
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm" variant="outline"
                  onClick={() => handleServiceAction("start")}
                  disabled={serviceLoading || serviceStatus?.active}
                  className="text-green-600 border-green-500/30 hover:bg-green-500/10"
                >
                  <Play className="h-3.5 w-3.5 mr-1" />Start
                </Button>
                <Button
                  size="sm" variant="outline"
                  onClick={() => handleServiceAction("stop")}
                  disabled={serviceLoading || !serviceStatus?.active}
                  className="text-red-600 border-red-500/30 hover:bg-red-500/10"
                >
                  <Square className="h-3.5 w-3.5 mr-1" />Stop
                </Button>
                <Button
                  size="sm" variant="outline"
                  onClick={() => handleServiceAction("restart")}
                  disabled={serviceLoading}
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-1" />Restart
                </Button>
                <Button
                  size="sm" variant="ghost"
                  onClick={refreshStatus}
                  disabled={serviceLoading}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh
                </Button>
              </div>

              {/* Install instructions if not installed */}
              {serviceStatus && !serviceStatus.installed && (
                <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/20 text-xs text-amber-600 dark:text-amber-400 space-y-1">
                  <p className="font-semibold">Service not installed. To install:</p>
                  <code className="block font-mono bg-black/10 dark:bg-white/10 px-2 py-1 rounded">
                    cd ~/projects/seewhozthere && sudo ./install_service.sh
                  </code>
                  <p>Or run manually without systemd:</p>
                  <code className="block font-mono bg-black/10 dark:bg-white/10 px-2 py-1 rounded">
                    python3 run_service.py
                  </code>
                </div>
              )}

              {/* Manual run instructions */}
              <div className="p-3 rounded-md bg-muted border text-xs space-y-2">
                <p className="font-semibold flex items-center gap-1"><Settings2 className="h-3.5 w-3.5" />Quick Reference</p>
                <div className="space-y-1 font-mono text-muted-foreground">
                  <p><span className="text-foreground">Install:</span> sudo ./install_service.sh</p>
                  <p><span className="text-foreground">Start:</span> sudo systemctl start seewhozthere</p>
                  <p><span className="text-foreground">Stop:</span> sudo systemctl stop seewhozthere</p>
                  <p><span className="text-foreground">Logs:</span> sudo journalctl -u seewhozthere -f</p>
                  <p><span className="text-foreground">Manual:</span> python3 run_service.py</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* About Tab */}
        <TabsContent value="about" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="h-4 w-4" />About SeeWhozThere
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">Product</p>
                  <p className="font-medium">SeeWhozThere</p>
                </div>
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">Built by</p>
                  <p className="font-medium">Sujit G · Techsilon</p>
                </div>
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">AI Hardware</p>
                  <p className="font-medium flex items-center gap-1">
                    <Cpu className="h-3.5 w-3.5 text-purple-500" />Hailo AI HAT+
                  </p>
                </div>
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">Platform</p>
                  <p className="font-medium">Raspberry Pi 5</p>
                </div>
              </div>

              <div className="p-3 rounded-md bg-muted border text-xs space-y-1">
                <p className="font-semibold">Stack</p>
                <p className="text-muted-foreground">FastAPI · React · TypeScript · Shadcn/UI · Recharts · SQLite · Hailo SDK</p>
              </div>

              <div className="p-3 rounded-md bg-muted border text-xs space-y-1">
                <p className="font-semibold">Source Code</p>
                <a
                  href="https://github.com/tektekgo/seewhozthere"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline font-mono"
                >
                  github.com/tektekgo/seewhozthere
                </a>
              </div>

              <div className="p-3 rounded-md bg-primary/5 border border-primary/20 text-xs">
                <p className="font-semibold text-primary mb-1">⚠️ Dependency Note</p>
                <p className="text-muted-foreground">
                  Hailo SDK requires <code className="bg-muted px-0.5 rounded">numpy&lt;2</code> and{" "}
                  <code className="bg-muted px-0.5 rounded">opencv==4.8.1.78</code>. Never upgrade these without
                  checking Hailo SDK compatibility. See <code className="bg-muted px-0.5 rounded">docs/DEPENDENCY_NOTES.md</code>.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </main>
  );
};

export default Settings;
