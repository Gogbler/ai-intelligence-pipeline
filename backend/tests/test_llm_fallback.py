"""Unit tests for Multi-Tier LLM Fallback Chain."""

import asyncio
from app.llm.orchestrator import LLMOrchestrator


def test_fallback_to_deterministic_extractor():
    orchestrator = LLMOrchestrator()
    # Force remote providers off
    orchestrator.gemini.api_key = ""
    orchestrator.groq.api_key = ""
    orchestrator.deepseek.api_key = ""

    html_sample = """
    <html>
        <body>
            <h1>Nova Intelligence Inc</h1>
            <p>Nova Intelligence builds autonomous data pipelines for AI teams.</p>
            <p>Our team has 45 employees across San Francisco.</p>
            <p>Pricing: We offer a Free Tier and an Enterprise Plan.</p>
        </body>
    </html>
    """

    res = asyncio.run(
        orchestrator.extract(
            raw_content=html_sample,
            system_instruction="Extract structured startup and product data.",
            user_prompt="Extract entityName, employeeCount, and pricingModel.",
        )
    )

    assert "entityName" in res
    assert res["employeeCount"] == 45
    assert res["pricingModel"] in ["FREE", "ENTERPRISE", "PAID", "FREEMIUM"]
    assert orchestrator.metrics["fallback_calls"] >= 1
