import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = {
  title: "Universe Atlas",
  description: "A local atlas of interconnected fictional worlds.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <header className="masthead">
          <Link className="brand" href="/">
            <span aria-hidden="true">✧</span> UNIVERSE ATLAS
          </Link>
          <span className="edition">FIELD NOTES / VOLUME 01</span>
          <span className="local">
            <i /> LOCAL EDITION
          </span>
        </header>
        <main id="main">{children}</main>
        <footer>
          <span>UNIVERSE ATLAS</span>
          <span>A beginning, not a boundary.</span>
          <span>PHASE 01 · FOUNDATIONS</span>
        </footer>
      </body>
    </html>
  );
}
