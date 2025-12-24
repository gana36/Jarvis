"""Profile Extraction Service - LLM-powered extraction of user profile info from conversation"""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def extract_profile_info(gemini_model, transcript: str) -> Optional[Dict[str, Any]]:
    """
    Extract profile information from user's message using Gemini Flash.
    
    Optimized for speed (~50-100ms):
    - Lightweight prompt
    - Short output limit
    - Temperature 0 for consistency
    
    Args:
        gemini_model: Gemini model instance
        transcript: User's message
        
    Returns:
        Dictionary with extracted fields, or None if no profile info found
        
    Example Returns:
        {"name": "Sarah"}
        {"dietary_preference": "vegan", "interests": ["cooking"]}
        {"learning_level": "beginner"}
        None (if no profile info detected)
    """
    try:
        prompt = f"""Extract ONLY explicit personal information from this message. Return JSON or "null".

User message: "{transcript}"

Extract ONLY if explicitly mentioned:
- name: First name or full name (only if user introduces themselves)
- dietary_preference: One of: vegetarian, vegan, pescatarian, kosher, halal, gluten-free, none
- learning_level: One of: beginner, intermediate, expert
- interests: Array of topics/hobbies mentioned (max 3)
- location: City or region if mentioned

Rules:
1. Only extract what is EXPLICITLY stated
2. Return "null" if no personal info found
3. Return valid JSON object if info found
4. Don't infer or assume

Examples:
"I'm Sarah" → {{"name": "Sarah"}}
"I don't eat meat" → {{"dietary_preference": "vegetarian"}}
"I'm vegan and love cooking" → {{"dietary_preference": "vegan", "interests": ["cooking"]}}
"I'm a beginner at Python" → {{"learning_level": "beginner", "interests": ["Python"]}}
"I live in Seattle" → {{"location": "Seattle"}}
"What's the weather?" → null
"How are you?" → null

Output (JSON or null):"""

        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 150
            }
        )
        
        text = response.text.strip()
        
        # Handle "null" response
        if text.lower() == "null" or text.lower() == "none":
            logger.debug(f"No profile info extracted from: '{transcript}'")
            return None
        
        # Extract JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            if text.startswith('json'):
                text = text[4:].strip()
        else:
            # No code blocks - extract JSON directly
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
        
        # Parse JSON
        extracted = json.loads(text)
        
        # Validate it's a dict with at least one field
        if isinstance(extracted, dict) and len(extracted) > 0:
            logger.info(f"📝 Extracted profile info: {extracted}")
            return extracted
        else:
            logger.debug(f"Empty extraction result from: '{transcript}'")
            return None
            
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error in profile extraction: {e}")
        logger.debug(f"Failed to parse: {text}")
        return None
    except Exception as e:
        logger.error(f"Profile extraction failed: {e}")
        return None


def normalize_dietary_preference(raw_value: str) -> str:
    """
    Normalize dietary preference to standard values.
    
    Args:
        raw_value: Raw extracted value
        
    Returns:
        Normalized dietary preference
    """
    value = raw_value.lower().strip()
    
    # Map variations to standard values
    mapping = {
        'vegetarian': 'vegetarian',
        'veggie': 'vegetarian',
        'veg': 'vegetarian',
        'vegan': 'vegan',
        'pescatarian': 'pescatarian',
        'pescetarian': 'pescatarian',
        'fish': 'pescatarian',
        'kosher': 'kosher',
        'halal': 'halal',
        'gluten-free': 'gluten-free',
        'gluten free': 'gluten-free',
        'celiac': 'gluten-free',
        'none': 'none',
        'no restrictions': 'none',
    }
    
    return mapping.get(value, value)


def normalize_learning_level(raw_value: str) -> str:
    """
    Normalize learning level to standard values.
    
    Args:
        raw_value: Raw extracted value
        
    Returns:
        Normalized learning level
    """
    value = raw_value.lower().strip()
    
    # Map variations to standard values
    mapping = {
        'beginner': 'beginner',
        'novice': 'beginner',
        'new': 'beginner',
        'starting': 'beginner',
        'intermediate': 'intermediate',
        'mid': 'intermediate',
        'moderate': 'intermediate',
        'advanced': 'expert',
        'expert': 'expert',
        'professional': 'expert',
        'pro': 'expert',
    }
    
    return mapping.get(value, value)


def normalize_profile_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize extracted profile data to standard formats.
    
    Args:
        raw_data: Raw extracted data
        
    Returns:
        Normalized profile data
    """
    normalized = {}
    
    # Normalize dietary preference
    if 'dietary_preference' in raw_data:
        normalized['dietary_preference'] = normalize_dietary_preference(
            raw_data['dietary_preference']
        )
    
    # Normalize learning level
    if 'learning_level' in raw_data:
        normalized['learning_level'] = normalize_learning_level(
            raw_data['learning_level']
        )
    
    # Pass through other fields as-is
    for key in ['name', 'location', 'interests']:
        if key in raw_data:
            normalized[key] = raw_data[key]
    
    return normalized
