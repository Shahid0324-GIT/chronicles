import type { StorySection } from "@/features/narrative/contracts";

export const paragraphKey = (section: number, paragraph: number) =>
  `${section}-${paragraph}`;

/** The first paragraph that tells each event. */
export function eventTargets(story: StorySection[]) {
  const targets = new Map<string, string>();
  story.forEach((section, s) =>
    section.paragraphs.forEach((paragraph, p) => {
      for (const id of paragraph.eventNodeIds)
        if (!targets.has(id)) targets.set(id, paragraphKey(s, p));
    }),
  );
  return targets;
}

/** The events at the reader's place; a paragraph without any keeps the previous ones. */
export function eventsAt(story: StorySection[], key: string) {
  let current: string[] = [];
  for (const [s, section] of story.entries())
    for (const [p, paragraph] of section.paragraphs.entries()) {
      if (paragraph.eventNodeIds.length) current = paragraph.eventNodeIds;
      if (paragraphKey(s, p) === key) return current;
    }
  return [];
}

/** Which paragraph is being read: the last one to pass the reading line. */
export function readingIndex(tops: number[], line: number, atEnd: boolean) {
  if (!tops.length) return 0;
  if (atEnd) return tops.length - 1;
  let index = 0;
  tops.forEach((top, i) => {
    if (top <= line) index = i;
  });
  return index;
}

export function readingMinutes(story: StorySection[]) {
  const words = story
    .flatMap((section) => section.paragraphs)
    .map((p) => p.segments.map((s) => s.text).join(""))
    .join(" ")
    .split(/\s+/)
    .filter(Boolean).length;
  return Math.max(1, Math.round(words / 220));
}
