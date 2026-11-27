"""Each story's own look: a model picks the mood, code makes it readable.

The model chooses a background, two colours, a type style and a motif. Every other
colour is derived, and colours are lightened or darkened until text on them passes
WCAG contrast, so no choice can produce an unreadable page.
"""

import colorsys
import hashlib
import json
from typing import Literal

from pydantic import Field

from src.application.knowledge_presentation import Infer
from src.application.research_contracts import InferenceFailure, StructuredModel

HEX = r"^#[0-9a-fA-F]{6}$"
TypeStyle = Literal["epic", "storybook", "gothic", "scifi", "playful", "modern"]
Motif = Literal["stars", "branches", "waves", "peaks", "embers", "rings"]
TEXT_CONTRAST = 4.5


class StoryTheme(StructuredModel):
    mode: Literal["dark", "light"] = "dark"
    ground: str = Field(pattern=HEX)
    accent: str = Field(pattern=HEX)
    second: str = Field(pattern=HEX)
    style: TypeStyle = "storybook"
    motif: Motif = "rings"


Rgb = tuple[float, float, float]


def _rgb(value: str) -> Rgb:
    return (int(value[1:3], 16) / 255, int(value[3:5], 16) / 255, int(value[5:7], 16) / 255)


def _hex(value: Rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in value)


def _luminance(value: str) -> float:
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in _rgb(value)]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _shade(value: str, lightness: float, saturation: float | None = None) -> str:
    hue, _, current = colorsys.rgb_to_hls(*_rgb(value))
    chosen = current if saturation is None else saturation
    return _hex(colorsys.hls_to_rgb(hue, max(0.0, min(1.0, lightness)), chosen))


def _mix(first: str, second: str, share: float) -> str:
    a, b = _rgb(first), _rgb(second)
    return _hex(
        (a[0] + (b[0] - a[0]) * share, a[1] + (b[1] - a[1]) * share, a[2] + (b[2] - a[2]) * share)
    )


def _readable(colour: str, grounds: tuple[str, ...], towards_light: bool) -> str:
    """The colour, moved toward white or black until it reads on every background."""
    lightness = colorsys.rgb_to_hls(*_rgb(colour))[1]
    step = 0.02 if towards_light else -0.02
    for _ in range(60):
        if min(contrast(colour, g) for g in grounds) >= TEXT_CONTRAST:
            return colour
        lightness += step
        colour = _shade(colour, lightness)
    return "#ffffff" if towards_light else "#000000"


def palette(theme: StoryTheme) -> dict[str, str]:
    dark = theme.mode == "dark"
    _, lightness, saturation = colorsys.rgb_to_hls(*_rgb(theme.ground))
    saturation = min(saturation, 0.6)
    ground = _shade(
        theme.ground, min(lightness, 0.12) if dark else max(lightness, 0.94), saturation
    )
    base = colorsys.rgb_to_hls(*_rgb(ground))[1]
    surface = _shade(ground, base + 0.065 if dark else 0.995, saturation)
    ink = _shade(ground, 0.96 if dark else 0.13, min(saturation, 0.35))
    grounds = (ground, surface)
    muted = _readable(_mix(ink, ground, 0.32), grounds, dark)
    accent = _readable(theme.accent.lower(), grounds, dark)
    second = _readable(theme.second.lower(), grounds, dark)
    accent_ink = max(("#ffffff", "#111018"), key=lambda c: contrast(c, accent))
    return {
        "mode": theme.mode,
        "ground": ground,
        "surface": surface,
        "ink": ink,
        "muted": muted,
        "line": _mix(surface, ink, 0.18),
        "accent": accent,
        "accentInk": accent_ink,
        "second": second,
        "style": theme.style,
        "motif": theme.motif,
    }


def fallback_theme(slug: str) -> StoryTheme:
    """A steady look for a story that has none, different from story to story."""
    seed = hashlib.sha256(slug.encode()).digest()
    # Hues from blue round to amber; the muted greens in between read poorly.
    hue = (200 + seed[0] % 220) % 360 / 360

    def colour(shift: float, light: float, strength: float) -> str:
        return _hex(colorsys.hls_to_rgb((hue + shift) % 1, light, strength))

    motifs: tuple[Motif, ...] = ("stars", "branches", "waves", "peaks", "embers", "rings")
    return StoryTheme(
        mode="dark",
        ground=colour(0, 0.09, 0.4),
        accent=colour(0.5, 0.68, 0.8),
        second=colour(0.12, 0.72, 0.65),
        style="storybook",
        motif=motifs[seed[1] % len(motifs)],
    )


async def choose_theme(
    title: str, medium: str, opening: str, places: list[str], infer: Infer, notes: list[str]
) -> StoryTheme | None:
    try:
        return StoryTheme.model_validate(
            await infer(
                "Choose the look of this story's pages so they feel like its world: mode "
                "(dark or light), ground (the background colour), accent and second (two "
                "vivid colours that suit it) as #rrggbb, style for its headings (epic, "
                "storybook, gothic, scifi, playful or modern) and motif for its artwork "
                "(stars, branches, waves, peaks, embers or rings). Prefer rich, clear "
                "colours over grey or muddy green ones.\n"
                'Return only JSON: {"mode":"dark","ground":"#101030","accent":"#ffc857",'
                '"second":"#6cb8ff","style":"epic","motif":"stars"}\n'
                + json.dumps(
                    {
                        "story": title,
                        "medium": medium,
                        "opening": opening[:600],
                        "places": places[:8],
                    },
                    ensure_ascii=False,
                ),
                StoryTheme,
                "presentation",
            )
        )
    except InferenceFailure:
        notes.append("No theme was chosen; the story uses a default look")
        return None
