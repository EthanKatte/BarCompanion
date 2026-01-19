import json
import os
from typing import Any, Dict, Optional

import requests
from openai import OpenAI


BASE_DIR = os.path.dirname(__file__)
DEFAULT_SECRETS_PATH = os.path.join(BASE_DIR, "secrets.json")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def get_api_key(filepath: str = DEFAULT_SECRETS_PATH, key_name: str = "OPENAI_KEY") -> str:
    with open(filepath, "r", encoding="utf-8") as file:
        secrets = json.load(file)
    api_key = secrets.get(key_name)
    if not api_key:
        raise ValueError(f"API key '{key_name}' not found in {filepath}")
    return api_key


def safe_json_loads(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            start = text.find("[")
            end = text.rfind("]")
            if start == -1 or end == -1:
                return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def query_distillery_address(
    distillery_name: str,
    brand_name: Optional[str] = None,
    distillery_description: Optional[str] = None,
    secrets_path: str = DEFAULT_SECRETS_PATH,
    model: str = "gpt-5",
) -> Dict[str, Any]:
    client = OpenAI(api_key=get_api_key(filepath=secrets_path))
    brand_hint = f"Brand name: {brand_name}\n" if brand_name else ""
    description_hint = (
        f"Known distillery description: {distillery_description}\n"
        if distillery_description
        else ""
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You identify official distillery locations and addresses. "
                "Brand names may not match distillery names, and you must prioritize the distillery site address "
                "(not corporate HQ, offices, or distributors). "
                "If multiple distillery sites exist, return only the primary or flagship distillery site. "
                "Include a concise description of the distillery itself (not the brand). "
                "Return JSON only with keys: distillery_name, address, city, region, country, "
                "description, confidence, notes."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{brand_hint}"
                f"{description_hint}"
                f"Distillery name: {distillery_name}\n"
                "Provide the most official primary distillery site address only. "
                "If you are uncertain, return the best guess with a lower confidence. "
                "Return JSON only."
            ),
        },
    ]

    response = client.chat.completions.create(model=model, messages=messages)
    content = response.choices[0].message.content
    data = safe_json_loads(content) or {}

    return {
        "distillery_name": data.get("distillery_name") or distillery_name,
        "address": (data.get("address") or "").strip(),
        "city": (data.get("city") or "").strip(),
        "region": (data.get("region") or "").strip(),
        "country": (data.get("country") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "confidence": float(data.get("confidence", 0.0) or 0.0),
        "notes": (data.get("notes") or "").strip(),
    }


def _pick_address_field(address: Dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = address.get(key)
        if value:
            return str(value)
    return ""


def geocode_address(address: str, timeout: int = 10) -> Dict[str, Any]:
    if not address:
        return {"error": "No address provided"}

    headers = {"User-Agent": "BarCompanion/1.0 (local dev)"}
    params = {
        "q": address,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
    }

    response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    results = response.json()
    if not results:
        return {"error": "No geocode results", "query": address}

    match = results[0]
    addr = match.get("address", {})

    city = _pick_address_field(addr, ["city", "town", "village", "hamlet"])
    region = _pick_address_field(addr, ["state", "region", "county", "state_district"])

    return {
        "lat": float(match.get("lat")),
        "lon": float(match.get("lon")),
        "country": addr.get("country", ""),
        "region": region,
        "city": city,
        "display_name": match.get("display_name", ""),
    }

def query_distilleries_for_brand(
    brand_name: str,
    bottle_names: Optional[list[str]] = None,
    secrets_path: str = DEFAULT_SECRETS_PATH,
    model: str = "gpt-5",
) -> list[Dict[str, Any]]:
    client = OpenAI(api_key=get_api_key(filepath=secrets_path))
    bottle_hint = ""
    if bottle_names:
        sample = ", ".join(bottle_names[:8])
        bottle_hint = f"Known products: {sample}\n"

    messages = [
        {
            "role": "system",
            "content": (
                "You map spirit brands to their producing distilleries. "
                "A brand can correspond to multiple distilleries, but you must return only the primary "
                "or flagship distillery for this brand. "
                "Return JSON only with key distilleries as an array of objects "
                "with keys: name, confidence, notes."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Brand: {brand_name}\n"
                f"{bottle_hint}"
                "Return only the primary/flagship distillery that should represent this brand. "
                "If unsure, return your best guess with lower confidence. "
                "Return JSON only."
            ),
        },
    ]

    response = client.chat.completions.create(model=model, messages=messages)
    content = response.choices[0].message.content
    data = safe_json_loads(content) or {}

    raw = data.get("distilleries", data if isinstance(data, list) else [])
    distilleries = []
    for item in raw or []:
        if isinstance(item, str):
            name = item.strip()
            if name:
                distilleries.append({"name": name, "confidence": 0.0, "notes": ""})
            continue
        if isinstance(item, dict):
            name = (item.get("name") or "").strip()
            if name:
                distilleries.append(
                    {
                        "name": name,
                        "confidence": float(item.get("confidence", 0.0) or 0.0),
                        "notes": (item.get("notes") or "").strip(),
                    }
                )

    return distilleries


def generate_distillery_location(
    distillery_name: str,
    brand_name: Optional[str] = None,
    distillery_description: Optional[str] = None,
    secrets_path: str = DEFAULT_SECRETS_PATH,
) -> Dict[str, Any]:
    details = query_distillery_address(
        distillery_name,
        brand_name,
        distillery_description=distillery_description,
        secrets_path=secrets_path,
    )
    address = details.get("address")

    if not address:
        fallback = details.get("distillery_name") or distillery_name
        country = details.get("country")
        address = f"{fallback} distillery {country or ''}".strip()

    try:
        geo = geocode_address(address)
    except requests.RequestException as exc:
        geo = {"error": str(exc), "query": address}

    return {
        "distillery_name": details.get("distillery_name") or distillery_name,
        "address": address,
        "city": details.get("city") or geo.get("city", ""),
        "region": details.get("region") or geo.get("region", ""),
        "country": details.get("country") or geo.get("country", ""),
        "lat": geo.get("lat"),
        "lon": geo.get("lon"),
        "description": details.get("description", ""),
        "confidence": details.get("confidence", 0.0),
        "notes": details.get("notes", ""),
        "geo_error": geo.get("error", ""),
    }

def test_populate_distilleries_from_brands(
    limit: Optional[int] = None,
    dry_run: bool = True,
    secrets_path: str = DEFAULT_SECRETS_PATH,
) -> list[Dict[str, Any]]:
    from db_queries import get_unique_brands, get_bottle_names_by_brand, upsert_distillery

    brands = get_unique_brands()
    if limit:
        brands = brands[:limit]

    results = []
    for brand in brands:
        bottle_names = get_bottle_names_by_brand(brand, limit=8)
        distilleries = query_distilleries_for_brand(
            brand, bottle_names=bottle_names, secrets_path=secrets_path
        )

        if not distilleries:
            distilleries = [{"name": brand, "confidence": 0.0, "notes": "fallback"}]

        for distillery in distilleries:
            info = generate_distillery_location(
                distillery["name"],
                brand_name=brand,
                distillery_description=distillery.get("notes"),
                secrets_path=secrets_path,
            )
            if not dry_run:
                distillery_id = upsert_distillery(
                    name=info.get("distillery_name"),
                    lat=info.get("lat"),
                    lon=info.get("lon"),
                    country=info.get("country"),
                    region=info.get("region"),
                    description=info.get("description"),
                )
            else:
                distillery_id = None

            results.append(
                {
                    "brand": brand,
                    "distillery_id": distillery_id,
                    "distillery_name": info.get("distillery_name"),
                    "lat": info.get("lat"),
                    "lon": info.get("lon"),
                    "country": info.get("country"),
                    "region": info.get("region"),
                    "description": info.get("description"),
                    "confidence": info.get("confidence"),
                    "geo_error": info.get("geo_error"),
                }
            )

    return results


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]).strip()
    #if not query:
        #raise SystemExit("Usage: python distillery_generator.py <distillery name>")
    test_populate_distilleries_from_brands(limit=2,dry_run=False)
    #result = generate_distillery_location(query)
    #print(json.dumps(result, indent=2))
