import json
from openai import OpenAI
from notes_generator import generate_expert_notes

def get_api_key(filepath: str = "secrets.json", key_name: str = "OPENAI_KEY") -> str:
    """
    Reads and returns the API key from a local JSON file.

    Args:
        filepath (str): Path to the secrets file.
        key_name (str): Key name to look up inside the JSON.

    Returns:
        str: The API key as a string.
    """
    try:
        with open(filepath, "r") as f:
            secrets = json.load(f)
        api_key = secrets.get(key_name)
        if not api_key:
            raise ValueError(f"API key '{key_name}' not found in {filepath}")
        return api_key
    except FileNotFoundError:
        raise FileNotFoundError(f"Secrets file not found at: {filepath}")
    except json.JSONDecodeError:
        raise ValueError("Secrets file is not valid JSON")


def generate_description(bottle_query):
    client = OpenAI(api_key=get_api_key())
    context = [
            {
            "role": "system",
            "content": (
                "You are an authoritative whiskey expert and sommelier specializing in brand-accurate product descriptions. "
                "When asked about a bottle, you must provide the *official* description that most closely matches the wording used "
                "on the distillery or brand's official website or product release page. "
                "If the exact wording is unavailable, write a faithful and neutral summary in the same professional tone. "
                "Avoid speculation, user reviews, or tasting notes unless explicitly part of the brand's official marketing text. "
                "Always maintain a formal, elegant tone that mirrors how distilleries describe their own whiskies."
                "Do not include any html or web artifacts in your response."
                "Do not include any discussion or other statements, only respond with the description."
            )
        },
        {
            "role": "user",
            "content": (
                f"Provide the official description for {bottle_query}. "
                "Focus strictly on the brand or distillery's own product description. "
                "Do not include personal opinions or unrelated history. "
                "If multiple editions exist, choose the one that best matches the core release unless otherwise specified."
            )
        },
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=context
        )
        text = response.choices[0].message.content
        return text
    except Exception as e:
        print(f"Error fetching description: {e}")
    return ""

