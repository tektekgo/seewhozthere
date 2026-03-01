import { useEffect, useState, useCallback } from "react";
import {
  Search, UserCheck, UserX, Camera, Clock, Calendar,
  Plus, Tag, Trash2, RefreshCw, CheckSquare, Square,
  CheckCheck, X, Users,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { api } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Sighting {
  id: number;
  camera_name: string;
  timestamp: string | null;
  snapshot_url: string | null;
  visitor_id?: number | null;
  visitor_name?: string | null;
}

interface KnownVisitor {
  id: number;
  name: string;
  thumbnail_path?: string | null;
}

type Filter = "all" | "unknown" | "known";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string | null): { date: string; time: string } {
  if (!iso) return { date: "Unknown date", time: "" };
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString(undefined, {
      weekday: "short", year: "numeric", month: "short", day: "numeric",
    }),
    time: d.toLocaleTimeString(undefined, {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    }),
  };
}

// ─── Name Dialog (single or bulk) ─────────────────────────────────────────────

interface NameDialogProps {
  sightingIds: number[];           // 1 = single, >1 = bulk
  previewSighting?: Sighting;      // show thumbnail for single
  knownVisitors: KnownVisitor[];
  onClose: () => void;
  onNamed: (ids: number[], visitorName: string) => void;
}

function NameDialog({ sightingIds, previewSighting, knownVisitors, onClose, onNamed }: NameDialogProps) {
  const [mode, setMode] = useState<"select" | "new">("select");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [newName, setNewName] = useState("");
  const [newPhoto, setNewPhoto] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const isBulk = sightingIds.length > 1;

  const handleSave = async () => {
    setSaving(true);
    try {
      let visitorId: number | null = null;
      let visitorName = "";

      if (mode === "select" && selectedId !== null) {
        visitorId = selectedId;
        visitorName = knownVisitors.find((v) => v.id === selectedId)?.name ?? "Known";
      } else if (mode === "new" && newName.trim()) {
        const addRes = await api.addVisitor(newName.trim(), newPhoto ?? undefined);
        if (!addRes.id) {
          toast.error(addRes.detail ?? "Failed to add visitor");
          setSaving(false);
          return;
        }
        visitorId = addRes.id;
        visitorName = newName.trim();
      } else {
        setSaving(false);
        return;
      }

      // Identify each selected sighting
      const results = await Promise.allSettled(
        sightingIds.map((id) => api.identifySighting(id, visitorId!))
      );
      const succeeded = results.filter((r) => r.status === "fulfilled").length;

      if (succeeded === sightingIds.length) {
        toast.success(
          isBulk
            ? `${succeeded} detections identified as ${visitorName}`
            : `Identified as ${visitorName}`
        );
      } else {
        toast.warning(`${succeeded} of ${sightingIds.length} identified as ${visitorName}`);
      }

      onNamed(sightingIds, visitorName);
    } catch {
      toast.error("An error occurred");
    } finally {
      setSaving(false);
      onClose();
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isBulk ? `Name ${sightingIds.length} Selected Detections` : "Name This Person"}</DialogTitle>
          <DialogDescription>
            {isBulk
              ? `All ${sightingIds.length} selected detections will be assigned to the same person.`
              : "Assign an identity so future appearances are recognised automatically."}
          </DialogDescription>
        </DialogHeader>

        {/* Single sighting preview */}
        {!isBulk && previewSighting?.snapshot_url && (
          <div className="flex justify-center">
            <img
              src={previewSighting.snapshot_url}
              alt="Detected face"
              className="h-32 w-32 rounded-lg object-cover border-2 border-border shadow"
            />
          </div>
        )}

        {/* Bulk preview strip */}
        {isBulk && (
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {sightingIds.slice(0, 8).map((id) => {
              const s = previewSighting; // we pass the first one; grid handles the rest
              return (
                <div key={id} className="shrink-0 h-14 w-14 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground border">
                  #{id}
                </div>
              );
            })}
            {sightingIds.length > 8 && (
              <div className="shrink-0 h-14 w-14 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground border">
                +{sightingIds.length - 8}
              </div>
            )}
          </div>
        )}

        {/* Mode toggle */}
        <div className="flex gap-2">
          <Button variant={mode === "select" ? "default" : "outline"} size="sm" className="flex-1" onClick={() => setMode("select")}>
            <UserCheck className="h-3.5 w-3.5 mr-1.5" />Existing Person
          </Button>
          <Button variant={mode === "new" ? "default" : "outline"} size="sm" className="flex-1" onClick={() => setMode("new")}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />New Person
          </Button>
        </div>

        {mode === "select" ? (
          <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
            {knownVisitors.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No known visitors yet. Switch to "New Person".
              </p>
            ) : (
              knownVisitors.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setSelectedId(v.id)}
                  className={`w-full flex items-center gap-3 p-2.5 rounded-lg border text-left transition-colors ${
                    selectedId === v.id
                      ? "border-primary bg-primary/10"
                      : "border-border hover:bg-muted"
                  }`}
                >
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary shrink-0">
                    {v.name[0].toUpperCase()}
                  </div>
                  <span className="text-sm font-medium">{v.name}</span>
                </button>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Full name</label>
              <Input
                placeholder="e.g. John Smith"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSave()}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">
                Reference photo{" "}
                <span className="text-muted-foreground font-normal">(optional — improves recognition)</span>
              </label>
              <Input type="file" accept="image/*" onChange={(e) => setNewPhoto(e.target.files?.[0] ?? null)} />
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button
            onClick={handleSave}
            disabled={
              saving ||
              (mode === "select" && selectedId === null) ||
              (mode === "new" && !newName.trim())
            }
          >
            {saving ? "Saving…" : isBulk ? `Identify ${sightingIds.length} Detections` : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Add Visitor Dialog ────────────────────────────────────────────────────────

function AddVisitorDialog({
  open, onClose, onAdded,
}: { open: boolean; onClose: () => void; onAdded: () => void }) {
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
        onAdded(); onClose();
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
          <DialogDescription>Register a person so the system can recognise them in future detections.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium mb-1 block">Full name</label>
            <Input placeholder="e.g. Jane Doe" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSave()} />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Reference photo <span className="text-muted-foreground font-normal">(optional)</span></label>
            <Input type="file" accept="image/*" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>{saving ? "Adding…" : "Add Visitor"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Sighting Card ─────────────────────────────────────────────────────────────

interface SightingCardProps {
  sighting: Sighting;
  selected: boolean;
  selectionMode: boolean;
  onToggleSelect: (id: number) => void;
  onName: (s: Sighting) => void;
  onDelete: (id: number) => void;
}

function SightingCard({ sighting, selected, selectionMode, onToggleSelect, onName, onDelete }: SightingCardProps) {
  const { date, time } = formatDateTime(sighting.timestamp);
  const isKnown = !!sighting.visitor_name;

  return (
    <Card
      className={`overflow-hidden transition-all cursor-pointer group ${
        selected
          ? "ring-2 ring-primary shadow-md"
          : "hover:shadow-md hover:border-primary/30"
      }`}
      onClick={() => onToggleSelect(sighting.id)}
    >
      <CardContent className="p-0">
        <div className="flex">
          {/* Thumbnail */}
          <div className="shrink-0 w-28 h-28 bg-muted relative">
            {sighting.snapshot_url ? (
              <img
                src={sighting.snapshot_url}
                alt={sighting.visitor_name ?? "Unknown person"}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <UserX className="h-10 w-10 text-muted-foreground/40" />
              </div>
            )}

            {/* Selection checkbox overlay */}
            <div
              className={`absolute top-1.5 left-1.5 transition-opacity ${
                selectionMode || selected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
              }`}
            >
              <div
                className={`h-5 w-5 rounded border-2 flex items-center justify-center ${
                  selected
                    ? "bg-primary border-primary text-primary-foreground"
                    : "bg-background/80 border-border"
                }`}
              >
                {selected && <CheckCheck className="h-3 w-3" />}
              </div>
            </div>

            {/* Known/Unknown badge */}
            <div className="absolute bottom-1 left-1">
              <Badge
                variant={isKnown ? "default" : "secondary"}
                className={`text-[9px] px-1 py-0 ${isKnown ? "" : "bg-amber-500/80 text-white border-0"}`}
              >
                {isKnown ? "Known" : "Unknown"}
              </Badge>
            </div>
          </div>

          {/* Info */}
          <div className="flex-1 p-3 flex flex-col justify-between min-w-0">
            <div>
              <p className="font-semibold text-sm truncate">
                {sighting.visitor_name ?? "Unknown Person"}
              </p>
              <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                <Calendar className="h-3 w-3 shrink-0" /><span>{date}</span>
              </div>
              <div className="flex items-center gap-1 mt-0.5 text-xs text-muted-foreground">
                <Clock className="h-3 w-3 shrink-0" /><span>{time}</span>
              </div>
              <div className="flex items-center gap-1 mt-0.5 text-xs text-muted-foreground">
                <Camera className="h-3 w-3 shrink-0" />
                <span className="truncate capitalize">
                  {sighting.camera_name?.replace(/_/g, " ") ?? "Unknown camera"}
                </span>
              </div>
            </div>
            <div className="flex gap-1.5 mt-2" onClick={(e) => e.stopPropagation()}>
              {!isKnown && (
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs flex-1"
                  onClick={() => onName(sighting)}
                >
                  <Tag className="h-3 w-3 mr-1" />Name
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => onDelete(sighting.id)}
                title="Delete sighting"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

const History = () => {
  const [sightings, setSightings] = useState<Sighting[]>([]);
  const [knownVisitors, setKnownVisitors] = useState<KnownVisitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");

  // Single-item dialogs
  const [namingSighting, setNamingSighting] = useState<Sighting | null>(null);
  const [showAddVisitor, setShowAddVisitor] = useState(false);

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [showBulkNameDialog, setShowBulkNameDialog] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // ── Data loading ──────────────────────────────────────────────────────────

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sightingsRes, visitorsRes] = await Promise.all([
        api.getAllSightings(500),
        api.getVisitors(),
      ]);
      setSightings(sightingsRes.sightings ?? []);
      setKnownVisitors(visitorsRes.visitors ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // ── Filtering ─────────────────────────────────────────────────────────────

  const filtered = sightings.filter((s) => {
    const isKnown = !!s.visitor_name;
    if (filter === "known" && !isKnown) return false;
    if (filter === "unknown" && isKnown) return false;
    if (search) {
      const q = search.toLowerCase();
      if (
        !(s.visitor_name ?? "unknown").toLowerCase().includes(q) &&
        !(s.camera_name ?? "").toLowerCase().includes(q)
      ) return false;
    }
    return true;
  });

  const knownCount = sightings.filter((s) => !!s.visitor_name).length;
  const unknownCount = sightings.filter((s) => !s.visitor_name).length;

  // ── Selection helpers ─────────────────────────────────────────────────────

  const selectionMode = selectedIds.size > 0;

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(filtered.map((s) => s.id)));
  };

  const clearSelection = () => setSelectedIds(new Set());

  const selectedUnknownIds = filtered
    .filter((s) => selectedIds.has(s.id) && !s.visitor_name)
    .map((s) => s.id);

  // ── Actions ───────────────────────────────────────────────────────────────

  const handleNamed = (ids: number[], visitorName: string) => {
    setSightings((prev) =>
      prev.map((s) => ids.includes(s.id) ? { ...s, visitor_name: visitorName } : s)
    );
    clearSelection();
  };

  const handleDelete = async (id: number) => {
    await api.deleteSighting(id);
    setSightings((prev) => prev.filter((s) => s.id !== id));
    setSelectedIds((prev) => { const n = new Set(prev); n.delete(id); return n; });
    toast.success("Detection deleted");
  };

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    setBulkDeleting(true);
    try {
      const res = await api.bulkDeleteSightings(ids);
      setSightings((prev) => prev.filter((s) => !ids.includes(s.id)));
      clearSelection();
      toast.success(`${res.deleted ?? ids.length} detection${ids.length !== 1 ? "s" : ""} deleted`);
    } catch {
      toast.error("Bulk delete failed");
    } finally {
      setBulkDeleting(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="container py-6 space-y-5">

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Detection History</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            All face detections from your cameras — click a card to select, or use "Name" to identify someone
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowAddVisitor(true)}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />Add Known Visitor
          </Button>
        </div>
      </div>

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name or camera…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          {(["all", "known", "unknown"] as Filter[]).map((f) => (
            <Button
              key={f}
              variant={filter === f ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(f)}
              className="capitalize"
            >
              {f === "known" && <UserCheck className="h-3.5 w-3.5 mr-1" />}
              {f === "unknown" && <UserX className="h-3.5 w-3.5 mr-1" />}
              {f}
            </Button>
          ))}
        </div>
      </div>

      {/* Summary counts */}
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span><strong className="text-foreground">{knownCount}</strong> identified</span>
        <span><strong className="text-amber-500">{unknownCount}</strong> unknown</span>
        <span><strong className="text-foreground">{sightings.length}</strong> total</span>
      </div>

      {/* ── Bulk action toolbar (appears when items are selected) ── */}
      {selectionMode && (
        <div className="sticky top-16 z-40 flex items-center gap-3 rounded-lg border bg-card/95 backdrop-blur px-4 py-2.5 shadow-lg">
          <div className="flex items-center gap-2 text-sm font-medium">
            <CheckSquare className="h-4 w-4 text-primary" />
            <span>{selectedIds.size} selected</span>
          </div>
          <div className="flex gap-2 ml-auto flex-wrap">
            <Button variant="outline" size="sm" onClick={selectAll} className="text-xs">
              <CheckCheck className="h-3.5 w-3.5 mr-1" />Select All ({filtered.length})
            </Button>
            {selectedUnknownIds.length > 0 && (
              <Button size="sm" variant="outline" className="text-xs" onClick={() => setShowBulkNameDialog(true)}>
                <Users className="h-3.5 w-3.5 mr-1" />
                Name {selectedUnknownIds.length} Unknown
              </Button>
            )}
            <Button
              size="sm"
              variant="destructive"
              className="text-xs"
              onClick={handleBulkDelete}
              disabled={bulkDeleting}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              {bulkDeleting ? "Deleting…" : `Delete ${selectedIds.size}`}
            </Button>
            <Button variant="ghost" size="sm" onClick={clearSelection} className="text-xs">
              <X className="h-3.5 w-3.5 mr-1" />Clear
            </Button>
          </div>
        </div>
      )}

      {/* ── Grid ── */}
      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 space-y-3">
          <Camera className="h-14 w-14 mx-auto text-muted-foreground/30" />
          <p className="text-lg font-medium">No detections found</p>
          <p className="text-sm text-muted-foreground">
            {sightings.length === 0
              ? "The detection service hasn't captured any faces yet. Make sure it's running and the camera is in view."
              : search
              ? "No results match your search."
              : `No ${filter} detections to show.`}
          </p>
          {sightings.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Check Settings → Service tab to confirm the detection service is active.
            </p>
          )}
        </div>
      ) : (
        <>
          {/* Select-all hint when nothing is selected */}
          {!selectionMode && (
            <p className="text-xs text-muted-foreground -mt-2">
              Tip: click any card to select it, then use the bulk toolbar to name or delete multiple detections at once.
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((s) => (
              <SightingCard
                key={s.id}
                sighting={s}
                selected={selectedIds.has(s.id)}
                selectionMode={selectionMode}
                onToggleSelect={toggleSelect}
                onName={setNamingSighting}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </>
      )}

      {/* Single-item Name dialog */}
      {namingSighting && (
        <NameDialog
          sightingIds={[namingSighting.id]}
          previewSighting={namingSighting}
          knownVisitors={knownVisitors}
          onClose={() => setNamingSighting(null)}
          onNamed={handleNamed}
        />
      )}

      {/* Bulk Name dialog */}
      {showBulkNameDialog && (
        <NameDialog
          sightingIds={selectedUnknownIds}
          knownVisitors={knownVisitors}
          onClose={() => setShowBulkNameDialog(false)}
          onNamed={handleNamed}
        />
      )}

      {/* Add Visitor dialog */}
      <AddVisitorDialog
        open={showAddVisitor}
        onClose={() => setShowAddVisitor(false)}
        onAdded={loadData}
      />
    </main>
  );
};

export default History;
