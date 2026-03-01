import google.generativeai as genai_old  # OLD SDK - for pitch generation
from google import genai                # NEW SDK - for brand discovery (supports search grounding)
from google.genai import types          # Types for configuring the new SDK
import json
from typing import Dict, List
from app.services.ai_provider import AIProvider
from app.config import settings


#Pitch generation
class GeminiProvider(AIProvider):
    def __init__(self):
        """Initialize Gemini provider with API key from settings."""
        # Configure the OLD SDK for pitch generation (this still works fine)
        genai_old.configure(api_key=settings.gemini_api_key)
        self.model = genai_old.GenerativeModel("gemini-2.5-flash")

        # Create the NEW SDK client for brand discovery (supports search grounding)
        self.discovery_client = genai.Client(api_key=settings.gemini_api_key)

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
6. Professional sign-off with name, TikTok URL, and portfolio URL (if available) - NO EMAIL

TONE: Professional, direct, confident but not salesy. Business inquiry, not fan mail.
FORMAT: HTML with <p> tags. Use bullet points (<ul><li>) for ideas only.

FOOTER/SIGNATURE:
- Always include: Name, TikTok username, and TikTok URL as clickable link
- If portfolio URL exists, include it as clickable link too
- Format TikTok username: "TikTok: @username" (extract from {profile_data.get('tiktok_url')})
- Format TikTok URL: <a href="{profile_data.get('tiktok_url')}">www.tiktok.com/@username</a>
- Include BOTH the @username and the clickable URL on separate lines
- Format Portfolio: <a href="{profile_data.get('portfolio_url')}">View Portfolio</a>
- DO NOT INCLUDE EMAIL ADDRESS - the email is already in the FROM field

Return ONLY valid JSON in this exact format:
{{
  "subject": "Your subject line here",
  "body": "<p>Your HTML email body here</p>"
}}
"""

        # Call Gemini API with JSON output
        response = self.model.generate_content(
            prompt,
            generation_config=genai_old.GenerationConfig(
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
    
    def discover_brand_contacts(self, brand_name: str) -> dict:
        """
        Use Gemini with Google Search grounding to find real contact emails
        and metadata for a brand.

        How it works:
        1. We create a Google Search grounding tool so Gemini can search the web in real-time
        2. We send a prompt asking Gemini to research the brand and find contact emails
        3. Gemini searches the web, finds real data, and returns structured JSON
        4. We parse and return the JSON with brand metadata + discovered contacts

        Args:
            brand_name: The name of the brand to research (e.g., "CeraVe", "The Ordinary")

        Returns:
            dict with keys: brand_name, parent_company, website, instagram,
                           category, description, contacts (list of email dicts)
        """

        # Step 1: Create the Google Search grounding tool
        # This gives Gemini the ability to search Google in real-time
        # Without this, Gemini can only use its training data (which may be outdated)
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        # Step 2: Build the research prompt
        # We ask Gemini to act as a brand researcher and find specific information
        # The prompt requests JSON output so we can parse it programmatically
        prompt = f"""
You are a brand research assistant. Research the brand "{brand_name}" using web search
and find their real contact information.

I need you to find:
1. The brand's official website URL
2. Their Instagram handle
3. Their parent company (if any)
4. What category they fall into (e.g., skincare, wellness, beauty, fashion)
5. A brief description of the brand (2-3 sentences)
6. 2-4 REAL email addresses for contacting them about partnerships/collaborations

For emails, look for:
- PR/press contact emails
- Partnership or collaboration emails  
- Marketing department emails
- General contact emails from their website
- Influencer/creator program emails

For each email, classify it as one of: "pr", "partnerships", "marketing", "general", "influencer"
and rate your confidence as "high", "medium", or "low".

IMPORTANT: Only include emails you actually found on their website, social media, or press pages.
Do NOT make up or guess email addresses.

Return your response as valid JSON in this exact format:
{{
    "brand_name": "{brand_name}",
    "parent_company": "Parent Company Name or null",
    "website": "https://example.com",
    "instagram": "@handle",
    "category": "skincare",
    "description": "Brief brand description here.",
    "contacts": [
        {{
            "email": "press@example.com",
            "type": "pr",
            "confidence": "high",
            "source": "Found on their website contact page"
        }}
    ]
}}

If you cannot find any contact emails, return an empty contacts list.
Return ONLY the JSON, no other text.
"""

        # Step 3: Send the request to Gemini using the NEW SDK
        # We use self.discovery_client (initialized in __init__) with search grounding
        # The config tells Gemini to use the Google Search tool before answering
        try:
            response = self.discovery_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[google_search_tool],
                    temperature=0.2  # Low temperature = more factual, less creative
                )
            )
            
            # Step 4: Extract the text from response
            if hasattr(response, 'text') and response.text:
                raw_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                raw_text = response.candidates[0].content.parts[0].text
            else:
                raise Exception(f"Unexpected response structure: {response}")
            
            # Step 5: Clean up markdown code blocks if present
            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Step 6: Parse JSON
            result = json.loads(cleaned_text)
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Gemini response as JSON. Response was: {cleaned_text[:200]}... Error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to discover brand contacts: {str(e)}")
    