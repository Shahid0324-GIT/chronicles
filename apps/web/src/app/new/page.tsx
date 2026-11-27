import type { Metadata } from "next";
import NewStory from "@/features/new-story/NewStory";

export const metadata: Metadata = { title: "New story — Chronicles" };

export default function Page() {
  return <NewStory />;
}
