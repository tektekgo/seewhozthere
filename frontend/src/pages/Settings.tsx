import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getApiUrl, setApiUrl } from "@/lib/api";
import { toast } from "sonner";

const Settings = () => {
  const [url, setUrl] = useState(getApiUrl());

  const handleSave = () => {
    setApiUrl(url.trim());
    toast.success("API URL saved. Dashboard will use this endpoint.");
  };

  const handleClear = () => {
    setUrl("");
    setApiUrl("");
    toast.success("Cleared. Dashboard will use mock data.");
  };

  return (
    <main className="container py-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">Configure your SeeWhozThere dashboard</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            API Connection
            <Badge variant={getApiUrl() ? "default" : "secondary"}>
              {getApiUrl() ? "Live" : "Mock Data"}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">FastAPI Backend URL</label>
            <Input
              placeholder="http://raspberrypi.local:8000"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Leave blank to use mock/demo data. Enter your Pi's URL to connect to the live backend.
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleSave}>Save</Button>
            <Button variant="outline" onClick={handleClear}>Use Mock Data</Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
};

export default Settings;
