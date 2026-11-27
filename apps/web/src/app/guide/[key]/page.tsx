import type { Metadata } from "next";
import GuidePage from "@/features/guide/GuidePage";

export const metadata: Metadata = { title: "Story page — Chronicles" };

export default async function Page({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  return <GuidePage key={key} id={key} />;
}
