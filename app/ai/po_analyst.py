"""
ProcureFlow AI — Purchase Order AI Analyst
Uses OpenAI or Anthropic to categorize and flag risk.
"""
import json
from typing import Optional
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)


class POAnalyst:
    """AI agent for PO categorization and risk analysis."""

    SYSTEM_PROMPT = """You are a procurement risk analyst AI.
Given a purchase order title, description and vendor name, respond ONLY with valid JSON:
{
  "category": "<category name>",
  "risk_level": "low|medium|high",
  "risk_flags": ["<flag1>", "<flag2>"],
  "suggested_vendor": "<vendor name or null>",
  "notes": "<brief analysis>"
}"""

    def __init__(self):
        self.provider = settings.ai_provider

    async def analyze_po(
        self,
        title: str,
        description: Optional[str],
        vendor_name: Optional[str],
    ) -> dict:
        prompt = f"Title: {title}\nDescription: {description or 'N/A'}\nVendor: {vendor_name or 'Unknown'}"

        if self.provider == "anthropic" and settings.anthropic_api_key:
            return await self._analyze_with_anthropic(prompt)
        elif self.provider == "openai" and settings.openai_api_key:
            return await self._analyze_with_openai(prompt)
        else:
            logger.warning("ai_provider_not_configured")
            return {"category": "uncategorized", "risk_level": "low", "risk_flags": [], "notes": "AI not configured"}

    async def _analyze_with_anthropic(self, prompt: str) -> dict:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(message.content[0].text)

    async def _analyze_with_openai(self, prompt: str) -> dict:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
