import type { NodeType } from "@/lib/contracts";
export const NODE_IDENTITIES: Record<
  NodeType,
  {
    label: string;
    color: string;
    shape: string;
    glyph: string;
    center: [number, number];
  }
> = {
  CHARACTER: {
    label: "Characters",
    color: "#d0b383",
    shape: "rectangle",
    glyph: "\u2727",
    center: [-260, 20],
  },
  EVENT: {
    label: "Events",
    color: "#d89974",
    shape: "diamond",
    glyph: "\u25c7",
    center: [70, -100],
  },
  LOCATION: {
    label: "Locations",
    color: "#8cafa1",
    shape: "rectangle",
    glyph: "\u2302",
    center: [390, 20],
  },
  LORE: {
    label: "Lore",
    color: "#a7abd0",
    shape: "circle",
    glyph: "\u25ce",
    center: [-300, 370],
  },
  FACTION: {
    label: "Factions",
    color: "#ba9b98",
    shape: "triangle",
    glyph: "\u25b3",
    center: [-570, -290],
  },
  OBJECT: {
    label: "Objects",
    color: "#d0c38c",
    shape: "square",
    glyph: "\u25a1",
    center: [30, 330],
  },
  STORY_ARC: {
    label: "Story arcs",
    color: "#9cb9c9",
    shape: "rectangle",
    glyph: "\u2312",
    center: [420, 360],
  },
  MYSTERY: {
    label: "Mysteries",
    color: "#b49abd",
    shape: "diamond",
    glyph: "\u27e1",
    center: [200, -400],
  },
};
export const NODE_TYPES = Object.keys(NODE_IDENTITIES) as NodeType[];
export const humanize = (value: string) =>
  value.toLowerCase().replaceAll("_", " ");
