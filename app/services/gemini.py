import google.generativeai as genai
import json
from typing import Dict, List
from app.services.ai_provider import AIProvider
from app.config import settings


class GeminiProvider(AIProvider):
    def __init__(self):
        """Initialize Gemini provider with API key from settings."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generate_pitch(self, brand_data: dict, profile_data: dict) -> Dict[str, str]:
        """
        Generate a personalized pitch using Gemini.

        Args:
            brand_data: Dictionary with brand info (name, website, category, etc.)
            profile_data: Dictionary with creator info (name, niches, bio, etc.)

        Returns:
            Dictionary with 'subject' and 'body' keys
        """
        # Build the prompt
        prompt = f"""
You are {profile_data.get('name', 'a content creator')} writing a pitch email directly to a brand. Write in FIRST PERSON - you are the creator, not a manager or agent.

BRAND INFORMATION:
- Name: {brand_data.get('name', 'Unknown')}
- Website: {brand_data.get('website', 'Not provided')}
- Category: {brand_data.get('category', 'Not provided')}
- Instagram: {brand_data.get('instagram', 'Not provided')}
- Notes: {brand_data.get('notes', 'Not provided')}

YOUR CREATOR PROFILE:
- Name: {profile_data.get('name', 'Unknown')}
- Email: {profile_data.get('sender_email', 'Not provided')}
- Niches: {', '.join(profile_data.get('niches', []))}
- Interests: {', '.join(profile_data.get('interests', []))}
- Bio: {profile_data.get('bio', 'Not provided')}
- Content Style: {profile_data.get('content_style', 'Not provided')}
- Unique Angle: {profile_data.get('unique_angle', 'Not provided')}
- Top Performing Content: {profile_data.get('top_performing_content', 'Not provided')}
- TikTok: {profile_data.get('tiktok_url', 'Not provided')}
- Portfolio: {profile_data.get('portfolio_url', 'Not provided')}
- Follower Count: {profile_data.get('follower_count', 0)}
- Average Views: {profile_data.get('avg_views', 0)}
- Engagement Rate: {profile_data.get('engagement_rate', 0)}%

INSTRUCTIONS:
Write a concise, professional pitch email FROM the creator's perspective (first person - "I'm...", "My content...", "I'd love...").

SUBJECT LINE:
- Professional and direct (e.g., "Collaboration Inquiry – [Content Type] Content")
- Under 60 characters
- No emojis or overly casual language

EMAIL BODY (KEEP IT CONCISE - max 4-5 short paragraphs):
1. Brief greeting and one-sentence introduction (name, location, content focus)
2. One paragraph explaining why the brand aligns with your audience (mention specific brand values/products)
3. Mention ONE key performance metric to show credibility
4. List 3-4 collaboration ideas as bullet points (short, specific)
5. Simple call-to-action offering to share analytics/discuss deliverables
6. Professional sign-off with name, TikTok handle, email, and portfolio URL (if available)

TONE: Professional, direct, confident but not salesy. Business inquiry, not fan mail.
FORMAT: HTML with <p> tags. Use bullet points (<ul><li>) for ideas only.

FOOTER/SIGNATURE:
- Always include: Name, TikTok handle ({profile_data.get('tiktok_url')}), Email ({profile_data.get('sender_email')})
- If portfolio URL exists ({profile_data.get('portfolio_url')}), include it too
- Format: "Best regards,\\nName\\nTikTok: @handle\\nEmail: actual@email.com\\nPortfolio: url" (only if portfolio exists)

CRITICAL: Use the ACTUAL email address provided: {profile_data.get('sender_email')}
Do NOT make up a fake email address.

Return ONLY valid JSON in this exact format:
{{
  "subject": "Your subject line here",
  "body": "<p>Your HTML email body here</p>"
}}
"""

        # Call Gemini API with JSON output
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )

        # Parse JSON response
        pitch = json.loads(response.text)

        return pitch

    def discover_brands(self, niches: List[str], limit: int = 10) -> List[dict]:
        """
        Discover brands matching given niches(Phase 9 - Auto-pilot).

        Args:
            niches: List of niche keywords(e.g., ["skincare", "wellness"])
            limit: Maximum number of brands to discover

        Returns:
            List of dictionaries with brand data
        """
        raise NotImplementedError(
            "Brand discovery will be implemented in Phase 9 (Auto-pilot mode)")
