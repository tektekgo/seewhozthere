/**
 * ImageLightbox — click any thumbnail to open a full-size overlay.
 * Renders via a React Portal into document.body to avoid stacking context issues.
 *
 * Usage:
 *   const [lightbox, setLightbox] = useState<LightboxImage | null>(null);
 *
 *   <img onClick={() => setLightbox({ src, alt, caption })} ... />
 *   <ImageLightbox image={lightbox} onClose={() => setLightbox(null)} />
 */

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Download, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface LightboxImage {
  src: string;
  alt?: string;
  /** Optional caption shown below the image (e.g. "Camera · 14:32:05") */
  caption?: string;
  /** Sighting ID — passed through so the caller can open the rename dialog from the lightbox */
  sightingId?: number;
}

interface ImageLightboxProps {
  image: LightboxImage | null;
  onClose: () => void;
  /** If provided, a "Change Name" button is shown in the lightbox toolbar */
  onChangeName?: (sightingId: number) => void;
}

function LightboxContent({ image, onClose, onChangeName }: ImageLightboxProps) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  if (!image) return null;

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = image.src;
    a.download = image.alt?.replace(/\s+/g, "_") ?? "snapshot";
    a.click();
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, zIndex: 9999 }}
      className="flex items-center justify-center bg-black/85 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Modal panel — stop propagation so clicking image/buttons doesn't close */}
      <div
        className="relative flex flex-col items-center"
        style={{ maxWidth: "90vw", maxHeight: "90vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Toolbar */}
        <div className="absolute top-2 right-2 flex gap-1" style={{ zIndex: 10000 }}>
          {onChangeName && image.sightingId !== undefined && (
            <Button
              size="sm"
              variant="secondary"
              className="h-8 px-3 rounded-full bg-black/60 hover:bg-black/80 text-white border-0 text-xs"
              onClick={() => { onClose(); onChangeName(image.sightingId!); }}
              title="Change or correct the name for this detection"
            >
              <Tag className="h-3.5 w-3.5 mr-1.5" />Change Name
            </Button>
          )}
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8 rounded-full bg-black/60 hover:bg-black/80 text-white border-0"
            onClick={handleDownload}
            title="Download image"
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8 rounded-full bg-black/60 hover:bg-black/80 text-white border-0"
            onClick={onClose}
            title="Close (Esc)"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Image */}
        <img
          src={image.src}
          alt={image.alt ?? "Snapshot"}
          style={{ maxWidth: "90vw", maxHeight: "80vh", objectFit: "contain" }}
          className="rounded-lg shadow-2xl"
          onError={(e) => {
            (e.target as HTMLImageElement).alt = "Image unavailable";
          }}
        />

        {/* Caption */}
        {image.caption && (
          <p className="mt-3 text-sm text-white/80 text-center px-4" style={{ maxWidth: "500px" }}>
            {image.caption}
          </p>
        )}

        {/* Hint */}
        <p className="mt-1 text-xs text-white/40">
          Click outside or press Esc to close
        </p>
      </div>
    </div>
  );
}

export function ImageLightbox({ image, onClose, onChangeName }: ImageLightboxProps) {
  if (!image) return null;
  return createPortal(
    <LightboxContent image={image} onClose={onClose} onChangeName={onChangeName} />,
    document.body
  );
}
