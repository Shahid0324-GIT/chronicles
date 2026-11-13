from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.inference import InferenceRouter
from src.application.narrative import NarrativeBuilder
from src.application.ports.knowledge import KnowledgeSession, KnowledgeTransaction
from src.application.ports.narrative import NarrativeRepository, NarrativeTransaction
from src.application.ports.research import ResearchRepository
from src.application.ports.retrieval import EvidenceIndex, EvidenceIndexTransaction
from src.application.ports.source_intelligence import SourceRegistry, SourceRegistryTransaction
from src.application.promotion import CanonicalGraphPromotionService
from src.application.retrieval import EvidenceRetrieval
from src.domain.knowledge import PromotionPolicy
from src.infrastructure.config.settings import Settings
from src.infrastructure.embeddings import OllamaEmbeddings
from src.infrastructure.inference import create_inference
from src.infrastructure.model_runtime import LocalModelLease
from src.infrastructure.persistence.evidence_index import SqlEvidenceIndex
from src.infrastructure.persistence.knowledge_repository import SqlKnowledgeRepository
from src.infrastructure.persistence.narrative_repository import SqlNarrativeRepository
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.persistence.source_registry import SqlSourceRegistry
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy, SearxngSearch
from src.orchestration.knowledge_pipeline import KnowledgePipeline
from src.orchestration.research_workflow import ResearchWorkflow


def knowledge_transactions(factory: async_sessionmaker[AsyncSession]) -> KnowledgeTransaction:
    @asynccontextmanager
    async def transaction() -> AsyncIterator[KnowledgeSession]:
        async with factory() as session, session.begin():
            yield KnowledgeSession(SqlResearchRepository(session), SqlKnowledgeRepository(session))

    return transaction


def build_workflow(
    settings: Settings,
    factory: async_sessionmaker[AsyncSession],
    inference: InferenceRouter | None = None,
) -> ResearchWorkflow:
    @asynccontextmanager
    async def transaction() -> AsyncIterator[ResearchRepository]:
        async with factory() as session, session.begin():
            yield SqlResearchRepository(session)

    knowledge_tx = knowledge_transactions(factory)
    publication = CanonicalGraphPromotionService(
        knowledge_tx,
        PromotionPolicy(settings.promotion_minimum_sources, settings.promotion_strong_sources),
    )
    policy = PublicSourcePolicy(settings.research_allowed_hosts)
    return ResearchWorkflow(
        transaction,
        inference or create_inference(settings, LocalModelLease(factory)),
        PublicDocumentFetcher(
            policy, settings.research_max_source_bytes, settings.research_max_source_chars
        ),
        SearxngSearch(settings.searxng_base_url, policy) if settings.searxng_base_url else None,
        max_iterations=settings.agent_max_iterations,
        max_sources=settings.agent_max_sources,
        max_queries=settings.agent_max_search_queries,
        cache_hours=settings.research_source_cache_hours,
        source_chars=settings.research_max_source_chars,
        knowledge=KnowledgePipeline(knowledge_tx, publication),
        retrieval=build_retrieval(settings, factory),
        narratives=NarrativeBuilder(narrative_transactions(factory)),
        registry=registry_transactions(factory),
        discovery_search=(
            SearxngSearch(settings.searxng_base_url, policy, navigation_only=True)
            if settings.searxng_base_url
            else None
        ),
    )


def index_transactions(factory: async_sessionmaker[AsyncSession]) -> EvidenceIndexTransaction:
    @asynccontextmanager
    async def transaction() -> AsyncIterator[EvidenceIndex]:
        async with factory() as session, session.begin():
            yield SqlEvidenceIndex(session)

    return transaction


def registry_transactions(factory: async_sessionmaker[AsyncSession]) -> SourceRegistryTransaction:
    @asynccontextmanager
    async def transaction() -> AsyncIterator[SourceRegistry]:
        async with factory() as session, session.begin():
            yield SqlSourceRegistry(session)

    return transaction


def narrative_transactions(factory: async_sessionmaker[AsyncSession]) -> NarrativeTransaction:
    @asynccontextmanager
    async def transaction() -> AsyncIterator[NarrativeRepository]:
        async with factory() as session, session.begin():
            yield SqlNarrativeRepository(session)

    return transaction


def build_retrieval(
    settings: Settings, factory: async_sessionmaker[AsyncSession]
) -> EvidenceRetrieval:
    return EvidenceRetrieval(
        index_transactions(factory),
        OllamaEmbeddings(
            settings.ollama_base_url, settings.ollama_embedding_model, LocalModelLease(factory)
        ),
    )
