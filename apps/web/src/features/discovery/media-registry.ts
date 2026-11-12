import type { NodeType } from "@/lib/contracts";
export interface MediaAsset {
  src: string;
  alt: string;
  credit: string;
  kind: "interpretive" | "fallback";
  focalPoint?: string;
}
const original = (file: string, alt: string): MediaAsset => ({
  src: `/art/${file}.svg`,
  alt,
  credit: "Original atlas illustration · interpretive, not official artwork",
  kind: "interpretive",
});
// Stable IDs select presentation assets only. No graph records or relationships live here.
const assets: Record<string, MediaAsset> = {
  "ad4c98b0-37d8-5057-9c47-5cd1783e9bb6": original(
    "capital",
    "An imagined fantasy city, illustrated for the atlas",
  ),
  "f974ad2b-7275-5dfa-8f3d-27bf2b40c03d": original(
    "traveler",
    "Interpretive dark-haired traveler portrait",
  ),
  "a13997f9-a7a5-5468-85dc-130e52b12db3": original(
    "silver",
    "Interpretive silver-haired traveler portrait",
  ),
  "6dbf7926-5ae5-540f-880b-2a4aaee5f8e9": original(
    "spirit",
    "Interpretive catlike spirit illustration",
  ),
  "4dd188d1-64a3-5cc7-a76c-ce4ae222a8f7": original(
    "wanderer",
    "Interpretive young wanderer portrait",
  ),
  "7fc7b4aa-71ec-5b13-b9f8-4d2515b3ab42": original(
    "keeper",
    "Interpretive elderly keeper portrait",
  ),
  "81c8e83b-f580-55c3-b153-b1a66240a587": original(
    "knight",
    "Interpretive knight portrait",
  ),
  "cd778b3c-2cf9-57d5-bee6-fde4e3fb973d": original(
    "capital",
    "Imagined capital architecture",
  ),
  "6ec78abf-27e1-5521-bad3-929e0740c917": original(
    "loot-house",
    "Interpretive timber building illustration",
  ),
  "52a97e24-c9c0-59b6-bc99-e50409c4a295": original(
    "insignia",
    "Symbolic insignia illustration",
  ),
  "8b292cf6-8822-5b00-b58b-f885abb761ac": original(
    "search",
    "Symbolic search illustration",
  ),
};
export const FALLBACK_MEDIA: MediaAsset = {
  src: "/art/uncharted.svg",
  alt: "An atlas compass marking uncharted artwork",
  credit: "Original atlas illustration · artwork not yet catalogued",
  kind: "fallback",
};
export function resolveMedia(id: string, type?: NodeType): MediaAsset {
  return (
    assets[id] ?? {
      ...FALLBACK_MEDIA,
      alt: `${type ? type.toLowerCase().replaceAll("_", " ") : "Universe"} artwork not yet catalogued`,
    }
  );
}
