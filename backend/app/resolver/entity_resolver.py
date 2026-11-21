"""Deterministic Entity Resolution Engine for FrontierAtlas Intelligence Graph.

Resolves noisy raw entity strings into canonical representations.
Example:
- 'OpenAI' -> 'OpenAI'
- 'Open AI' -> 'OpenAI'
- 'OpenAI, Inc.' -> 'OpenAI'
- 'OpenAI Inc' -> 'OpenAI'
- 'OpenAI LLC' -> 'OpenAI'

Incorporates:
- Seed database of 50+ frontier AI startups
- Unicode NFKC normalization
- Legal suffix stripping (Inc, LLC, Ltd, Corp, Technologies, Labs, etc.)
- Case and punctuation normalization
- Alias dictionary matching
- Token-set and Levenshtein similarity metric
- Detailed mapping audit log generation
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from app.models.schemas import EntityMappingLog
from app.resolver.seed_entities import SEED_CANONICAL_ENTITIES

# Common corporate / legal entity suffixes
LEGAL_SUFFIXES = [
    r"\binc\.?\b",
    r"\bllc\.?\b",
    r"\bltd\.?\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    r"\bpbc\.?\b",
    r"\bsas\.?\b",
    r"\bgmbh\.?\b",
    r"\bs\.?a\.?\b",
    r"\bholding\b",
    r"\bholdings\b",
]

COMPILED_LEGAL_SUFFIXES = [re.compile(pattern, re.IGNORECASE) for pattern in LEGAL_SUFFIXES]


class EntityResolver:
    """Production-grade deterministic entity resolver."""

    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
        self.canonical_entities: Dict[str, Dict] = {}
        self.alias_lookup: Dict[str, str] = {}  # normalized_alias -> canonical_name
        self.domain_lookup: Dict[str, str] = {}  # domain -> canonical_name
        self.mapping_history: List[EntityMappingLog] = []

        self._build_seed_indexes()

    def _normalize_string(self, text: str, strip_legal: bool = True) -> str:
        """Apply Unicode normalization, punctuation stripping, and lowercasing."""
        if not text:
            return ""

        # Unicode NFKC normalization
        norm = unicodedata.normalize("NFKC", text)

        # Lowercase
        norm = norm.lower()

        # Remove special punctuation & symbols, keep alphanumeric and basic spaces
        norm = re.sub(r"[^\w\s]", " ", norm)

        # Conditionally strip legal/corporate suffixes
        if strip_legal:
            for pattern in COMPILED_LEGAL_SUFFIXES:
                norm = pattern.sub(" ", norm)

        # Collapse whitespace
        norm = re.sub(r"\s+", " ", norm).strip()

        # Also strip spaces between single letters (e.g. 'open ai' -> 'openai' for indexing)
        return norm

    def _compact_string(self, text: str) -> str:
        """Strip all non-alphanumeric characters for aggressive canonical keying."""
        norm = self._normalize_string(text, strip_legal=True)
        return re.sub(r"[^a-z0-9]", "", norm)

    def _build_seed_indexes(self):
        """Build in-memory fast index from the seed database."""
        for item in SEED_CANONICAL_ENTITIES:
            canonical = item["canonical_name"]
            self.canonical_entities[canonical] = item

            # Index canonical name itself
            norm_canonical = self._normalize_string(canonical, strip_legal=False)
            compact_canonical = self._compact_string(canonical)
            self.alias_lookup[norm_canonical] = canonical
            self.alias_lookup[compact_canonical] = canonical

            # Index domain if available
            domain = item.get("domain")
            if domain:
                clean_dom = domain.lower().replace("www.", "").strip()
                self.domain_lookup[clean_dom] = canonical

            # Index aliases
            for alias in item.get("aliases", []):
                norm_alias = self._normalize_string(alias, strip_legal=False)
                compact_alias = self._compact_string(alias)
                self.alias_lookup[norm_alias] = canonical
                self.alias_lookup[compact_alias] = canonical

    @staticmethod
    def _levenshtein_similarity(s1: str, s2: str) -> float:
        """Calculate normalized Levenshtein similarity ratio between 0.0 and 1.0."""
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,       # deletion
                    dp[i][j - 1] + 1,       # insertion
                    dp[i - 1][j - 1] + cost  # substitution
                )

        distance = dp[m][n]
        max_len = max(m, n)
        return 1.0 - (distance / max_len)

    @staticmethod
    def _token_jaccard_similarity(s1: str, s2: str) -> float:
        """Token set Jaccard similarity."""
        set1 = set(s1.split())
        set2 = set(s2.split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def resolve(
        self,
        raw_name: str,
        entity_type: str = "STARTUP",
        source_url: Optional[str] = None,
    ) -> Tuple[str, EntityMappingLog]:
        """Resolve a raw entity string to its canonical representation.

        Returns:
            Tuple of (canonical_name, mapping_log_entry)
        """
        if not raw_name or not raw_name.strip():
            fallback_log = EntityMappingLog(
                raw_name=raw_name or "Unknown",
                canonical_name="Unknown",
                entity_type=entity_type,
                resolution_method="EMPTY_FALLBACK",
                confidence_score=0.0,
            )
            return "Unknown", fallback_log

        raw_trimmed = raw_name.strip()

        # Step 1: Direct Domain Match (if source URL provided)
        if source_url:
            for domain, canonical in self.domain_lookup.items():
                if domain in source_url.lower():
                    log = EntityMappingLog(
                        raw_name=raw_trimmed,
                        canonical_name=canonical,
                        entity_type=entity_type,
                        resolution_method="DOMAIN_MATCH",
                        confidence_score=1.0,
                    )
                    self.mapping_history.append(log)
                    return canonical, log

        # Step 2: Exact Canonical Match
        for canonical in self.canonical_entities:
            if raw_trimmed.lower() == canonical.lower():
                log = EntityMappingLog(
                    raw_name=raw_trimmed,
                    canonical_name=canonical,
                    entity_type=entity_type,
                    resolution_method="EXACT_SEED_MATCH",
                    confidence_score=1.0,
                )
                self.mapping_history.append(log)
                return canonical, log

        # Step 3: Fast Alias & Compact String Lookup
        norm_raw = self._normalize_string(raw_trimmed, strip_legal=False)
        compact_raw = self._compact_string(raw_trimmed)

        if norm_raw in self.alias_lookup:
            canonical = self.alias_lookup[norm_raw]
            log = EntityMappingLog(
                raw_name=raw_trimmed,
                canonical_name=canonical,
                entity_type=entity_type,
                resolution_method="ALIAS_DICTIONARY_MATCH",
                confidence_score=1.0,
            )
            self.mapping_history.append(log)
            return canonical, log

        if compact_raw in self.alias_lookup:
            canonical = self.alias_lookup[compact_raw]
            log = EntityMappingLog(
                raw_name=raw_trimmed,
                canonical_name=canonical,
                entity_type=entity_type,
                resolution_method="COMPACT_KEY_MATCH",
                confidence_score=0.98,
            )
            self.mapping_history.append(log)
            return canonical, log

        # Step 4: Legal Suffix Stripping & Normalization
        norm_stripped = self._normalize_string(raw_trimmed, strip_legal=True)
        compact_stripped = re.sub(r"[^a-z0-9]", "", norm_stripped)

        if compact_stripped in self.alias_lookup:
            canonical = self.alias_lookup[compact_stripped]
            log = EntityMappingLog(
                raw_name=raw_trimmed,
                canonical_name=canonical,
                entity_type=entity_type,
                resolution_method="LEGAL_SUFFIX_NORMALIZATION",
                confidence_score=0.95,
            )
            self.mapping_history.append(log)
            return canonical, log

        # Step 5: Fuzzy & Token-Set Similarity against Seed Catalog
        best_canonical = None
        best_score = 0.0

        for canonical, data in self.canonical_entities.items():
            norm_c = self._normalize_string(canonical, strip_legal=True)
            lev_sim = self._levenshtein_similarity(norm_stripped, norm_c)
            tok_sim = self._token_jaccard_similarity(norm_stripped, norm_c)
            combined_score = max(lev_sim, (lev_sim * 0.7 + tok_sim * 0.3))

            if combined_score > best_score:
                best_score = combined_score
                best_canonical = canonical

        if best_canonical and best_score >= self.confidence_threshold:
            log = EntityMappingLog(
                raw_name=raw_trimmed,
                canonical_name=best_canonical,
                entity_type=entity_type,
                resolution_method="FUZZY_STRING_SIMILARITY",
                confidence_score=round(best_score, 4),
            )
            self.mapping_history.append(log)
            return best_canonical, log

        # Step 6: Clean Fallback (New Canonical Entity Formed)
        # Format as clean title case with legal suffixes stripped
        clean_new_canonical = " ".join(word.capitalize() for word in norm_stripped.split())
        if not clean_new_canonical:
            clean_new_canonical = raw_trimmed

        # Register dynamically so subsequent variations resolve to this same entity
        compact_new = self._compact_string(clean_new_canonical)
        self.alias_lookup[compact_new] = clean_new_canonical

        log = EntityMappingLog(
            raw_name=raw_trimmed,
            canonical_name=clean_new_canonical,
            entity_type=entity_type,
            resolution_method="DYNAMIC_CANONICAL_CREATION",
            confidence_score=0.80,
        )
        self.mapping_history.append(log)
        return clean_new_canonical, log

    def get_mapping_logs(self) -> List[EntityMappingLog]:
        """Return audit trail of all mappings performed."""
        return self.mapping_history


# Singleton resolver instance
entity_resolver = EntityResolver()
