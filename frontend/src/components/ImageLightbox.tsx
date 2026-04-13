/**
 * ImageLightbox — click any thumbnail to open a full-size overlay.
 *
 * Usage:
 *   const [lightbox, setLightbox] = useState<LightboxImage | null>(null);
 *
 *   <img onClick={() => setLightbox({ src, alt, caption })} ... />
 *   <ImageLightbox image={lightbox} onClose={() => setLightbox(null)} />
 */

import { useEffect } from "react";
import { X, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface LightboxImage {
  src: string;
  alt?: string;
  /** Optional caption shown below the image (e.g. "Camera · 14:32:05") */
  caption?: string;
}

interface ImageLightboxProps {
  image: LightboxImage | null;
  onClose: () => void;
}

export function ImageLightbox({ image, onClose }: ImageLightboxProps) {
  // Close on Escape key
  useEffect(() => {
    if (!image) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [image, onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    if (image) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [image]);

  if (!image) return null;

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = image.src;
    a.download = image.alt?.replace(/\s+/g, "_") ?? "snapshot";
    a.click();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Modal panel — stop click propagation so clicking the image doesn't close */}
      <div
        className="relative flex flex-col items-center max-w-[90vw] max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Toolbar */}
        <div className="absolute top-2 right-2 flex gap-1 z-10">
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
          className="max-w-[90vw] max-h-[80vh] rounded-lg object-contain shadow-2xl"
          onError={(e) => {
            (e.target as HTMLImageElement).src = "/static/mock_faces/unknown_1.jpg";
          }}
        />

        {/* Caption */}
        {image.caption && (
          <p className="mt-3 text-sm text-white/80 text-center px-4 max-w-md">
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
