import { notFound } from "next/navigation";
import { ApiError, getUniverseGraph, listUniverses } from "@/lib/api";
import AtlasExperience from "@/features/atlas/AtlasExperience";
export const dynamic = "force-dynamic";
// Compatibility deep link: same continuous canvas, initialized to the requested universe.
export default async function UniversePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [universes, graph] = await Promise.all([
    listUniverses(),
    getUniverseGraph(slug).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
  ]);
  return <AtlasExperience universes={universes} graph={graph} />;
}
