import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getUniverseGraph } from "@/lib/api";
import Atlas from "@/components/Atlas";
export const dynamic = "force-dynamic";
export default async function UniversePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const graph = await getUniverseGraph(slug).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });
  return (
    <>
      <section className="universe-intro">
        <Link className="back" href="/">
          ← All worlds
        </Link>
        <p className="eyebrow">
          THE ATLAS /{" "}
          {graph.continuities.map((c) => c.medium).join(" · ") || "UNCHARTED"}
        </p>
        <h1>{graph.universe.title}</h1>
        <p className="lede">{graph.universe.description}</p>
        <div className="stats">
          <span>
            <b>{graph.nodes.length}</b> entries
          </span>
          <span>
            <b>{graph.edges.length}</b> connections
          </span>
          <span>
            <b>{graph.continuities.length}</b> continuities
          </span>
        </div>
      </section>
      <Atlas graph={graph} />
    </>
  );
}
