"""LLM integration for reasoning tasks (Grok primary, Claude fallback)."""

import json
import logging
from typing import Optional

from src.config import settings


class LLMClient:
    """Unified interface for xAI Grok or Claude API."""

    def __init__(self):
        """Initialize LLM client based on configuration."""
        self.logger = logging.getLogger("llm")
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model

        if self.provider == "xai":
            self._init_grok()
        elif self.provider == "anthropic":
            self._init_claude()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _init_grok(self):
        """Initialize xAI Grok client."""
        try:
            # Note: xai-sdk package needs to be installed
            # Placeholder for xAI Grok integration
            self.client = None  # Will be set when xAI SDK available
            self.logger.info("Grok client initialized (placeholder)")
        except ImportError:
            self.logger.warning("xAI SDK not available, falling back to Claude")
            self._init_claude()

    def _init_claude(self):
        """Initialize Anthropic Claude client."""
        try:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=settings.anthropic_api_key)
            self.logger.info(f"Claude client initialized ({self.model})")
        except ImportError:
            raise ImportError("anthropic package not installed")

    async def reason_about_invoice(
        self, vendor: str, amount: float, items: list, validation_issues: list
    ) -> dict:
        """
        Use LLM to reason about approval decision (generator phase).

        Args:
            vendor: Vendor name
            amount: Invoice amount
            items: List of line items
            validation_issues: List of validation issues found

        Returns:
            Dict with reasoning, risk factors, and recommendation
        """
        if self.provider == "xai" and self.client is None:
            return self._grok_placeholder_reasoning(vendor, amount, validation_issues)

        prompt = self._build_reasoning_prompt(vendor, amount, items, validation_issues)
        return await self._call_claude_reasoning(prompt)

    async def critique_approval(self, reasoning: dict) -> dict:
        """
        Use LLM to critique the approval recommendation (critic phase).

        Args:
            reasoning: Previous reasoning output

        Returns:
            Dict with critique, identified flaws
        """
        if self.provider == "xai" and self.client is None:
            return self._grok_placeholder_critique(reasoning)

        prompt = self._build_critique_prompt(reasoning)
        return await self._call_claude_critique(prompt)

    async def revise_approval(self, reasoning: dict, critique: dict) -> dict:
        """
        Use LLM to revise recommendation based on critique (revision phase).

        Args:
            reasoning: Original reasoning
            critique: Critique feedback

        Returns:
            Dict with revised reasoning and confidence
        """
        if self.provider == "xai" and self.client is None:
            return self._grok_placeholder_revision(reasoning, critique)

        prompt = self._build_revision_prompt(reasoning, critique)
        return await self._call_claude_revision(prompt)

    # Claude Integration Methods
    async def _call_claude_reasoning(self, prompt: str) -> dict:
        """Call Claude for invoice reasoning."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text
            return self._parse_json_response(text, "reasoning")
        except Exception as e:
            self.logger.error(f"Claude reasoning failed: {str(e)}")
            return {
                "analysis": "Error during reasoning",
                "risk_factors": [],
                "recommendation": "require_manual_review",
                "confidence": 0.0,
            }

    async def _call_claude_critique(self, prompt: str) -> dict:
        """Call Claude for critique."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text
            return self._parse_json_response(text, "critique")
        except Exception as e:
            self.logger.error(f"Claude critique failed: {str(e)}")
            return {"has_flaws": False, "flaws": [], "severity": "none"}

    async def _call_claude_revision(self, prompt: str) -> dict:
        """Call Claude for revision."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text
            return self._parse_json_response(text, "revision")
        except Exception as e:
            self.logger.error(f"Claude revision failed: {str(e)}")
            return {
                "analysis": "Error during revision",
                "recommendation": "require_manual_review",
                "confidence": 0.0,
            }

    # Prompt Builders
    def _build_reasoning_prompt(
        self, vendor: str, amount: float, items: list, issues: list
    ) -> str:
        """Build prompt for approval reasoning."""
        items_str = "\n".join([f"  - {item}" for item in items])
        issues_str = "\n".join([f"  - {issue}" for issue in issues]) if issues else "  None"

        return f"""You are an approval specialist for invoice processing. Analyze this invoice and recommend approval or rejection.

Vendor: {vendor}
Amount: ${amount:.2f}
Items:
{items_str}

Validation Issues:
{issues_str}

Provide your analysis and recommendation in JSON format:
{{
  "analysis": "your detailed analysis",
  "risk_factors": ["factor1", "factor2"],
  "recommendation": "approve" or "reject" or "require_manual_review",
  "confidence": 0.0 to 1.0
}}"""

    def _build_critique_prompt(self, reasoning: dict) -> str:
        """Build prompt for critiquing the recommendation."""
        return f"""Review this approval recommendation and identify any flaws or concerns:

Recommendation: {reasoning.get('recommendation')}
Analysis: {reasoning.get('analysis')}
Confidence: {reasoning.get('confidence')}

Provide critique in JSON format:
{{
  "has_flaws": true/false,
  "flaws": ["flaw1", "flaw2"],
  "severity": "critical", "high", "medium", "low", or "none",
  "suggestions": "improvement suggestions if any"
}}"""

    def _build_revision_prompt(self, reasoning: dict, critique: dict) -> str:
        """Build prompt for revising based on critique."""
        return f"""Revise this approval recommendation based on the critique:

Original Recommendation: {reasoning.get('recommendation')}
Original Analysis: {reasoning.get('analysis')}

Critique:
{critique.get('flaws')}

Severity: {critique.get('severity')}

Provide revised recommendation in JSON format:
{{
  "analysis": "revised analysis",
  "recommendation": "approve", "reject", or "require_manual_review",
  "confidence": 0.0 to 1.0,
  "changes_made": "summary of what changed"
}}"""

    # Placeholder Methods (for Grok when SDK unavailable)
    def _grok_placeholder_reasoning(
        self, vendor: str, amount: float, issues: list
    ) -> dict:
        """Placeholder Grok reasoning (for development)."""
        self.logger.debug(
            f"[GROK PLACEHOLDER] Reasoning for {vendor}, ${amount:.2f}, {len(issues)} issues"
        )

        has_issues = len(issues) > 0
        high_amount = amount > 10000

        return {
            "analysis": f"Invoice from {vendor} for ${amount:.2f}. Validation issues: {len(issues)}. High-value: {high_amount}.",
            "risk_factors": (
                ["validation_failures", "high_amount"] if has_issues or high_amount else []
            ),
            "recommendation": "require_manual_review" if (has_issues or high_amount) else "approve",
            "confidence": 0.7 if has_issues or high_amount else 0.85,
        }

    def _grok_placeholder_critique(self, reasoning: dict) -> dict:
        """Placeholder Grok critique (for development)."""
        self.logger.debug(f"[GROK PLACEHOLDER] Critiquing recommendation")

        has_issues = len(reasoning.get("risk_factors", [])) > 0

        return {
            "has_flaws": has_issues,
            "flaws": reasoning.get("risk_factors", []),
            "severity": "high" if has_issues else "none",
            "suggestions": "Consider stricter validation" if has_issues else "No changes needed",
        }

    def _grok_placeholder_revision(self, reasoning: dict, critique: dict) -> dict:
        """Placeholder Grok revision (for development)."""
        self.logger.debug(f"[GROK PLACEHOLDER] Revising based on critique")

        # If critique found flaws, revise recommendation
        if critique.get("has_flaws"):
            revised_rec = "require_manual_review"
            confidence = 0.6
        else:
            revised_rec = reasoning.get("recommendation")
            confidence = min(reasoning.get("confidence", 0.7) + 0.1, 0.95)

        return {
            "analysis": reasoning.get("analysis", "")
            + " [REVISED based on critique]",
            "recommendation": revised_rec,
            "confidence": confidence,
            "changes_made": f"Revised from {reasoning.get('recommendation')} to {revised_rec}",
        }

    # Utility Methods
    def _parse_json_response(self, text: str, context: str = "") -> dict:
        """Extract and parse JSON from LLM response."""
        try:
            # Try to find JSON in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        self.logger.warning(f"Failed to parse JSON from {context} response")
        return {}
