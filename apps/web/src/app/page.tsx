import Link from "next/link";
import { listUniverses } from "@/lib/api";
export const dynamic = "force-dynamic";
export default async function Catalog() {
  const universes = await listUniverses();
  return (
    <>
      <section className="intro">
        <p className="eyebrow">
          THE COLLECTION / {String(universes.length).padStart(2, "0")} WORLDS
          CHARTED
        </p>
        <h1>
          Every world has
          <br />a thousand <em>connections.</em>
        </h1>
        <p className="lede">
          Follow a character. Trace an event. Discover the threads that turn a
          story into a universe.
        </p>
        <div className="intro-rule">
          <span>CHOOSE A WORLD TO BEGIN</span>
          <span aria-hidden="true">↓</span>
        </div>
      </section>
      <section className="catalog" aria-label="Universe catalog">
        {universes.length ? (
          universes.map((u, i) => (
            <Link
              key={u.id}
              href={`/universes/${u.slug}`}
              className="world-card"
            >
              <div className="map-art" aria-hidden="true">
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <span className="star star-a">✦</span>
                <span className="star star-b">✧</span>
                <span className="map-coordinate">
                  {String(i + 1).padStart(2, "0")} / A WORLD OF INTERSECTIONS
                </span>
                <span className="compass">
                  N<br />⟡
                </span>
              </div>
              <div className="world-copy">
                <p className="eyebrow">
                  ATLAS {String(i + 1).padStart(2, "0")}
                </p>
                <h2>{u.title}</h2>
                <p>{u.description}</p>
                <span className="enter">
                  Open the atlas <span aria-hidden="true">↗</span>
                </span>
              </div>
            </Link>
          ))
        ) : (
          <div className="notice">
            <h2>The first page is waiting.</h2>
            <p>
              No universes have been added. Run the backend seed command to load
              the illustrative atlas.
            </p>
          </div>
        )}
        <aside className="margin-note">
          <span aria-hidden="true">✺</span>
          <p>Stories are not straight lines.</p>
          <small>
            They are places to get lost in.
            <br />
            Choose a world, then follow a thread.
          </small>
        </aside>
      </section>
    </>
  );
}
