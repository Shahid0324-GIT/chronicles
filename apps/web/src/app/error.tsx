"use client";
export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="standalone-state" role="alert">
      <span className="state-brand">✧ CHRONICLES</span>
      <p className="eyebrow">THE LOCAL ATLAS IS UNAVAILABLE</p>
      <h1>A world just out of reach.</h1>
      <p>
        Start FastAPI and PostgreSQL, check migrations, then open the atlas
        again.
      </p>
      <button className="primary-button" onClick={reset}>
        Open the atlas ↗
      </button>
    </section>
  );
}
