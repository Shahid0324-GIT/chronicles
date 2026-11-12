import Link from "next/link";
export default function NotFound() {
  return (
    <section className="standalone-state">
      <span className="state-brand">✧ CHRONICLES</span>
      <h1>An uncharted world.</h1>
      <p>This universe is not in your local collection.</p>
      <Link className="primary-button" href="/">
        Return to the atlas ↗
      </Link>
    </section>
  );
}
