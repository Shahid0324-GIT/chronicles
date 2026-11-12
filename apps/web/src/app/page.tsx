import { getUniverseGraph, listUniverses } from "@/lib/api";
import AtlasExperience from "@/features/atlas/AtlasExperience";
export const dynamic = "force-dynamic";
export default async function Home() {
  const universes = await listUniverses();
  const graph = universes[0] ? await getUniverseGraph(universes[0].slug) : null;
  return <AtlasExperience universes={universes} graph={graph} />;
}
