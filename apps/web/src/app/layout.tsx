import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Chronicles — A fictional universe atlas",
  description:
    "Enter a world. Follow a thread. An immersive local atlas of interconnected stories.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">
          Skip to the atlas
        </a>
        <main id="main">{children}</main>
      </body>
    </html>
  );
}
