"""Inspection and spoiler-fence tests using owned synthetic research fixtures."""

from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from .test_knowledge import prepared


async def test_publication_inspection_scoped_reads_and_targeted_correction(factory, app):
    job, service, tx, claims, resolutions = await prepared(factory)
    result = await service.publish(job, resolutions, {}, False)
    character = resolutions[claims[0]["id"]]["canonical_id"]
    async with tx() as unit:
        sources = sorted(
            {e["source_id"] for row in await unit.archive.findings(job) for e in row["evidence"]}
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        audit = await client.get(f"/api/research/jobs/{job}/knowledge")
        assert audit.status_code == 200 and audit.json()["summary"]["active_promotions"] == 3
        graph = (await client.get("/api/universes/re-zero/graph?curated_only=true")).json()
        assert len(graph["nodes"]) == 15 and len(graph["edges"]) == 25
        assert (await client.get(f"/api/nodes/{character}?curated_only=true")).status_code == 404
        query = [("allowed_source_id", value) for value in sources]
        visible = (await client.get("/api/universes/re-zero/graph", params=query)).json()
        assert len(visible["nodes"]) == 17 and len(visible["edges"]) == 26
        hidden = (
            await client.get(
                "/api/universes/re-zero/graph", params={"allowed_source_id": str(uuid4())}
            )
        ).json()
        assert len(hidden["nodes"]) == 15
        aliases = (await client.get(f"/api/nodes/{character}/aliases", params=query)).json()
        assert len(aliases) == 1 and aliases[0]["supporting_claim_ids"]
        assert aliases[0]["source_ids"]
        edge = next(r for r in result["promoted"] if r["kind"] == "relationship")
        corrected = await client.post(
            f"/api/research/promotions/{edge['id']}/rollback",
            json={"reason": "Synthetic correction of one researched relationship."},
        )
        assert corrected.status_code == 200 and corrected.json()["reversed"]
        assert (await client.get(f"/api/research/jobs/{job}/knowledge")).json()["summary"][
            "active_promotions"
        ] == 2
