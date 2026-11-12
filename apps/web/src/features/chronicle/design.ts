import type { CSSProperties } from "react";

/** Shared presentation settings. No story knowledge belongs in a theme. */
export const CHRONICLE_DESIGN = {
  spine: { start: 12, end: 88, lineY: 43, maxVisible: 5 },
  motion: {
    enter: 0.35,
    camera: 0.85,
    emphasis: 0.5,
    reveal: 0.6,
    ease: "power2.out",
    cameraEase: "power3.inOut",
  },
  desktop: { primaryWidth: 1920, primaryHeight: 1080, compactWidth: 1400 },
} as const;
export interface UniverseTheme {
  id: string;
  palette: {
    ground: string;
    surface: string;
    ink: string;
    muted: string;
    accent: string;
    branch: string;
    paper: string;
  };
  motif: "arch" | "chart" | "rune";
}
export const UNIVERSE_THEMES: Record<string, UniverseTheme> = {
  manuscript: {
    id: "manuscript",
    motif: "arch",
    palette: {
      ground: "#141c20",
      surface: "#1b272a",
      ink: "#eee5cf",
      muted: "#aaa99b",
      accent: "#ceb17d",
      branch: "#a6c0b6",
      paper: "#e7d6ae",
    },
  },
  nautical: {
    id: "nautical",
    motif: "chart",
    palette: {
      ground: "#101f27",
      surface: "#1c3038",
      ink: "#f0e6d0",
      muted: "#a6b2ad",
      accent: "#d4b274",
      branch: "#8bbfb8",
      paper: "#e9d7b1",
    },
  },
  weathered: {
    id: "weathered",
    motif: "rune",
    palette: {
      ground: "#20211c",
      surface: "#2b2c23",
      ink: "#e8e3ce",
      muted: "#ada992",
      accent: "#bfa468",
      branch: "#aab498",
      paper: "#d6cba6",
    },
  },
};
const universeThemes: Record<string, string> = {
  "re-zero": "manuscript",
  "one-piece": "nautical",
  "elden-ring": "weathered",
};
export const themeForUniverse = (slug?: string) =>
  UNIVERSE_THEMES[universeThemes[slug ?? ""] ?? "manuscript"];
export function themeStyle(theme: UniverseTheme): CSSProperties {
  return Object.fromEntries(
    Object.entries(theme.palette).map(([key, value]) => [
      "--chronicle-" + key,
      value,
    ]),
  ) as CSSProperties;
}
