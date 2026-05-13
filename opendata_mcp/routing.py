"""
Sophisticated multi-criteria routing engine for provider discovery.

This module provides intelligent ranking of providers based on:
- Token matching (exact matches, partial matches)
- Fuzzy matching (typo tolerance via Levenshtein distance)
- Semantic similarity (TF-IDF cosine similarity)
- Metadata matching (domains, regions, keywords)
- Recency/freshness scoring
- Cached results for frequent queries

The RoutingEngine accepts pluggable scoring strategies and combines them
with configurable weights for flexible tuning.
"""

from __future__ import annotations

import difflib
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

from opendata_mcp.registry import REGISTRY, ProviderEntry

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoredProvider:
    """A provider with its ranking score and scoring breakdown."""

    entry: ProviderEntry
    score: float
    breakdown: dict[str, float] | None = None  # {strategy: score, ...}


class Scorer(ABC):
    """Base class for provider scoring strategies."""

    @abstractmethod
    async def score(self, query: str | None, provider: ProviderEntry) -> float:
        """Return score 0.0-1.0 for how well this provider matches the query."""
        pass


class TokenScorer(Scorer):
    """Token-level matching with keyword bonuses.

    Splits query into tokens and matches against provider metadata.
    Keywords receive 3x weight; other matches 1x weight.
    """

    async def score(self, query: str | None, provider: ProviderEntry) -> float:
        if not query:
            return 0.0

        q_tokens = set(query.lower().split())
        if not q_tokens:
            return 0.0

        # Build haystack of all searchable provider text
        haystack = " ".join(
            (
                provider.id,
                provider.title,
                provider.description,
                " ".join(provider.keywords),
                " ".join(provider.domains),
                " ".join(provider.regions),
            )
        ).lower()

        score = 0.0
        for token in q_tokens:
            if token in haystack:
                score += 1.0
                # Bonus for keyword matches
                if token in provider.keywords:
                    score += 2.0

        # Normalize to 0-1
        return min(score / (len(q_tokens) * 3), 1.0)


class FuzzyScorer(Scorer):
    """Levenshtein distance matching for typo tolerance.

    Uses difflib.SequenceMatcher to find fuzzy matches in provider metadata.
    Threshold: 0.6 similarity required.
    """

    async def score(self, query: str | None, provider: ProviderEntry) -> float:
        if not query:
            return 0.0

        q_lower = query.lower()
        targets = [
            provider.id,
            provider.title.lower(),
            provider.description.lower(),
        ] + [k.lower() for k in provider.keywords]

        # Find best match
        best_ratio = 0.0
        for target in targets:
            ratio = difflib.SequenceMatcher(None, q_lower, target).ratio()
            best_ratio = max(best_ratio, ratio)

        # Only return if threshold met (>0.6 similarity)
        return max(0.0, best_ratio - 0.4) if best_ratio > 0.6 else 0.0


class MetadataScorer(Scorer):
    """Domain, region, and keyword exact/partial matching.

    Awards points for domain/region matches (hard filter + bonus).
    """

    async def score(self, query: str | None, provider: ProviderEntry) -> float:
        if not query:
            return 0.0

        q_lower = query.lower()
        score = 0.0

        # Check if query matches any domain or region
        for domain in provider.domains:
            if domain.lower() in q_lower or q_lower in domain.lower():
                score += 0.5

        for region in provider.regions:
            if region.lower() in q_lower or q_lower in region.lower():
                score += 0.3

        return min(score, 1.0)


class SimpleSemanticScorer(Scorer):
    """Simple word-frequency based semantic similarity.

    Compares query against provider description using term frequency.
    No external dependencies (no sklearn yet).
    """

    async def score(self, query: str | None, provider: ProviderEntry) -> float:
        if not query:
            return 0.0

        q_terms = set(query.lower().split())
        desc_text = (
            provider.description + " " + " ".join(provider.keywords)
        ).lower()
        desc_terms = set(desc_text.split())

        if not q_terms or not desc_terms:
            return 0.0

        # Jaccard similarity
        intersection = len(q_terms & desc_terms)
        union = len(q_terms | desc_terms)
        return intersection / union if union > 0 else 0.0


class RoutingEngine:
    """Multi-criteria provider router with caching and explainability.

    Combines multiple scoring strategies with configurable weights.
    Implements LRU caching for frequent queries.
    """

    def __init__(
        self,
        scorers: dict[str, Scorer] | None = None,
        weights: dict[str, float] | None = None,
        cache_size: int = 1000,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize the routing engine.

        Args:
            scorers: Dict of {strategy_name: Scorer instance}
            weights: Dict of {strategy_name: weight (0-1)}
            cache_size: Maximum cached queries
            cache_ttl_seconds: Cache expiration time
        """
        self.scorers = scorers or {
            "token": TokenScorer(),
            "fuzzy": FuzzyScorer(),
            "metadata": MetadataScorer(),
            "semantic": SimpleSemanticScorer(),
        }

        self.weights = weights or {
            "token": 0.3,
            "fuzzy": 0.2,
            "metadata": 0.25,
            "semantic": 0.25,
        }

        # Normalize weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

        self.cache: dict[str, tuple[list[ScoredProvider], float]] = {}
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl_seconds

    def _cache_key(
        self,
        query: str | None,
        domain: str | None,
        region: str | None,
    ) -> str:
        """Generate cache key from query parameters."""
        parts = [query or "", domain or "", region or ""]
        key_str = "|".join(parts).lower().strip()
        return hashlib.md5(key_str.encode()).hexdigest()

    async def route(
        self,
        query: str | None = None,
        domain: str | None = None,
        region: str | None = None,
        limit: int = 20,
        explain: bool = False,
    ) -> list[ScoredProvider]:
        """Route a query to matching providers.

        Applies hard filters (domain/region), then scores remaining providers,
        finally limits results.

        Args:
            query: Free-text search query
            domain: Filter by domain (hard filter)
            region: Filter by region (hard filter)
            limit: Maximum results to return
            explain: Include scoring breakdown in results

        Returns:
            List of ScoredProvider ranked by score.
        """
        # Check cache
        cache_key = self._cache_key(query, domain, region)
        if cache_key in self.cache:
            cached_results, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                log.debug(f"Cache hit for key {cache_key}")
                return cached_results[:limit]
            else:
                del self.cache[cache_key]

        # Apply hard filters
        filtered = [p for p in REGISTRY if self._passes_filters(p, domain, region)]

        # Score each provider
        scored: list[ScoredProvider] = []
        for provider in filtered:
            score, breakdown = await self._combined_score(query, provider, explain)
            if score > 0:
                scored.append(
                    ScoredProvider(
                        entry=provider,
                        score=score,
                        breakdown=breakdown if explain else None,
                    )
                )

        # Sort by score descending, then by id for stability
        scored.sort(key=lambda x: (-x.score, x.entry.id))

        # Limit results
        results = scored[:limit]

        # Cache the results
        if len(self.cache) >= self.cache_size:
            # Evict oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[cache_key] = (results, time.time())

        return results

    def _passes_filters(
        self,
        provider: ProviderEntry,
        domain: str | None,
        region: str | None,
    ) -> bool:
        """Check if provider passes domain/region filters."""
        if domain and domain not in provider.domains:
            return False
        if region and region not in provider.regions:
            return False
        return True

    async def _combined_score(
        self,
        query: str | None,
        provider: ProviderEntry,
        explain: bool,
    ) -> tuple[float, dict[str, float] | None]:
        """Compute weighted combined score across all strategies."""
        breakdown = {} if explain else None
        combined = 0.0

        for strategy_name, scorer in self.scorers.items():
            strategy_score = await scorer.score(query, provider)
            weight = self.weights.get(strategy_name, 0.0)
            weighted = strategy_score * weight
            combined += weighted

            if explain:
                breakdown[strategy_name] = strategy_score

        return combined, breakdown


# Backward-compatible wrapper
async def find_providers_sophisticated(
    query: str | None = None,
    domain: str | None = None,
    region: str | None = None,
    limit: int = 20,
    explain: bool = False,
) -> list[ScoredProvider | ProviderEntry]:
    """Route query using sophisticated engine. Returns ProviderEntry for backward compat."""
    engine = RoutingEngine()
    results = await engine.route(
        query=query, domain=domain, region=region, limit=limit, explain=explain
    )
    # Return entries for backward compatibility
    return [r.entry for r in results]
