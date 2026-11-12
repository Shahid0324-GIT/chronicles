"use client";
import Image from "next/image";
import { useState } from "react";
import { FALLBACK_MEDIA, type MediaAsset } from "./media-registry";
export default function MediaArtwork({
  asset,
  className = "",
  priority = false,
  variant = "thumbnail",
}: {
  asset: MediaAsset;
  className?: string;
  priority?: boolean;
  variant?: "thumbnail" | "scene";
}) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const requestedSrc =
    (variant === "scene" ? asset.fullSrc : asset.thumbnailSrc) ?? asset.src;
  const shown =
    failedSrc === requestedSrc
      ? FALLBACK_MEDIA
      : { ...asset, src: requestedSrc };
  return (
    <div className={`media-art ${className}`}>
      <Image
        unoptimized
        fill
        src={shown.src}
        alt={shown.alt}
        priority={priority}
        sizes="(max-width: 640px) 90vw, 360px"
        style={{
          objectFit: "cover",
          objectPosition: asset.focalPoint ?? "center 35%",
        }}
        onError={() => {
          if (shown.src !== FALLBACK_MEDIA.src) setFailedSrc(requestedSrc);
        }}
      />
    </div>
  );
}
