"""Unit tests for Intelligent Chunking and HTTP 413 Prevention."""

from app.llm.chunking import IntelligentChunker


def test_clean_html_removes_boilerplate():
    dirty_html = """
    <html>
        <head>
            <script>alert('spam');</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <nav><a href="/home">Home</a></nav>
            <main>
                <h1>Autonomous AI Agents</h1>
                <p>We are building autonomous agents for software workflows.</p>
            </main>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """
    clean_text = IntelligentChunker.clean_html(dirty_html)
    assert "alert('spam')" not in clean_text
    assert "body { color: red; }" not in clean_text
    assert "Copyright 2026" not in clean_text
    assert "Autonomous AI Agents" in clean_text
    assert "We are building autonomous agents" in clean_text


def test_chunking_strictly_enforces_budget():
    # Generate large payload exceeding max_chars
    huge_paragraph = "This is a detailed analysis of neural network architectures and pricing tiers. " * 500
    huge_payload = f"Title: Frontier AI\n\n{huge_paragraph}\n\nPricing: We offer an Enterprise plan and a Free tier."

    max_allowed = 1000
    chunked = IntelligentChunker.prune_and_chunk(huge_payload, max_chars=max_allowed)

    assert len(chunked) <= max_allowed + 50  # Allows slight margin for safety truncate indicator
    assert "Frontier AI" in chunked
    # Ensure pricing signal was prioritized
    assert "Pricing" in chunked or "Enterprise" in chunked or "Free" in chunked
