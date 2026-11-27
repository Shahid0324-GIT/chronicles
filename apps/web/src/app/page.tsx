import SearchHome from "@/features/search/SearchHome";

type Search = Promise<{ character?: string; story?: string }>;

export default async function Home({ searchParams }: { searchParams: Search }) {
  const { character, story } = await searchParams;
  // A cast member's link arrives already knowing what to write.
  const asked =
    typeof character === "string" && typeof story === "string"
      ? {
          kind: "character" as const,
          story: story.slice(0, 180),
          subject: character.slice(0, 120),
          wikipedia_title: "",
        }
      : undefined;
  return (
    <SearchHome key={`${asked?.story}/${asked?.subject}`} initial={asked} />
  );
}
