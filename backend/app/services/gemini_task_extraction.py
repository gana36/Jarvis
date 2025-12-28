"""Task extraction helpers for Gemini"""
import json
import logging

logger = logging.getLogger(__name__)


async def extract_task_completion(model, user_message: str, history: list = None) -> dict:
    """Extract task name to complete."""
    try:
        # Build context from history
        history_context = ""
        if history and len(history) > 0:
            history_lines = []
            for msg in history[-4:]:
                role = "User" if msg.get("role") == "user" else "Manas"
                content = msg.get("parts", "")
                history_lines.append(f"{role}: {content}")
            history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

        prompt = f"""{history_context}Extract task name to mark complete. JSON only.
Use the conversation history above to resolve pronouns like "that" or "it" if the current message is a follow-up.
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


async def extract_task_update(model, user_message: str, history: list = None) -> dict:
    """Extract task update details."""
    try:
        # Build context from history
        history_context = ""
        if history and len(history) > 0:
            history_lines = []
            for msg in history[-4:]:
                role = "User" if msg.get("role") == "user" else "Manas"
                content = msg.get("parts", "")
                history_lines.append(f"{role}: {content}")
            history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

        prompt = f"""{history_context}Extract task details for updating. JSON only.
Use the conversation history to resolve which task is being updated if pronouns are used.
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


async def extract_task_deletion(model, user_message: str, history: list = None) -> dict:
    """Extract task name to delete."""
    try:
        # Build context from history
        history_context = ""
        if history and len(history) > 0:
            history_lines = []
            for msg in history[-4:]:
                role = "User" if msg.get("role") == "user" else "Manas"
                content = msg.get("parts", "")
                history_lines.append(f"{role}: {content}")
            history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

        prompt = f"""{history_context}Extract task to delete. JSON only.
Use the conversation history to resolve references if the user says "delete that one".
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
