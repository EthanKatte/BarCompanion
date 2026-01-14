import json
import os
import re
from html.parser import HTMLParser
from db_queries import get_tasting_note_names
import requests
from openai import OpenAI


BASE_DIR = os.path.dirname(__file__)

DEFAULT_SECRETS_PATH = os.path.join(BASE_DIR, "secrets.json")
SERPAPI_BASE_URL = "https://serpapi.com/search.json"


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._chunks.append(data)

    def get_text(self):
        return " ".join(self._chunks)


def html_to_text(html):
    parser = HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


def collapse_whitespace(text):
    return re.sub(r"\s+", " ", text).strip()


def get_api_key(filepath=DEFAULT_SECRETS_PATH, key_name="OPENAI_KEY"):
    with open(filepath, "r", encoding="utf-8") as file:
        secrets = json.load(file)
    api_key = secrets.get(key_name)
    if not api_key:
        raise ValueError(f"API key '{key_name}' not found in {filepath}")
    return api_key

def serpapi_search(query, max_results=10, secrets_path=DEFAULT_SECRETS_PATH):
    api_key = get_api_key(filepath=secrets_path, key_name="SERP_KEY")
    deny_list = ["reddit.com", "archierose.com.au"]
    for blocked_url in deny_list:
        query += f" -site:{blocked_url}"

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": min(max_results, 10),
    }
    response = requests.get(SERPAPI_BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("organic_results", []):
        url = item.get("link")
        if not url:
            continue
        results.append(
            {
                "url": url,
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
            }
        )
        if len(results) >= max_results:
            break

    return results


def safe_json_loads(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def choose_official_url(client, bottle_query, results):
    if not results:
        return {"selected_url": None, "confidence": 0.0, "reason": "no results"}

    formatted_results = []
    for idx, item in enumerate(results, start=1):
        formatted_results.append(
            f"{idx}. {item['url']}\n"
            f"   title: {item['title']}\n"
            f"   snippet: {item['snippet']}"
        )

    prompt = "\n".join(formatted_results)

    messages = [
        {
            "role": "system",
            "content": (
                "You are selecting the official product information for a bottle. "
                "Choose the single most official URL from the list."
                "Prioritize official brand pages for a given bottle, then retailer product pages, then review pages."
                "Return JSON only with keys: selected_url, confidence, reason. "
                "If none are official, return selected_url as null and confidence 0."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Bottle: {bottle_query}\n\nCandidates:\n{prompt}\n\n"
                "Return JSON only."
            ),
        },
    ]

    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages,
    )
    content = response.choices[0].message.content
    data = safe_json_loads(content) or {}

    return {
        "selected_url": data.get("selected_url"),
        "confidence": float(data.get("confidence", 0.0) or 0.0),
        "reason": data.get("reason", ""),
    }


def fetch_page_text(url, timeout=10):
    if url.lower().endswith(".pdf"):
        return ""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    text = html_to_text(response.text)
    return collapse_whitespace(text)


def classify_tasting_notes(client, bottle_query, page_text, allowed_notes, max_notes=8):
    allowed_list = json.dumps(allowed_notes, ensure_ascii=True)
    truncated_text = page_text[:6000]
    messages = [
        {
            "role": "system",
            "content": (
                "You are a classifier that extracts tasting notes from official product descriptions. "
                "Use only the allowed notes list. Do not guess. "
                "Return JSON only with keys: notes (array of strings), evidence (object mapping note to quote)."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Bottle: {bottle_query}\n\n"
                f"Allowed notes: {allowed_list}\n\n"
                f"Description text: {truncated_text}\n\n"
                f"Select up to {max_notes} notes. Return JSON only."
            ),
        },
    ]

    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages,
    )
    content = response.choices[0].message.content
    data = safe_json_loads(content) or {}

    notes = data.get("notes", [])
    evidence = data.get("evidence", {})

    allowed_set = set(allowed_notes)
    filtered = [note for note in notes if note in allowed_set]

    return {
        "notes": filtered[:max_notes],
        "evidence": {note: evidence.get(note, "") for note in filtered},
    }


def generate_expert_notes(
    bottle_query,
    secrets_path=DEFAULT_SECRETS_PATH,
    max_results=10,
    max_notes=8,
    max_attempts=5,
):
    allowed_notes = get_tasting_note_names()
    client = OpenAI(api_key=get_api_key(filepath=secrets_path))
    print("target bottle to generate notes for", bottle_query)
    results = serpapi_search(
        bottle_query,
        max_results=max_results,
        secrets_path=secrets_path,
    )

    failed_urls = set()
    selection = {"selected_url": None, "confidence": 0.0, "reason": "no results"}
    attempts = 0

    while attempts < max_attempts:
        candidates = [
            item for item in results
            if item.get("url") and item["url"] not in failed_urls
        ]
        if not candidates:
            break

        selection = choose_official_url(client, bottle_query, candidates)
        url = selection.get("selected_url")
        candidate_urls = {item["url"] for item in candidates}
        if not url or url not in candidate_urls:
            continue

        print("selection", selection)
        page_text = fetch_page_text(url)
        if page_text:
            classified = classify_tasting_notes(
                client,
                bottle_query,
                page_text,
                allowed_notes,
                max_notes=max_notes,
            )

            if len(classified["notes"]) > 0:
                print("failed URLS: ", failed_urls)
                return {
                    "bottle": bottle_query,
                    "source_url": url,
                    "selection": selection,
                    "notes": classified["notes"],
                    "evidence": classified["evidence"],
                }
            print("retrying, URL was", url,"page text was: ", page_text)

        failed_urls.add(url)
        attempts += 1

    return {
        "bottle": bottle_query,
        "source_url": selection.get("selected_url"),
        "selection": selection,
        "notes": [],
        "evidence": {},
    }


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]).strip()
    if not query:
        raise SystemExit("Usage: python notes_generator.py <brand and bottle name>")

    result = generate_expert_notes(query)
    print(json.dumps(result, indent=2))
