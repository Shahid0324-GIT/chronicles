import { NextResponse } from "next/server";
import { ApiError, getUniverseGraph } from "@/lib/api";
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  try {
    return NextResponse.json(await getUniverseGraph(slug), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return NextResponse.json(
      {
        code: "atlas_unavailable",
        message:
          error instanceof Error
            ? error.message
            : "The atlas could not be opened.",
      },
      { status: error instanceof ApiError ? error.status : 503 },
    );
  }
}
