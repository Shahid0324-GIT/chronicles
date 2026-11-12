import Link from "next/link";
export default function NotFound() {
  return (
    <section className="notice">
      <h1>An uncharted world.</h1>
      <p>This universe is not in your local collection.</p>
      <Link href="/">Return to the collection →</Link>
    </section>
  );
}
