import pytest

from src.application.story_theme import StoryTheme, contrast, fallback_theme, palette

# Deliberately hard to read: text colours close to their backgrounds.
HARD = [
    StoryTheme(mode="dark", ground="#808080", accent="#101010", second="#222266"),
    StoryTheme(mode="light", ground="#101010", accent="#ffffe0", second="#eeeeee"),
    StoryTheme(mode="dark", ground="#00ff00", accent="#00ff00", second="#00ff00"),
]


@pytest.mark.parametrize("theme", [*HARD, *(fallback_theme(f"story-{n}") for n in range(40))])
def test_every_theme_reads(theme):
    colours = palette(theme)
    for text in ("ink", "muted", "accent", "second"):
        for ground in ("ground", "surface"):
            assert contrast(colours[text], colours[ground]) >= 4.5, (text, ground, colours)
    assert contrast(colours["accentInk"], colours["accent"]) >= 4.5


def test_stories_get_steady_and_differing_looks():
    assert fallback_theme("marsh-draft") == fallback_theme("marsh-draft")
    looks = {palette(fallback_theme(f"story-{n}"))["ground"] for n in range(20)}
    assert len(looks) > 10
