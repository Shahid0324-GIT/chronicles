import type { CSSProperties } from "react";
import type { StoryTheme } from "@/features/narrative/contracts";

const FONTS: Record<StoryTheme["style"], string> = {
  epic: "var(--font-cinzel), serif",
  storybook: "var(--font-fraunces), serif",
  gothic: "var(--font-cormorant), serif",
  scifi: "var(--font-space), sans-serif",
  playful: "var(--font-baloo), sans-serif",
  modern: "var(--font-inter), sans-serif",
};

/** A story's look as the variables every screen is drawn with. */
export function storyThemeStyle(theme: StoryTheme): CSSProperties {
  return {
    "--chronicle-ground": theme.ground,
    "--chronicle-surface": theme.surface,
    "--chronicle-ink": theme.ink,
    "--chronicle-muted": theme.muted,
    "--chronicle-accent": theme.accent,
    "--chronicle-accent-ink": theme.accentInk,
    "--chronicle-branch": theme.second,
    // Notes are printed dark on light, whichever way round the story is.
    "--chronicle-paper": theme.mode === "light" ? theme.surface : theme.ink,
    "--frame-line": theme.line,
    "--display": FONTS[theme.style],
    colorScheme: theme.mode,
  } as CSSProperties;
}
