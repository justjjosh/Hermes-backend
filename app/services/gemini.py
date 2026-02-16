import google.generativeai as genai
import json
from typing import Dict, List
from app.services.ai_provider import AIProvider
from app.config import settings

class GeminiProvider(AIProvider):
    def __init__(self):
        """Initialize Gemini provider with API key from settings."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
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
You are a professional brand partnership manager writing a pitch email on behalf of a content creator.

BRAND INFORMATION:
- Name: {brand_data.get('name', 'Unknown')}
- Website: {brand_data.get('website', 'Not provided')}
- Category: {brand_data.get('category', 'Not provided')}
- Instagram: {brand_data.get('instagram', 'Not provided')}
- Notes: {brand_data.get('notes', 'Not provided')}

CREATOR INFORMATION:
- Name: {profile_data.get('name', 'Unknown')}
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
Generate a highly personalized, professional pitch email that:
1. Has a compelling subject line (under 60 characters)
2. Opens with a personalized greeting
3. Demonstrates knowledge of the brand's values and products
4. Explains why this creator is an authentic fit for the brand
5. Includes specific collaboration ideas
6. Has a clear call-to-action
7. Ends with a professional signature

The email body should be in HTML format with proper paragraph tags (<p>, <br>, etc.).
Make it warm, genuine, and professional - not salesy or desperate.

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
        Discover brands matching given niches (Phase 9 - Auto-pilot).
        
        Args:
            niches: List of niche keywords (e.g., ["skincare", "wellness"])
            limit: Maximum number of brands to discover
        
        Returns:
            List of dictionaries with brand data
        """
        raise NotImplementedError("Brand discovery will be implemented in Phase 9 (Auto-pilot mode)")

