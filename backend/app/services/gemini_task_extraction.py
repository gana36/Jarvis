"""Task extraction helpers for Gemini"""
import json
import logging

logger = logging.getLogger(__name__)


async def extract_task_completion(model, user_message: str) -> dict:
    """Extract task name to complete."""
    try:
        prompt = f"""Extract task name. JSON only.
User: "{user_message}"
Format: {{"task_name": "..."}}"""
        
        response = model.generate_content(
            prompt, generation_config={"temperature": 0.0, "max_output_tokens": 50}
        )
        text = response.text.strip()
        
        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            # Remove 'json' prefix if present
            if text.startswith('json'):
                text = text[4:].strip()
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {"task_name": user_message}


async def extract_task_update(model, user_message: str) -> dict:
    """Extract task update details."""
    try:
        prompt = f"""Extract details. JSON only.
User: "{user_message}"
Format: {{"task_name": "...", "priority": null, "new_title": null}}"""
        
        response = model.generate_content(
            prompt, generation_config={"temperature": 0.0, "max_output_tokens": 100}
        )
        text = response.text.strip()
        
        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            if text.startswith('json'):
                text = text[4:].strip()
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {"task_name": user_message, "priority": None, "new_title": None}


async def extract_task_deletion(model, user_message: str) -> dict:
    """Extract task name to delete."""
    try:
        prompt = f"""Extract task to delete. JSON only.
User: "{user_message}"
Format: {{"task_name": "..."}}"""
        
        response = model.generate_content(
            prompt, generation_config={"temperature": 0.0, "max_output_tokens": 50}
        )
        text = response.text.strip()
        
        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            if text.startswith('json'):
                text = text[4:].strip()
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {"task_name": user_message}
