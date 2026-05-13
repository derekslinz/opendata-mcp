import pkgutil

import meta_data_mcp.providers as providers_pkg
from meta_data_mcp.registry import (
    DOMAINS,
    REGIONS,
    REGISTRY,
    _check_registry_vocabulary,
    all_ids,
    find_providers,
    get_provider,
    list_domains,
    list_regions,
)


def test_registry_is_non_empty():
    assert len(REGISTRY) >= 50


def test_registry_ids_are_unique():
    ids = [entry.id for entry in REGISTRY]
    assert len(ids) == len(set(ids))


def test_registry_server_names_are_unique():
    names = [entry.server_name for entry in REGISTRY]
    assert len(names) == len(set(names))


def test_registry_uses_known_vocabulary():
    warnings = list(_check_registry_vocabulary())
    assert warnings == [], f"Registry has out-of-vocabulary terms: {warnings}"


def test_every_registry_id_matches_a_provider_module():
    discovered = {
        name
        for _, name, _ in pkgutil.iter_modules(providers_pkg.__path__)
        if not name.startswith("__")
    }
    missing = [entry.id for entry in REGISTRY if entry.id not in discovered]
    assert missing == [], f"Registry references missing provider modules: {missing}"


def test_every_provider_module_has_a_registry_entry():
    """Every provider module SHOULD have a registry entry. New providers
    must be added to the registry so they're discoverable via the meta
    aggregator."""
    discovered = {
        name
        for _, name, _ in pkgutil.iter_modules(providers_pkg.__path__)
        if not name.startswith("__")
        and name not in ("meta_data_mcp", "meta_data_mcp_all")
    }
    registry_ids = set(all_ids())
    orphaned = sorted(discovered - registry_ids)
    assert orphaned == [], (
        f"Provider modules missing from registry: {orphaned}. "
        "Add an entry to meta_data_mcp/registry.py REGISTRY tuple."
    )


def test_find_providers_query_match():
    results = find_providers(query="earthquake")
    assert any(entry.id == "us_usgs_earthquake" for entry in results)


def test_find_providers_keyword_bonus_outranks_general_match():
    """A keyword exact-match should rank higher than a substring hit elsewhere."""
    results = find_providers(query="fx")
    # Frankfurter and ECB both have 'fx' in keywords; they should be at the top.
    top_ids = {entry.id for entry in results[:3]}
    assert "global_frankfurter" in top_ids


def test_find_providers_domain_filter():
    results = find_providers(domain="health")
    assert all("health" in entry.domains for entry in results)


def test_find_providers_region_filter():
    results = find_providers(region="uk")
    assert all("uk" in entry.regions for entry in results)


def test_find_providers_unknown_query_returns_empty():
    assert find_providers(query="zzzzzz_unknown") == []


def test_find_providers_no_filters_returns_full_list_up_to_limit():
    results = find_providers(limit=200)
    assert len(results) == len(REGISTRY)


def test_get_provider_known():
    entry = get_provider("us_nasa")
    assert entry is not None
    assert entry.title.startswith("NASA")


def test_get_provider_unknown_returns_none():
    assert get_provider("not_a_provider") is None


def test_list_domains_is_subset_of_controlled_vocabulary():
    assert set(list_domains()).issubset(set(DOMAINS))


def test_list_regions_is_subset_of_controlled_vocabulary():
    assert set(list_regions()).issubset(set(REGIONS))
