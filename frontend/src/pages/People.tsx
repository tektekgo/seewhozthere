import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { api, getApiUrl } from "@/lib/api";
import { toast } from "sonner";
import {
  Users,
  UserPlus,
  Trash2,
  Upload,
  Search,
  Eye,
  RefreshCw,
  Camera,
  CheckCircle2,
  XCircle,
  CalendarDays,
  RotateCcw,
  ShieldAlert,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Visitor {
  id: number;
  name: string;
  thumbnail_path: string | null;
  created_at: string | null;
  has_encoding: boolean;
  sighting_count: number;
  last_seen: string | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function thumbnailUrl(path: string | null): string | null {
  if (!path) return null;
  const base = getApiUrl();
  // path is like "data/thumbnails/foo.jpg" — prefix with /
  return `${base}/${path}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function formatRelative(iso: string | null): string {
  if (!iso) return "Never";
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return formatDate(iso);
  } catch {
    return iso;
  }
}

// ─── Avatar ───────────────────────────────────────────────────────────────────
function Avatar({ visitor, size = 56 }: { visitor: Visitor; size?: number }) {
  const url = thumbnailUrl(visitor.thumbnail_path);
  const initials = visitor.name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  if (url) {
    return (
      <img
        src={url}
        alt={visitor.name}
        width={size}
        height={size}
        className="rounded-full object-cover border border-border shrink-0"
        style={{ width: size, height: size }}
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
        }}
      />
    );
  }
  return (
    <div
      className="rounded-full bg-muted flex items-center justify-center border border-border shrink-0 text-muted-foreground font-semibold"
      style={{ width: size, height: size, fontSize: size * 0.35 }}
    >
      {initials || "?"}
    </div>
  );
}

// ─── Add / Edit Visitor Dialog ────────────────────────────────────────────────
function VisitorFormDialog({
  open,
  onClose,
  onSaved,
  existing,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  existing?: Visitor | null;
}) {
  const [name, setName] = useState(existing?.name ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Reset when dialog opens
  useEffect(() => {
    if (open) {
      setName(existing?.name ?? "");
      setPhoto(null);
    }
  }, [open, existing]);

  const isEdit = !!existing;

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (isEdit && existing) {
        // Update via PUT
        const baseUrl = getApiUrl();
        const form = new FormData();
        form.append("name", name.trim());
        if (photo) form.append("photo", photo);
        const res = await fetch(`${baseUrl}/api/visitors/${existing.id}`, {
          method: "PUT",
          body: form,
        });
        const data = await res.json();
        if (data.success) {
          toast.success(`${name.trim()} updated`);
          onSaved();
          onClose();
        } else {
          toast.error(data.detail ?? "Failed to update visitor");
        }
      } else {
        // Add new via POST (upsert — server handles duplicates gracefully)
        const res = await api.addVisitor(name.trim(), photo ?? undefined);
        if (res.id || res.visitor_id) {
          toast.success(`${name.trim()} added`);
          onSaved();
          onClose();
        } else {
          toast.error(res.detail ?? "Failed to add visitor");
        }
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
          <DialogTitle>{isEdit ? "Edit Visitor" : "Add Known Visitor"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update the name or reference photo for this person."
              : "Register a person so the system can recognise them in future detections."}
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
              <span className="text-muted-foreground font-normal">
                (optional — improves recognition)
              </span>
            </label>
            {isEdit && existing?.thumbnail_path && (
              <div className="mb-2 flex items-center gap-2">
                <Avatar visitor={existing} size={40} />
                <span className="text-xs text-muted-foreground">Current photo</span>
              </div>
            )}
            <Input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
            />
            {photo && (
              <p className="text-xs text-muted-foreground mt-1">
                Selected: {photo.name} ({(photo.size / 1024).toFixed(0)} KB)
              </p>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? (isEdit ? "Saving…" : "Adding…") : isEdit ? "Save Changes" : "Add Visitor"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Delete Confirm Dialog ────────────────────────────────────────────────────
function DeleteConfirmDialog({
  visitor,
  onClose,
  onDeleted,
}: {
  visitor: Visitor | null;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!visitor) return;
    setDeleting(true);
    try {
      const res = await api.deleteVisitor(visitor.id);
      if (res.success) {
        toast.success(`Removed ${visitor.name}`);
        onDeleted();
        onClose();
      } else {
        toast.error(res.detail ?? "Failed to delete visitor");
      }
    } catch {
      toast.error("An error occurred");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AlertDialog open={!!visitor} onOpenChange={onClose}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove {visitor?.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            This will permanently delete <strong>{visitor?.name}</strong> from the known visitors
            list. Their {visitor?.sighting_count ?? 0} sighting record(s) will also be removed.
            This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={deleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleting ? "Removing…" : "Remove"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// ─── Visitor Card ─────────────────────────────────────────────────────────────
function VisitorCard({
  visitor,
  onEdit,
  onDelete,
  onReset,
}: {
  visitor: Visitor;
  onEdit: (v: Visitor) => void;
  onDelete: (v: Visitor) => void;
  onReset: (v: Visitor) => void;
}) {
  return (
    <Card className="flex flex-col gap-0 overflow-hidden hover:shadow-md transition-shadow">
      <CardContent className="p-4 flex gap-3 items-start">
        <Avatar visitor={visitor} size={56} />
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-1">
            <p className="font-semibold text-sm truncate">{visitor.name}</p>
            <div className="flex gap-1 shrink-0">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                title="Edit / Re-enroll photo"
                onClick={() => onEdit(visitor)}
              >
                <Upload className="h-3.5 w-3.5" />
              </Button>
              {visitor.has_encoding && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-amber-600 hover:text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-950/30"
                  title="Reset face data — clears polluted encoding so they can be re-enrolled cleanly"
                  onClick={() => onReset(visitor)}
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:text-destructive"
                title="Remove visitor"
                onClick={() => onDelete(visitor)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5 mt-1.5">
            <Badge
              variant={visitor.has_encoding ? "default" : "secondary"}
              className="text-[10px] h-4 px-1.5 gap-0.5"
            >
              {visitor.has_encoding ? (
                <CheckCircle2 className="h-2.5 w-2.5" />
              ) : (
                <XCircle className="h-2.5 w-2.5" />
              )}
              {visitor.has_encoding ? "Trained" : "No encoding"}
            </Badge>
            <Badge variant="outline" className="text-[10px] h-4 px-1.5 gap-0.5">
              <Camera className="h-2.5 w-2.5" />
              {visitor.sighting_count} sighting{visitor.sighting_count !== 1 ? "s" : ""}
            </Badge>
          </div>

          <div className="mt-1.5 space-y-0.5">
            <p className="text-[11px] text-muted-foreground flex items-center gap-1">
              <CalendarDays className="h-3 w-3" />
              Added {formatDate(visitor.created_at)}
            </p>
            {visitor.last_seen && (
              <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                <Eye className="h-3 w-3" />
                Last seen {formatRelative(visitor.last_seen)}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function People() {
  const [visitors, setVisitors] = useState<Visitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Visitor | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Visitor | null>(null);
  const [resetTarget, setResetTarget] = useState<Visitor | null>(null);
  const [resetting, setResetting] = useState(false);
  const [showResetAll, setShowResetAll] = useState(false);
  const [resettingAll, setResettingAll] = useState(false);

  const loadVisitors = async () => {
    setLoading(true);
    try {
      const data = await api.getVisitors();
      setVisitors(data.visitors ?? []);
    } catch {
      toast.error("Failed to load visitors");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!resetTarget) return;
    setResetting(true);
    try {
      const res = await api.resetVisitorEncoding(resetTarget.id);
      if (res.success) {
        toast.success(`Face data cleared for ${resetTarget.name}. They will appear as Unknown until re-enrolled.`);
        loadVisitors();
      } else {
        toast.error("Failed to reset face data");
      }
    } catch {
      toast.error("Failed to reset face data");
    } finally {
      setResetting(false);
      setResetTarget(null);
    }
  };

  const handleResetAll = async () => {
    setResettingAll(true);
    try {
      const res = await api.resetAllEncodings();
      if (res.success) {
        toast.success(res.message ?? "All face encodings cleared. Re-enrol each person by walking past the camera.");
        loadVisitors();
      } else {
        toast.error(res.detail ?? "Failed to reset all encodings");
      }
    } catch {
      toast.error("Failed to reset all encodings");
    } finally {
      setResettingAll(false);
      setShowResetAll(false);
    }
  };
  useEffect(() => {
    loadVisitors();
  }, []);

  const filtered = visitors.filter((v) =>
    v.name.toLowerCase().includes(search.toLowerCase())
  );

  const trainedCount = visitors.filter((v) => v.has_encoding).length;
  const totalSightings = visitors.reduce((s, v) => s + v.sighting_count, 0);

  return (
    <div className="container mx-auto px-4 py-6 max-w-5xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="h-6 w-6" />
            Known People
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage registered visitors and their face recognition profiles.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={loadVisitors} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowResetAll(true)}
            disabled={visitors.length === 0}
            className="border-amber-500 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950"
            title="Clear all face encodings for everyone — use when the recognition database has been contaminated by false positives"
          >
            <ShieldAlert className="h-3.5 w-3.5 mr-1.5" />
            Reset All Encodings
          </Button>
          <Button size="sm" onClick={() => setShowAdd(true)}>
            <UserPlus className="h-3.5 w-3.5 mr-1.5" />
            Add Person
          </Button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold">{visitors.length}</p>
            <p className="text-xs text-muted-foreground">Registered</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-green-500">{trainedCount}</p>
            <p className="text-xs text-muted-foreground">Trained</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold">{totalSightings}</p>
            <p className="text-xs text-muted-foreground">Total Sightings</p>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search by name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Grid */}
      {loading ? (
        <div className="text-center py-16 text-muted-foreground">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-3 opacity-50" />
          <p>Loading…</p>
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Users className="h-12 w-12 mx-auto mb-3 text-muted-foreground opacity-40" />
            {search ? (
              <>
                <p className="font-medium">No results for "{search}"</p>
                <p className="text-sm text-muted-foreground mt-1">Try a different name.</p>
              </>
            ) : (
              <>
                <p className="font-medium">No known visitors yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Add someone to start recognising them in detections.
                </p>
                <Button className="mt-4" onClick={() => setShowAdd(true)}>
                  <UserPlus className="h-4 w-4 mr-2" />
                  Add First Person
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((v) => (
            <VisitorCard
              key={v.id}
              visitor={v}
              onEdit={setEditTarget}
              onDelete={setDeleteTarget}
              onReset={setResetTarget}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      <VisitorFormDialog
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onSaved={loadVisitors}
      />
      <VisitorFormDialog
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        onSaved={loadVisitors}
        existing={editTarget}
      />
      <DeleteConfirmDialog
        visitor={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onDeleted={loadVisitors}
      />
      {/* Reset ALL Face Encodings confirmation dialog */}
      <AlertDialog open={showResetAll} onOpenChange={(o) => { if (!o) setShowResetAll(false); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-500" />
              Reset All Face Encodings?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will clear <strong>all stored face recognition data</strong> for every person
              ({visitors.length} visitor{visitors.length !== 1 ? "s" : ""}).
              <br /><br />
              Use this when the recognition database has been contaminated by false positives
              (birds, shadows, or objects that were accidentally labelled as people).
              <br /><br />
              <strong>Everyone will appear as Unknown</strong> until you re-enrol them by walking
              past the camera and identifying them via Telegram or the History page.
              Visitor names and sighting history are not affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={resettingAll}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleResetAll}
              disabled={resettingAll}
              className="bg-amber-600 hover:bg-amber-700 text-white"
            >
              {resettingAll ? "Resetting…" : "Reset All Face Data"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reset Face Data confirmation dialog (per-person) */}
      <AlertDialog open={!!resetTarget} onOpenChange={(o) => { if (!o) setResetTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset Face Data for {resetTarget?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will clear all stored face encodings for <strong>{resetTarget?.name}</strong>.
              They will appear as <em>Unknown</em> in future detections until a clean encoding is
              captured from a new correct identification. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={resetting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReset}
              disabled={resetting}
              className="bg-amber-600 hover:bg-amber-700 text-white"
            >
              {resetting ? "Resetting…" : "Reset Face Data"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
