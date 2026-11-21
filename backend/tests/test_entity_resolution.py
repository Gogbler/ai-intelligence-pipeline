"""Unit tests for Deterministic Entity Resolution."""

from app.resolver.entity_resolver import EntityResolver


def test_openai_canonicalization():
    resolver = EntityResolver()

    variants = [
        "OpenAI",
        "Open AI",
        "OpenAI, Inc.",
        "OpenAI Inc",
        "OpenAI LLC",
        "OpenAI Global LLC",
        "open ai inc.",
    ]

    for variant in variants:
        canonical, log = resolver.resolve(variant, entity_type="STARTUP")
        assert canonical == "OpenAI", f"Expected 'OpenAI' for '{variant}', got '{canonical}'"
        assert log.canonical_name == "OpenAI"
        assert log.confidence_score >= 0.90


def test_other_seed_canonicalizations():
    resolver = EntityResolver()

    cases = [
        ("Anthropic PBC", "Anthropic"),
        ("Anthropic, Inc.", "Anthropic"),
        ("DeepMind", "Google DeepMind"),
        ("Google Brain", "Google DeepMind"),
        ("Mistral AI SAS", "Mistral AI"),
        ("Mistral.ai", "Mistral AI"),
        ("Scale Media Inc.", "Scale AI"),
        ("ScaleAI", "Scale AI"),
        ("Perplexity AI, Inc.", "Perplexity AI"),
        ("Stability AI Ltd", "Stability AI"),
        ("Weights and Biases", "Weights & Biases"),
        ("Cursor Editor", "Cursor"),
    ]

    for raw, expected in cases:
        canonical, log = resolver.resolve(raw)
        assert canonical == expected, f"Failed for raw='{raw}': expected '{expected}', got '{canonical}'"
        assert log.confidence_score >= 0.85


def test_domain_matching():
    resolver = EntityResolver()
    canonical, log = resolver.resolve(
        raw_name="Some Obscure Subsidiary",
        source_url="https://openai.com/research/index",
    )
    assert canonical == "OpenAI"
    assert log.resolution_method == "DOMAIN_MATCH"
    assert log.confidence_score == 1.0


def test_new_unknown_entity_normalization():
    resolver = EntityResolver()
    raw = "Quantum Neural Systems, LLC."
    canonical, log = resolver.resolve(raw)

    # Legal suffixes stripped, cleanly title-cased
    assert "LLC" not in canonical
    assert canonical == "Quantum Neural Systems"
    assert log.resolution_method in ("LEGAL_SUFFIX_NORMALIZATION", "DYNAMIC_CANONICAL_CREATION")
