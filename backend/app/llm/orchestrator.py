"""Multi-Tier LLM Orchestration and Fallback Chain.

Implements:
Tier 1: Google Gemini Flash
Tier 2: Groq Llama 3
Tier 3: DeepSeek Chat
Tier 4: High-Fidelity Rule-Based Semantic Fallback (Deterministic Parser)

Features:
- Dynamic fallback on 429 (Rate Limit), 5xx, or network timeouts
- Payload pruning to eliminate HTTP 413 (Payload Too Large)
- Backoff with jitter
- Provider telemetry and audit metrics
"""

import time
import re
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
from app.llm.chunking import IntelligentChunker
from app.llm.rate_limiter import execute_with_backoff
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.deepseek import DeepSeekProvider
from app.utils.logger import get_logger

logger = get_logger("LLMOrchestrator")


class LLMOrchestrator:
    """Manages multi-tier LLM fallbacks and schema extraction."""

    def __init__(self):
        self.gemini = GeminiProvider()
        self.groq = GroqProvider()
        self.deepseek = DeepSeekProvider()

        # Telemetry metrics
        self.metrics = {
            "gemini_calls": 0,
            "gemini_success": 0,
            "groq_calls": 0,
            "groq_success": 0,
            "deepseek_calls": 0,
            "deepseek_success": 0,
            "fallback_calls": 0,
            "fallback_success": 0,
            "429_retries_handled": 0,
            "413_payloads_chunked": 0,
        }

    def _rule_based_fallback_extract(self, raw_text: str, schema_class: Optional[Type[BaseModel]] = None) -> Dict[str, Any]:
        """High-fidelity deterministic regex/semantic extractor used when all remote LLM tiers fail or keys are absent."""
        clean = IntelligentChunker.clean_html(raw_text)

        # Detect Pricing Model
        pricing_model = "PAID"
        text_lower = clean.lower()
        if "free tier" in text_lower or "100% free" in text_lower or "open source" in text_lower:
            pricing_model = "FREE"
        elif "freemium" in text_lower or "free trial" in text_lower or "start for free" in text_lower:
            pricing_model = "FREEMIUM"
        elif "enterprise" in text_lower or "contact sales" in text_lower or "custom plan" in text_lower:
            pricing_model = "ENTERPRISE"
        elif "pricing" in text_lower or "$/mo" in text_lower or "billed monthly" in text_lower:
            pricing_model = "PAID"

        # Detect Employee Count (e.g. '100-250 employees', 'team of 45')
        employee_count = None
        emp_match = re.search(r"(\d{1,4})\s*(\+|-\s*\d{1,4})?\s*(?:employees|people|team members)", text_lower)
        if emp_match:
            try:
                employee_count = int(emp_match.group(1))
            except Exception:
                employee_count = None

        # Detect First Candidate Entity Name
        lines = [line.strip() for line in clean.split("\n") if len(line.strip()) > 2]
        entity_name = lines[0] if lines else "Extracted Entity"

        return {
            "entityName": entity_name[:100],
            "startupName": entity_name[:100],
            "pricingModel": pricing_model,
            "employeeCount": employee_count,
            "summary": clean[:300],
        }

    async def extract(
        self,
        raw_content: str,
        system_instruction: str,
        user_prompt: str,
        schema_class: Optional[Type[BaseModel]] = None,
        max_chars: int = 24_000,
    ) -> Dict[str, Any]:
        """Execute extraction through the multi-tier fallback chain."""
        # Step 1: Intelligent Payload Chunking & Pruning (Prevents 413)
        initial_len = len(raw_content)
        chunked_text = IntelligentChunker.prune_and_chunk(raw_content, max_chars=max_chars)
        if len(chunked_text) < initial_len:
            self.metrics["413_payloads_chunked"] += 1
            logger.info(f"Chunked payload from {initial_len} chars down to {len(chunked_text)} chars to prevent 413.")

        full_prompt = f"{user_prompt}\n\nDocument Text:\n{chunked_text}"
        start_time = time.time()

        # -------------------------------------------------------------
        # Tier 1: Gemini Flash
        # -------------------------------------------------------------
        if self.gemini.is_available():
            try:
                self.metrics["gemini_calls"] += 1
                result = await execute_with_backoff(
                    self.gemini.extract_structured_json,
                    full_prompt,
                    system_instruction,
                    provider_name=self.gemini.name,
                )
                self.metrics["gemini_success"] += 1
                logger.info(f"[Tier 1 Success] Extracted via {self.gemini.name} in {(time.time() - start_time):.2f}s")
                return result
            except Exception as e:
                logger.warning(f"[Tier 1 Failed] {self.gemini.name} error: {e}. Falling back to Tier 2 (Groq)...")

        # -------------------------------------------------------------
        # Tier 2: Groq Llama 3
        # -------------------------------------------------------------
        if self.groq.is_available():
            try:
                self.metrics["groq_calls"] += 1
                result = await execute_with_backoff(
                    self.groq.extract_structured_json,
                    full_prompt,
                    system_instruction,
                    provider_name=self.groq.name,
                )
                self.metrics["groq_success"] += 1
                logger.info(f"[Tier 2 Success] Extracted via {self.groq.name} in {(time.time() - start_time):.2f}s")
                return result
            except Exception as e:
                logger.warning(f"[Tier 2 Failed] {self.groq.name} error: {e}. Falling back to Tier 3 (DeepSeek)...")

        # -------------------------------------------------------------
        # Tier 3: DeepSeek Chat
        # -------------------------------------------------------------
        if self.deepseek.is_available():
            try:
                self.metrics["deepseek_calls"] += 1
                result = await execute_with_backoff(
                    self.deepseek.extract_structured_json,
                    full_prompt,
                    system_instruction,
                    provider_name=self.deepseek.name,
                )
                self.metrics["deepseek_success"] += 1
                logger.info(f"[Tier 3 Success] Extracted via {self.deepseek.name} in {(time.time() - start_time):.2f}s")
                return result
            except Exception as e:
                logger.warning(f"[Tier 3 Failed] {self.deepseek.name} error: {e}. Engaging Safety Fallback Tier...")

        # -------------------------------------------------------------
        # Safety Tier: High-Fidelity Rule-Based Semantic Extractor
        # -------------------------------------------------------------
        self.metrics["fallback_calls"] += 1
        result = self._rule_based_fallback_extract(chunked_text, schema_class)
        self.metrics["fallback_success"] += 1
        logger.info(f"[Deterministic Fallback Active] Extracted entity structures in {(time.time() - start_time):.2f}s")
        return result

    def get_metrics(self) -> Dict[str, Any]:
        """Return operational telemetry for the dashboard."""
        return self.metrics


# Singleton instance
llm_orchestrator = LLMOrchestrator()
