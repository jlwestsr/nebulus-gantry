import os
import json
from openai import AsyncOpenAI

# Configure Ollama client for API
client = AsyncOpenAI(
    base_url=os.getenv("OLLAMA_HOST", "http://ollama:11434") + "/v1",
    api_key="ollama",
)

SYSTEM_PROMPT = """
You are an entity extraction system. Your goal is to identify and extract key entities from the user's message.
Return ONLY valid JSON.
Format:
{
    "entities": {
        "Person": ["Name1", "Name2"],
        "Project": ["Project A"],
        "Tool": ["Python", "Docker"],
        "Concept": ["Entity Recognition"]
    }
}
If no entities are found, return {"entities": {}}.
"""

async def extract_entities(text: str, model: str = "llama3.1:latest") -> dict:
    """
    Extracts entities from the given text using the LLM.
    """
    if not text or len(text.strip()) < 5:
        return {}

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0, # Deterministic
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        return data.get("entities", {})
    except Exception as e:
        print(f"Entity Extraction Error: {e}")
        return {}
