"use client";
export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="notice" role="alert">
      <p className="eyebrow">CONNECTION INTERRUPTED</p>
      <h1>The atlas is out of reach.</h1>
      <p>
        Check that FastAPI and PostgreSQL are running and migrations have been
        applied.
      </p>
      <button onClick={reset}>Try again ↗</button>
    </section>
  );
}
