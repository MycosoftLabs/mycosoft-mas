"""
Comprehensive tests for all new routers added March 3, 2026.

Covers:
- Economy API (12 endpoints)
- Taxonomy API (9 endpoints)
- Knowledge API (7 endpoints)
- Widget API (5 endpoints)
- STATIC Decoding API (15 endpoints)
- Unified Latents API (9 endpoints)
- Router registration in myca_main.py

Uses FastAPI TestClient for HTTP-level testing of every endpoint,
including happy paths, edge cases, and error handling.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Disable rate limiting for tests
os.environ["DISABLE_RATE_LIMIT"] = "true"


# ============================================================================
# App fixture
# ============================================================================


@pytest.fixture(scope="module")
def app():
    """Import the FastAPI app."""
    from mycosoft_mas.core.myca_main import app
    return app


@pytest.fixture(scope="module")
def client(app):
    """Provide a TestClient for the full app."""
    return TestClient(app, raise_server_exceptions=False)


# ============================================================================
# Router Registration Tests
# ============================================================================


class TestRouterRegistration:
    """Verify all new routers are registered on the app."""

    def test_economy_router_registered(self, app):
        routes = [r.path for r in app.routes]
        assert any("/api/economy" in r for r in routes)

    def test_taxonomy_router_registered(self, app):
        routes = [r.path for r in app.routes]
        assert any("/api/taxonomy" in r for r in routes)

    def test_knowledge_router_registered(self, app):
        routes = [r.path for r in app.routes]
        assert any("/api/knowledge" in r for r in routes)

    def test_widget_router_registered(self, app):
        routes = [r.path for r in app.routes]
        assert any("/api/widgets" in r for r in routes)

    def test_static_router_registered(self, app):
        routes = [r.path for r in app.routes]
        assert any("/api/static" in r for r in routes)

    def test_unified_latents_router_registered(self, app):
        routes = [r.path for r in app.routes]
        assert any("/api/unified-latents" in r for r in routes)


# ============================================================================
# Economy API Tests (/api/economy)
# ============================================================================


class TestEconomyHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/economy/health")
        assert resp.status_code == 200

    def test_health_has_status(self, client):
        data = client.get("/api/economy/health").json()
        assert data["status"] == "healthy"

    def test_health_has_wallets_active(self, client):
        data = client.get("/api/economy/health").json()
        assert "wallets_active" in data
        assert data["wallets_active"] == 3  # solana, bitcoin, x401

    def test_health_has_timestamp(self, client):
        data = client.get("/api/economy/health").json()
        assert "timestamp" in data


class TestEconomyWallets:
    def test_list_wallets_returns_200(self, client):
        resp = client.get("/api/economy/wallets")
        assert resp.status_code == 200

    def test_list_wallets_returns_list(self, client):
        data = client.get("/api/economy/wallets").json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_wallet_types_present(self, client):
        data = client.get("/api/economy/wallets").json()
        types = {w["wallet_type"] for w in data}
        assert "solana" in types
        assert "bitcoin" in types
        assert "x401" in types

    def test_wallet_has_address(self, client):
        data = client.get("/api/economy/wallets").json()
        for w in data:
            assert "address" in w
            assert len(w["address"]) > 0

    def test_wallet_has_currency(self, client):
        data = client.get("/api/economy/wallets").json()
        currencies = {w["currency"] for w in data}
        assert "SOL" in currencies
        assert "BTC" in currencies
        assert "X401" in currencies

    def test_get_solana_wallet(self, client):
        resp = client.get("/api/economy/wallets/solana")
        assert resp.status_code == 200
        data = resp.json()
        assert data["wallet_type"] == "solana"
        assert data["currency"] == "SOL"

    def test_get_bitcoin_wallet(self, client):
        resp = client.get("/api/economy/wallets/bitcoin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["wallet_type"] == "bitcoin"

    def test_get_x401_wallet(self, client):
        resp = client.get("/api/economy/wallets/x401")
        assert resp.status_code == 200
        data = resp.json()
        assert data["currency"] == "X401"

    def test_get_nonexistent_wallet_returns_404(self, client):
        resp = client.get("/api/economy/wallets/dogecoin")
        assert resp.status_code == 404


class TestEconomyCharging:
    def test_charge_returns_200(self, client):
        resp = client.post("/api/economy/charge", json={
            "client_id": "test_agent_001",
            "service_type": "taxonomy_lookup",
            "amount": 0.005,
            "currency": "SOL",
        })
        assert resp.status_code == 200

    def test_charge_response_fields(self, client):
        data = client.post("/api/economy/charge", json={
            "client_id": "test_agent_002",
            "service_type": "image_generation",
            "amount": 0.1,
            "currency": "BTC",
        }).json()
        assert "transaction_id" in data
        assert data["client_id"] == "test_agent_002"
        assert data["status"] == "completed"
        assert data["amount"] == 0.1
        assert data["currency"] == "BTC"

    def test_charge_default_amount_from_tier(self, client):
        data = client.post("/api/economy/charge", json={
            "client_id": "test_agent_tier",
            "service_type": "basic_query",
        }).json()
        assert data["status"] == "completed"
        # Default tier is "agent" with price 0.001
        assert data["amount"] == 0.001

    def test_charge_with_metadata(self, client):
        resp = client.post("/api/economy/charge", json={
            "client_id": "test_agent_meta",
            "service_type": "simulation",
            "amount": 1.0,
            "currency": "X401",
            "metadata": {"run_id": "sim_001"},
        })
        assert resp.status_code == 200


class TestEconomyRevenue:
    def test_revenue_returns_200(self, client):
        resp = client.get("/api/economy/revenue")
        assert resp.status_code == 200

    def test_revenue_has_fields(self, client):
        data = client.get("/api/economy/revenue").json()
        assert "daily_revenue" in data
        assert "weekly_revenue" in data
        assert "monthly_revenue" in data
        assert "total_revenue" in data
        assert "active_clients" in data
        assert "currency" in data


class TestEconomyPricing:
    def test_pricing_returns_200(self, client):
        resp = client.get("/api/economy/pricing")
        assert resp.status_code == 200

    def test_pricing_has_four_tiers(self, client):
        data = client.get("/api/economy/pricing").json()
        assert "free" in data
        assert "agent" in data
        assert "premium" in data
        assert "enterprise" in data

    def test_free_tier_is_zero(self, client):
        data = client.get("/api/economy/pricing").json()
        assert data["free"]["price_per_request"] == 0.0

    def test_tiers_have_features(self, client):
        data = client.get("/api/economy/pricing").json()
        for tier_name, tier_info in data.items():
            assert "features" in tier_info
            assert len(tier_info["features"]) > 0


class TestEconomyResources:
    def test_purchase_insufficient_funds(self, client):
        resp = client.post("/api/economy/resources/purchase", json={
            "resource_type": "gpu",
            "quantity": 100,
            "max_price": 99999.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "insufficient_funds"

    def test_resource_needs_returns_200(self, client):
        resp = client.get("/api/economy/resources/needs")
        assert resp.status_code == 200

    def test_resource_needs_has_items(self, client):
        data = client.get("/api/economy/resources/needs").json()
        assert "needs" in data
        assert len(data["needs"]) > 0
        assert "total_estimated_cost" in data

    def test_resource_needs_includes_gpu(self, client):
        data = client.get("/api/economy/resources/needs").json()
        resource_types = [n["resource"] for n in data["needs"]]
        assert "gpu" in resource_types


class TestEconomyIncentives:
    def test_create_incentive_returns_200(self, client):
        resp = client.post("/api/economy/incentives", json={
            "agent_id": "taxonomy_agent",
            "incentive_type": "free_tier",
            "value": 100.0,
            "duration_days": 30,
            "description": "Test incentive",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_list_incentives_returns_200(self, client):
        resp = client.get("/api/economy/incentives")
        assert resp.status_code == 200
        data = resp.json()
        assert "incentives" in data


class TestEconomySummary:
    def test_summary_returns_200(self, client):
        resp = client.get("/api/economy/summary")
        assert resp.status_code == 200

    def test_summary_has_all_fields(self, client):
        data = client.get("/api/economy/summary").json()
        assert data["status"] == "success"
        assert "wallets" in data
        assert "total_revenue" in data
        assert "total_transactions" in data
        assert "pricing_tiers" in data
        assert "timestamp" in data


class TestEconomyClientRegistration:
    def test_register_client_returns_200(self, client):
        resp = client.post("/api/economy/clients/register",
                           params={"client_id": "new_agent_42", "client_type": "agent", "tier": "premium"})
        assert resp.status_code == 200

    def test_register_client_response(self, client):
        data = client.post("/api/economy/clients/register",
                           params={"client_id": "new_human_1", "client_type": "human", "tier": "enterprise"}).json()
        assert data["status"] == "success"
        assert data["client_id"] == "new_human_1"
        assert data["tier"] == "enterprise"


# ============================================================================
# Taxonomy API Tests (/api/taxonomy)
# ============================================================================


class TestTaxonomyHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/taxonomy/health")
        assert resp.status_code == 200

    def test_health_has_status(self, client):
        data = client.get("/api/taxonomy/health").json()
        assert data["status"] == "healthy"

    def test_health_has_mindex_url(self, client):
        data = client.get("/api/taxonomy/health").json()
        assert "mindex_url" in data
        assert "192.168.0.189" in data["mindex_url"]


class TestTaxonomySearch:
    def test_search_returns_200(self, client):
        resp = client.post("/api/taxonomy/search", json={
            "query": "Amanita muscaria",
            "limit": 5,
        })
        assert resp.status_code == 200

    def test_search_response_structure(self, client):
        data = client.post("/api/taxonomy/search", json={
            "query": "test_species",
            "limit": 1,
        }).json()
        assert data["status"] == "success"
        assert "results" in data
        assert "count" in data
        assert "source" in data

    def test_search_with_rank_filter(self, client):
        resp = client.post("/api/taxonomy/search", json={
            "query": "Fungi",
            "rank": "kingdom",
            "limit": 5,
        })
        assert resp.status_code == 200

    def test_search_with_kingdom_filter(self, client):
        resp = client.post("/api/taxonomy/search", json={
            "query": "mushroom",
            "kingdom": "Fungi",
            "include_images": True,
            "include_genetics": False,
        })
        assert resp.status_code == 200


class TestTaxonomyKingdoms:
    def test_kingdoms_returns_200(self, client):
        resp = client.get("/api/taxonomy/kingdoms")
        assert resp.status_code == 200

    def test_kingdoms_has_seven(self, client):
        data = client.get("/api/taxonomy/kingdoms").json()
        assert data["status"] == "success"
        assert len(data["kingdoms"]) == 7

    def test_kingdoms_includes_fungi(self, client):
        data = client.get("/api/taxonomy/kingdoms").json()
        names = [k["name"] for k in data["kingdoms"]]
        assert "Fungi" in names
        assert "Plantae" in names
        assert "Animalia" in names

    def test_kingdoms_total_species(self, client):
        data = client.get("/api/taxonomy/kingdoms").json()
        assert data["total_estimated_species"] == 2189500


class TestTaxonomyIngestion:
    def test_start_ingestion_returns_200(self, client):
        resp = client.post("/api/taxonomy/ingest/start",
                           params={"target": "fungi", "batch_size": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "ingestion_id" in data

    def test_ingestion_status_returns_200(self, client):
        resp = client.get("/api/taxonomy/ingest/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "active" in data
        assert "completed" in data


class TestTaxonomyStats:
    def test_stats_returns_200(self, client):
        resp = client.get("/api/taxonomy/stats")
        assert resp.status_code == 200

    def test_stats_has_kingdoms(self, client):
        data = client.get("/api/taxonomy/stats").json()
        assert "kingdoms" in data
        assert "Fungi" in data["kingdoms"]

    def test_stats_has_all_fields(self, client):
        data = client.get("/api/taxonomy/stats").json()
        assert "total_species" in data
        assert "total_observations" in data
        assert "total_images" in data
        assert "total_genetic_sequences" in data
        assert "last_updated" in data


class TestTaxonomyRandomSpecies:
    def test_random_species_returns_200(self, client):
        resp = client.get("/api/taxonomy/species/random")
        assert resp.status_code == 200

    def test_random_species_with_kingdom(self, client):
        resp = client.get("/api/taxonomy/species/random", params={"kingdom": "Fungi"})
        assert resp.status_code == 200


class TestTaxonomyGetTaxon:
    def test_get_taxon_by_id(self, client):
        # Use a known iNaturalist taxon ID (may fail if no network, that's OK)
        resp = client.get("/api/taxonomy/taxon/47170")  # Fungi
        # Could be 200 or 404 depending on network
        assert resp.status_code in (200, 404)


class TestTaxonomyObservations:
    def test_observations_returns_200(self, client):
        resp = client.get("/api/taxonomy/observations")
        assert resp.status_code == 200

    def test_observations_with_params(self, client):
        resp = client.get("/api/taxonomy/observations",
                          params={"quality_grade": "research", "per_page": 5, "page": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert "observations" in data


# ============================================================================
# Knowledge API Tests (/api/knowledge)
# ============================================================================


class TestKnowledgeHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200

    def test_health_has_status(self, client):
        data = client.get("/api/knowledge/health").json()
        assert data["status"] in ("healthy", "degraded")

    def test_health_has_agent_available(self, client):
        data = client.get("/api/knowledge/health").json()
        assert "agent_available" in data


class TestKnowledgeDomains:
    def test_domains_returns_200(self, client):
        resp = client.get("/api/knowledge/domains")
        assert resp.status_code == 200


class TestKnowledgeStats:
    def test_stats_returns_200(self, client):
        resp = client.get("/api/knowledge/stats")
        assert resp.status_code == 200


class TestKnowledgeQuery:
    def test_query_requires_agent(self, client):
        resp = client.post("/api/knowledge/query", json={
            "query": "What is psilocybin?",
            "depth": "quick",
        })
        # 200 if agent available, 503 if not
        assert resp.status_code in (200, 503)

    def test_classify_requires_agent(self, client):
        resp = client.post("/api/knowledge/classify", params={"query": "mushroom identification"})
        assert resp.status_code in (200, 503)

    def test_research_requires_agent(self, client):
        resp = client.post("/api/knowledge/research", json={
            "query": "mycelium networks and soil health",
            "domains": ["biology", "environmental_science"],
        })
        assert resp.status_code in (200, 503)

    def test_sources_requires_agent(self, client):
        resp = client.get("/api/knowledge/sources/biology")
        assert resp.status_code in (200, 503)


# ============================================================================
# Widget API Tests (/api/widgets)
# ============================================================================


class TestWidgetHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/widgets/health")
        assert resp.status_code == 200

    def test_health_has_widget_types(self, client):
        data = client.get("/api/widgets/health").json()
        assert data["status"] == "healthy"
        assert "available_widget_types" in data
        assert data["total_types"] == 16  # 16 widget types

    def test_health_lists_all_types(self, client):
        data = client.get("/api/widgets/health").json()
        types = data["available_widget_types"]
        assert "map" in types
        assert "taxonomy_tree" in types
        assert "molecule_3d" in types
        assert "species_card" in types


class TestWidgetTypes:
    def test_types_returns_200(self, client):
        resp = client.get("/api/widgets/types")
        assert resp.status_code == 200

    def test_types_has_16_entries(self, client):
        data = client.get("/api/widgets/types").json()
        assert data["total"] == 16
        assert len(data["types"]) == 16

    def test_types_have_correct_structure(self, client):
        data = client.get("/api/widgets/types").json()
        for t in data["types"]:
            assert "type" in t
            assert "name" in t
            assert "description" in t


class TestWidgetSuggest:
    def test_suggest_taxonomy_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "What species of mushroom is this?",
        }).json()
        assert data["status"] == "success"
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "species_card" in types

    def test_suggest_map_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "Where are chanterelles found in the Pacific Northwest?",
        }).json()
        assert data["status"] == "success"
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "map" in types

    def test_suggest_chemistry_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "Show me the molecular structure of psilocybin",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "molecule_3d" in types

    def test_suggest_genetics_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "Show the DNA sequence of ITS region",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "genetic_viewer" in types

    def test_suggest_weather_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "What is the weather forecast for growing season?",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "weather_map" in types

    def test_suggest_evolution_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "Show the phylogeny and evolution of basidiomycetes",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "phylogenetic_tree" in types

    def test_suggest_protein_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "Show the protein structure from AlphaFold",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "protein_structure" in types

    def test_suggest_ecosystem_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "Model the ecosystem and mycelium network interactions",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "ecosystem_model" in types

    def test_suggest_reaction_query(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "What chemical reaction produces this yield?",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "chemical_reaction" in types

    def test_suggest_no_match(self, client):
        data = client.post("/api/widgets/suggest", json={
            "query": "Hello how are you?",
        }).json()
        assert data["status"] == "success"
        assert data["count"] == 0

    def test_suggest_max_five(self, client):
        # A query that matches many types
        data = client.post("/api/widgets/suggest", json={
            "query": "Show the species classification taxonomy with molecule structure and map location where found in ecosystem simulation",
        }).json()
        assert data["count"] <= 5


class TestWidgetGenerate:
    def test_generate_map_widget(self, client):
        data = client.post("/api/widgets/generate", json={
            "query": "Where are morels found?",
            "widget_type": "map",
            "parameters": {"center": [45.0, -122.0], "zoom": 5},
            "size": "large",
        }).json()
        assert data["status"] == "success"
        assert data["widget"]["widget_type"] == "map"
        assert data["widget"]["size"] == "large"

    def test_generate_taxonomy_tree(self, client):
        data = client.post("/api/widgets/generate", json={
            "query": "Agaricus bisporus classification",
            "widget_type": "taxonomy_tree",
            "parameters": {"root_taxon": "Fungi"},
        }).json()
        assert data["status"] == "success"
        assert data["widget"]["widget_type"] == "taxonomy_tree"

    def test_generate_species_card(self, client):
        data = client.post("/api/widgets/generate", json={
            "query": "Pleurotus ostreatus",
            "widget_type": "species_card",
            "parameters": {"scientific_name": "Pleurotus ostreatus", "common_name": "Oyster mushroom"},
        }).json()
        assert data["status"] == "success"
        assert data["widget"]["widget_type"] == "species_card"

    def test_generate_molecule(self, client):
        data = client.post("/api/widgets/generate", json={
            "query": "psilocybin molecule",
            "widget_type": "molecule_3d",
            "parameters": {"smiles": "C1=CC2=C(C=C1O)C(=CN2)CCN(C)P(=O)(O)O", "name": "Psilocybin"},
        }).json()
        assert data["status"] == "success"
        assert data["widget"]["widget_type"] == "molecule_3d"

    def test_generate_auto_suggest_type(self, client):
        data = client.post("/api/widgets/generate", json={
            "query": "Where is this species found?",
        }).json()
        assert data["status"] == "success"
        # Should auto-select map based on "where" and "found"

    def test_generate_no_match_returns_no_widget(self, client):
        data = client.post("/api/widgets/generate", json={
            "query": "hello world",
        }).json()
        assert data["status"] == "no_widget"

    def test_generate_generic_widget_type(self, client):
        """Widget types without custom generators get a generic widget."""
        data = client.post("/api/widgets/generate", json={
            "query": "data chart",
            "widget_type": "chart",
            "parameters": {"data": [1, 2, 3]},
        }).json()
        assert data["status"] == "success"
        assert data["widget"]["widget_type"] == "chart"


class TestWidgetBatch:
    def test_batch_returns_200(self, client):
        resp = client.post("/api/widgets/batch", json=[
            {"query": "Where are chanterelles found?", "widget_type": "map"},
            {"query": "Show Amanita taxonomy", "widget_type": "taxonomy_tree"},
        ])
        assert resp.status_code == 200

    def test_batch_returns_multiple(self, client):
        data = client.post("/api/widgets/batch", json=[
            {"query": "map location of species", "widget_type": "map"},
            {"query": "species card for Fungi", "widget_type": "species_card",
             "parameters": {"scientific_name": "Agaricus"}},
        ]).json()
        assert data["status"] == "success"
        assert data["count"] == 2

    def test_batch_max_ten(self, client):
        """Batch is capped at 10 widgets."""
        queries = [{"query": f"map of species {i}", "widget_type": "map"} for i in range(15)]
        data = client.post("/api/widgets/batch", json=queries).json()
        assert data["count"] <= 10


# ============================================================================
# STATIC Decoding API Tests (/api/static)
# ============================================================================


class TestStaticHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/static/health")
        assert resp.status_code == 200

    def test_health_has_framework(self, client):
        data = client.get("/api/static/health").json()
        assert data["status"] == "healthy"
        assert "STATIC" in data["framework"]
        assert "indexes_loaded" in data


class TestStaticIndexLifecycle:
    """Test building, listing, getting, and deleting indexes."""

    def test_build_index_from_sequences(self, client):
        resp = client.post("/api/static/indexes", json={
            "name": "test_seq_idx",
            "sequences": [[1, 2, 3], [1, 2, 4], [5, 6, 7]],
            "vocab_size": 100,
            "dense_depth": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "Built index" in data["message"]

    def test_build_index_from_strings(self, client):
        resp = client.post("/api/static/indexes/strings", json={
            "name": "test_str_idx",
            "valid_strings": ["Agaricus bisporus", "Pleurotus ostreatus", "Amanita muscaria"],
            "vocab_size": 256,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_list_indexes(self, client):
        resp = client.get("/api/static/indexes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["count"] >= 0

    def test_get_specific_index(self, client):
        # Build then get
        client.post("/api/static/indexes/strings", json={
            "name": "test_get_idx",
            "valid_strings": ["hello", "world"],
        })
        resp = client.get("/api/static/indexes/test_get_idx")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "index" in data

    def test_get_nonexistent_index_returns_404(self, client):
        resp = client.get("/api/static/indexes/nonexistent_index_xyz")
        assert resp.status_code == 404

    def test_delete_index(self, client):
        # Build then delete
        client.post("/api/static/indexes/strings", json={
            "name": "test_del_idx",
            "valid_strings": ["delete", "me"],
        })
        resp = client.delete("/api/static/indexes/test_del_idx")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/static/indexes/nonexistent_del_xyz")
        assert resp.status_code == 404

    def test_build_empty_sequences_returns_400(self, client):
        resp = client.post("/api/static/indexes", json={
            "name": "empty_idx",
            "sequences": [],
        })
        assert resp.status_code == 400

    def test_build_empty_strings_returns_400(self, client):
        resp = client.post("/api/static/indexes/strings", json={
            "name": "empty_str_idx",
            "valid_strings": [],
        })
        assert resp.status_code == 400


class TestStaticDecoding:
    def test_decode_against_index(self, client):
        # Build an index first
        client.post("/api/static/indexes", json={
            "name": "test_decode_idx",
            "sequences": [[10, 20, 30], [10, 20, 40]],
            "vocab_size": 100,
        })
        resp = client.post("/api/static/decode", json={
            "index_name": "test_decode_idx",
            "beam_width": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "result" in data

    def test_decode_nonexistent_index(self, client):
        resp = client.post("/api/static/decode", json={
            "index_name": "no_such_index",
            "beam_width": 4,
        })
        assert resp.status_code == 404


class TestStaticValidation:
    def test_validate_valid_sequence(self, client):
        client.post("/api/static/indexes", json={
            "name": "test_val_idx",
            "sequences": [[1, 2, 3], [4, 5, 6]],
            "vocab_size": 10,
        })
        resp = client.post("/api/static/validate", json={
            "index_name": "test_val_idx",
            "tokens": [1, 2, 3],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True

    def test_validate_invalid_sequence(self, client):
        resp = client.post("/api/static/validate", json={
            "index_name": "test_val_idx",
            "tokens": [9, 9, 9],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False

    def test_validate_nonexistent_index(self, client):
        resp = client.post("/api/static/validate", json={
            "index_name": "nonexistent_val",
            "tokens": [1, 2],
        })
        assert resp.status_code == 404


class TestStaticRerank:
    def test_rerank_candidates(self, client):
        client.post("/api/static/indexes/strings", json={
            "name": "test_rerank_idx",
            "valid_strings": ["Agaricus bisporus", "Pleurotus ostreatus"],
        })
        resp = client.post("/api/static/rerank", json={
            "index_name": "test_rerank_idx",
            "candidates": ["Agaricus bisporus", "Unknown species", "Pleurotus ostreatus"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["ranked"]) == 3
        # Valid candidates should be marked
        valid_candidates = [r for r in data["ranked"] if r["valid"]]
        assert len(valid_candidates) == 2

    def test_rerank_nonexistent_index(self, client):
        resp = client.post("/api/static/rerank", json={
            "index_name": "no_such_rerank",
            "candidates": ["test"],
        })
        assert resp.status_code == 404


class TestStaticMask:
    def test_get_logit_mask(self, client):
        client.post("/api/static/indexes", json={
            "name": "test_mask_idx",
            "sequences": [[1, 2, 3], [1, 4, 5]],
            "vocab_size": 10,
        })
        resp = client.post("/api/static/mask", json={
            "index_name": "test_mask_idx",
            "states": [0],
            "step": 0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "valid_tokens_per_beam" in data
        assert len(data["valid_tokens_per_beam"]) == 1
        # Token 1 should be valid at step 0 (both sequences start with 1)
        assert 1 in data["valid_tokens_per_beam"][0]

    def test_mask_nonexistent_index(self, client):
        resp = client.post("/api/static/mask", json={
            "index_name": "no_mask_idx",
            "states": [0],
            "step": 0,
        })
        assert resp.status_code == 404


class TestStaticDomains:
    def test_list_domains(self, client):
        resp = client.get("/api/static/domains")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "domains" in data
        assert data["total_domains"] > 0

    def test_domains_include_expected(self, client):
        data = client.get("/api/static/domains").json()
        domains = data["domains"]
        for expected in ["mindex", "taxonomy", "agents", "devices"]:
            assert expected in domains, f"Missing domain: {expected}"

    def test_domain_report_no_build(self, client):
        # Before any build, report should be None
        resp = client.get("/api/static/domains/report")
        assert resp.status_code == 200

    def test_build_single_domain(self, client):
        resp = client.post("/api/static/domains/build", json={
            "domain": "agents",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["domain"] == "agents"
        assert "indexes_built" in data

    def test_build_invalid_domain(self, client):
        resp = client.post("/api/static/domains/build", json={
            "domain": "nonexistent_domain",
        })
        assert resp.status_code == 400

    def test_build_all_domains(self, client):
        resp = client.post("/api/static/domains/build-all", json={
            "domains": ["agents", "devices"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "report" in data

    def test_validate_domain_entity(self, client):
        # First build the agents domain
        client.post("/api/static/domains/build", json={"domain": "agents"})
        # Now validate an entity
        resp = client.post("/api/static/domains/validate", json={
            "entity": "ceo_agent",
            "index_name": "agent_ids",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "valid" in data

    def test_validate_against_nonexistent_index(self, client):
        resp = client.post("/api/static/domains/validate", json={
            "entity": "test",
            "index_name": "nonexistent_domain_index_xyz",
        })
        assert resp.status_code == 404


# ============================================================================
# Unified Latents API Tests (/api/unified-latents)
# ============================================================================


class TestUnifiedLatentsHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/unified-latents/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "unified-latents"


class TestUnifiedLatentsInfo:
    def test_info_returns_200(self, client):
        resp = client.get("/api/unified-latents/info")
        assert resp.status_code == 200

    def test_info_has_framework(self, client):
        data = client.get("/api/unified-latents/info").json()
        assert data["framework"] == "Unified Latents (UL)"
        assert data["arxiv"] == "2602.17270"

    def test_info_has_benchmarks(self, client):
        data = client.get("/api/unified-latents/info").json()
        assert data["benchmarks"]["imagenet_512_fid"] == 1.4
        assert data["benchmarks"]["kinetics_600_fvd"] == 1.3

    def test_info_has_capabilities(self, client):
        data = client.get("/api/unified-latents/info").json()
        assert "generate_image" in data["capabilities"]
        assert "generate_video" in data["capabilities"]
        assert "encode_to_latent" in data["capabilities"]
        assert "decode_from_latent" in data["capabilities"]

    def test_info_has_gpu_node(self, client):
        data = client.get("/api/unified-latents/info").json()
        assert "gpu_node" in data


class TestUnifiedLatentsGenerateImage:
    def test_generate_image_returns_200(self, client):
        resp = client.post("/api/unified-latents/generate/image", json={
            "prompt": "A bioluminescent mushroom in a dark forest",
            "resolution": 512,
            "num_samples": 1,
        })
        assert resp.status_code == 200

    def test_generate_image_empty_prompt_rejected(self, client):
        resp = client.post("/api/unified-latents/generate/image", json={
            "prompt": "",
        })
        assert resp.status_code == 422  # Validation error

    def test_generate_image_result_structure(self, client):
        data = client.post("/api/unified-latents/generate/image", json={
            "prompt": "test image",
            "resolution": 256,
        }).json()
        assert "generation_id" in data
        assert "prompt" in data
        assert "output_paths" in data


class TestUnifiedLatentsGenerateVideo:
    def test_generate_video_returns_200(self, client):
        resp = client.post("/api/unified-latents/generate/video", json={
            "prompt": "Time-lapse of mycelium growth",
            "resolution": 256,
            "num_frames": 16,
        })
        assert resp.status_code == 200

    def test_generate_video_empty_prompt_rejected(self, client):
        resp = client.post("/api/unified-latents/generate/video", json={
            "prompt": "",
        })
        assert resp.status_code == 422


class TestUnifiedLatentsEncode:
    def test_encode_returns_200(self, client):
        resp = client.post("/api/unified-latents/encode", json={
            "input_path": "/data/images/mushroom_001.png",
        })
        assert resp.status_code == 200

    def test_encode_empty_path_rejected(self, client):
        resp = client.post("/api/unified-latents/encode", json={
            "input_path": "",
        })
        assert resp.status_code == 422


class TestUnifiedLatentsDecode:
    def test_decode_returns_200(self, client):
        resp = client.post("/api/unified-latents/decode", json={
            "latent_id": "lat_test_001",
        })
        assert resp.status_code == 200

    def test_decode_empty_id_rejected(self, client):
        resp = client.post("/api/unified-latents/decode", json={
            "latent_id": "",
        })
        assert resp.status_code == 422


class TestUnifiedLatentsTrain:
    def test_train_returns_200(self, client):
        resp = client.post("/api/unified-latents/train", json={
            "dataset": "imagenet-512",
            "batch_size": 32,
            "max_steps": 1000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data

    def test_train_then_get_status(self, client):
        data = client.post("/api/unified-latents/train", json={
            "dataset": "test-dataset",
            "max_steps": 100,
        }).json()
        run_id = data["run_id"]
        resp = client.get(f"/api/unified-latents/train/{run_id}")
        assert resp.status_code == 200

    def test_get_status_not_found(self, client):
        resp = client.get("/api/unified-latents/train/nonexistent_run_xyz")
        assert resp.status_code == 404


class TestUnifiedLatentsEvaluate:
    def test_evaluate_returns_200(self, client):
        resp = client.post("/api/unified-latents/evaluate", json={
            "checkpoint": "best_v1",
            "dataset": "imagenet-512",
            "num_samples": 100,
            "metrics": ["fid", "psnr"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data


# ============================================================================
# Cross-Router Integration Tests
# ============================================================================


class TestCrossRouterIntegration:
    """Test that routers work together correctly."""

    def test_all_health_endpoints_respond(self, client):
        """Every new router should have a working health endpoint."""
        health_endpoints = [
            "/api/economy/health",
            "/api/taxonomy/health",
            "/api/knowledge/health",
            "/api/widgets/health",
            "/api/static/health",
            "/api/unified-latents/health",
        ]
        for endpoint in health_endpoints:
            resp = client.get(endpoint)
            assert resp.status_code == 200, f"Health check failed for {endpoint}"
            data = resp.json()
            assert "status" in data, f"No status field in {endpoint}"

    def test_economy_charge_then_check_revenue(self, client):
        """Charging a client should affect revenue metrics."""
        # Charge
        client.post("/api/economy/charge", json={
            "client_id": "integration_test_client",
            "service_type": "deep_research",
            "amount": 5.0,
            "currency": "SOL",
        })
        # Check revenue
        rev = client.get("/api/economy/revenue").json()
        assert rev["total_revenue"] > 0

    def test_economy_charge_then_check_summary(self, client):
        """Summary should reflect transactions."""
        summary = client.get("/api/economy/summary").json()
        assert summary["total_transactions"] > 0

    def test_static_build_then_validate(self, client):
        """Build an index, then validate against it."""
        # Build
        client.post("/api/static/indexes/strings", json={
            "name": "integration_species",
            "valid_strings": ["Agaricus bisporus", "Pleurotus ostreatus"],
        })
        # Validate existing entity
        resp = client.post("/api/static/domains/validate", json={
            "entity": "Agaricus bisporus",
            "index_name": "integration_species",
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

        # Validate hallucinated entity
        resp2 = client.post("/api/static/domains/validate", json={
            "entity": "Fakeus speciesus",
            "index_name": "integration_species",
        })
        assert resp2.status_code == 200
        assert resp2.json()["valid"] is False

    def test_widget_suggest_taxonomy_related(self, client):
        """Widget suggestions for taxonomy queries should include taxonomy_tree."""
        data = client.post("/api/widgets/suggest", json={
            "query": "Show me the taxonomy classification of Amanita",
        }).json()
        types = [s["widget_type"] for s in data["suggestions"]]
        assert "taxonomy_tree" in types

    def test_app_startup_succeeds(self, app):
        """The app should have loaded without import errors."""
        assert app is not None
        assert app.title is not None

    def test_openapi_schema_generated(self, client):
        """OpenAPI schema should be generated without errors."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        paths = schema.get("paths", {})
        # Check new router paths exist in schema
        assert "/api/economy/health" in paths
        assert "/api/taxonomy/health" in paths
        assert "/api/widgets/health" in paths
        assert "/api/static/health" in paths
        assert "/api/unified-latents/health" in paths


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================


class TestEdgeCases:
    def test_economy_charge_x401_currency(self, client):
        """X401 (Mycosoft's own token) charges should work."""
        data = client.post("/api/economy/charge", json={
            "client_id": "x401_test",
            "service_type": "premium_query",
            "amount": 10.0,
            "currency": "X401",
        }).json()
        assert data["status"] == "completed"
        assert data["currency"] == "X401"

    def test_widget_batch_empty_list(self, client):
        data = client.post("/api/widgets/batch", json=[]).json()
        assert data["count"] == 0

    def test_static_decode_with_max_steps(self, client):
        client.post("/api/static/indexes", json={
            "name": "test_maxstep_idx",
            "sequences": [[1, 2], [3, 4]],
            "vocab_size": 10,
        })
        resp = client.post("/api/static/decode", json={
            "index_name": "test_maxstep_idx",
            "beam_width": 1,
            "max_steps": 2,
        })
        assert resp.status_code == 200

    def test_taxonomy_start_ingestion_custom_batch(self, client):
        data = client.post("/api/taxonomy/ingest/start",
                           params={"target": "plantae", "batch_size": 500}).json()
        assert data["target"] == "plantae"

    def test_economy_register_then_charge_with_tier_pricing(self, client):
        """A registered premium client should use premium tier pricing by default."""
        # Register
        client.post("/api/economy/clients/register",
                     params={"client_id": "premium_client_test", "tier": "premium"})
        # Charge without amount (should use tier default)
        data = client.post("/api/economy/charge", json={
            "client_id": "premium_client_test",
            "service_type": "simulation",
        }).json()
        assert data["amount"] == 0.01  # premium tier price
