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
/** The look before a story supplies its own. */
export const DEFAULT_THEME: UniverseTheme = {
  id: "midnight",
  motif: "arch",
  palette: {
    ground: "#0e1130",
    surface: "#181c48",
    ink: "#f1f2fb",
    muted: "#b6bce0",
    accent: "#ffc857",
    branch: "#78bdff",
    paper: "#ece9f8",
  },
};
export const themeForUniverse = () => DEFAULT_THEME;
export function themeStyle(theme: UniverseTheme): CSSProperties {
  return Object.fromEntries(
    Object.entries(theme.palette).map(([key, value]) => [
      "--chronicle-" + key,
      value,
    ]),
  ) as CSSProperties;
}
