import type { Metadata } from "next";
import {
  Baloo_2,
  Cinzel,
  Cormorant_Garamond,
  Fraunces,
  Inter,
  Literata,
  Space_Grotesk,
} from "next/font/google";
import "./globals.css";

// Each story picks one heading style; only the fonts a page uses are downloaded.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const literata = Literata({ subsets: ["latin"], variable: "--font-literata" });
const cinzel = Cinzel({
  subsets: ["latin"],
  variable: "--font-cinzel",
  preload: false,
});
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  preload: false,
});
const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-cormorant",
  preload: false,
});
const space = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space",
  preload: false,
});
const baloo = Baloo_2({
  subsets: ["latin"],
  variable: "--font-baloo",
  preload: false,
});
const fonts = [inter, literata, cinzel, fraunces, cormorant, space, baloo]
  .map((font) => font.variable)
  .join(" ");
export const metadata: Metadata = {
  title: "Chronicles — A fictional universe atlas",
  description:
    "Enter a world. Follow a thread. An immersive local atlas of interconnected stories.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={fonts}>
      <body>
        <a className="skip" href="#main">
          Skip to the atlas
        </a>
        <main id="main">{children}</main>
      </body>
    </html>
  );
}
