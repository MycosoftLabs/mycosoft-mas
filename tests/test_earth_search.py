"""
Tests for the Earth Search module — planetary-scale unified search.

Tests models, registry, orchestrator, connectors, MINDEX client, and API router.

Created: March 15, 2026
"""

from datetime import datetime


from mycosoft_mas.earth_search.models import (
    DOMAIN_GROUPS,
    EarthSearchDomain,
    EarthSearchQuery,
    EarthSearchResponse,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)
from mycosoft_mas.earth_search.registry import (
    EARTH_DATA_SOURCES,
    get_all_realtime_sources,
    get_source_info,
    get_sources_for_domain,
)

# ── Model Tests ──────────────────────────────────────────────────────────────


class TestEarthSearchDomain:
    def test_all_domains_exist(self):
        """Verify all 35+ domains are defined."""
        assert len(EarthSearchDomain) >= 35

    def test_domain_groups_cover_all(self):
        """Every domain group contains valid domains."""
        for group, members in DOMAIN_GROUPS.items():
            for domain in members:
                assert isinstance(domain, EarthSearchDomain), f"{group}: {domain}"

    def test_key_domains_present(self):
        """Critical domains are present."""
        critical = [
            "fungi",
            "plants",
            "birds",
            "mammals",
            "reptiles",
            "insects",
            "marine_life",
            "earthquakes",
            "volcanoes",
            "wildfires",
            "storms",
            "flights",
            "vessels",
            "satellites",
            "solar_flares",
            "power_plants",
            "cell_towers",
            "internet_cables",
            "weather",
            "co2",
            "air_quality",
            "compounds",
            "genetics",
            "research",
        ]
        domain_values = {d.value for d in EarthSearchDomain}
        for c in critical:
            assert c in domain_values, f"Missing critical domain: {c}"


class TestEarthSearchQuery:
    def test_basic_query(self):
        q = EarthSearchQuery(query="mushrooms near Portland")
        assert q.query == "mushrooms near Portland"
        assert q.limit == 20
        assert q.include_crep is True

    def test_resolved_domains_empty_returns_all(self):
        q = EarthSearchQuery(query="test")
        resolved = q.resolved_domains()
        assert len(resolved) == len(EarthSearchDomain)

    def test_resolved_domains_with_groups(self):
        q = EarthSearchQuery(query="test", domain_groups=["life"])
        resolved = q.resolved_domains()
        assert EarthSearchDomain.FUNGI in resolved
        assert EarthSearchDomain.PLANTS in resolved
        assert EarthSearchDomain.BIRDS in resolved

    def test_geo_filter(self):
        geo = GeoFilter(lat=45.5, lng=-122.6, radius_km=50)
        q = EarthSearchQuery(query="test", geo=geo)
        assert q.geo.lat == 45.5
        assert q.geo.radius_km == 50

    def test_temporal_filter(self):
        tf = TemporalFilter(realtime=True)
        q = EarthSearchQuery(query="test", temporal=tf)
        assert q.temporal.realtime is True


class TestEarthSearchResult:
    def test_basic_result(self):
        r = EarthSearchResult(
            result_id="test-1",
            domain=EarthSearchDomain.FUNGI,
            source="mindex_local",
            title="Amanita muscaria",
            description="Fly agaric mushroom",
            lat=45.5,
            lng=-122.6,
            confidence=0.95,
        )
        assert r.result_id == "test-1"
        assert r.domain == EarthSearchDomain.FUNGI
        assert r.lat == 45.5

    def test_crep_fields(self):
        r = EarthSearchResult(
            result_id="test-2",
            domain=EarthSearchDomain.FLIGHTS,
            source="crep_flights",
            title="Flight ABC123",
            crep_layer="flights",
            crep_entity_id="a1b2c3",
        )
        assert r.crep_layer == "flights"
        assert r.crep_entity_id == "a1b2c3"


class TestEarthSearchResponse:
    def test_basic_response(self):
        resp = EarthSearchResponse(
            query="test",
            domains_searched=[EarthSearchDomain.FUNGI],
            results=[],
            total_count=0,
            timestamp=datetime.utcnow().isoformat(),
        )
        assert resp.query == "test"
        assert resp.total_count == 0


# ── Registry Tests ───────────────────────────────────────────────────────────


class TestRegistry:
    def test_sources_exist(self):
        """At least 20 data sources are registered."""
        assert len(EARTH_DATA_SOURCES) >= 20

    def test_get_source_info(self):
        info = get_source_info("inaturalist")
        assert info is not None
        assert info.name == "iNaturalist"
        assert EarthSearchDomain.FUNGI in info.domains

    def test_get_sources_for_domain(self):
        sources = get_sources_for_domain(EarthSearchDomain.FUNGI)
        source_ids = {s.source_id for s in sources}
        assert "inaturalist" in source_ids
        assert "gbif" in source_ids

    def test_realtime_sources(self):
        rt = get_all_realtime_sources()
        rt_ids = {s.source_id for s in rt}
        assert "crep_flights" in rt_ids
        assert "usgs_earthquake" in rt_ids

    def test_mindex_local_covers_all_domains(self):
        mindex = get_source_info("mindex_local")
        assert mindex is not None
        assert len(mindex.domains) == len(EarthSearchDomain)

    def test_critical_sources_present(self):
        critical = [
            "inaturalist",
            "gbif",
            "usgs_earthquake",
            "firms_wildfires",
            "crep_flights",
            "crep_marine",
            "crep_satellites",
            "noaa_swpc",
            "pubchem",
            "genbank",
            "pubmed",
            "osm_overpass",
            "mindex_local",
        ]
        for sid in critical:
            assert get_source_info(sid) is not None, f"Missing source: {sid}"


# ── Connector Tests (unit, no network) ───────────────────────────────────────


class TestConnectorImports:
    def test_all_connectors_import(self):
        from mycosoft_mas.earth_search.connectors import (
            EnvironmentConnector,
            SpaceConnector,
            SpeciesConnector,
        )

        assert SpeciesConnector.source_id == "species"
        assert EnvironmentConnector.source_id == "environment"
        assert SpaceConnector.source_id == "space"


# ── MINDEX Earth Client Tests ───────────────────────────────────────────────


class TestMINDEXEarthClient:
    def test_client_import(self):
        from mycosoft_mas.earth_search.mindex_earth_client import get_mindex_earth_client

        client = get_mindex_earth_client()
        assert client.base_url == "http://192.168.0.189:8000"


# ── Orchestrator Tests ───────────────────────────────────────────────────────


class TestOrchestratorImport:
    def test_run_earth_search_importable(self):
        from mycosoft_mas.earth_search.orchestrator import run_earth_search

        assert callable(run_earth_search)


# ── Agent Tests ──────────────────────────────────────────────────────────────


class TestEarthSearchAgent:
    def test_agent_creation(self):
        from mycosoft_mas.agents.earth_search_agent import EarthSearchAgent

        agent = EarthSearchAgent()
        assert agent.name == "EarthSearchAgent"
        assert "earth_search" in agent.capabilities
        assert "species_search" in agent.capabilities
        assert "crep_search" in agent.capabilities


# ── API Router Tests ─────────────────────────────────────────────────────────


class TestEarthSearchAPI:
    def test_router_import(self):
        from mycosoft_mas.core.routers.earth_search_api import router

        assert router.prefix == "/api/earth-search"

    def test_router_routes(self):
        from mycosoft_mas.core.routers.earth_search_api import router

        paths = {r.path for r in router.routes}
        assert "/query" in paths
        assert "/domains" in paths
        assert "/sources" in paths
        assert "/health" in paths
        assert "/crep" in paths
        assert "/ingest" in paths


# ── Ingestion Pipeline Tests ─────────────────────────────────────────────────


class TestIngestionPipeline:
    def test_pipeline_import(self):
        from mycosoft_mas.earth_search.ingestion.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        assert pipeline.SUPABASE_TABLE == "earth_search_results"
