import json
import re
from pathlib import Path
from typing import Any, Dict, List

REC_PATH = Path(__file__).parent / "data" / "recommendations.json"
RECOMMENDATIONS = json.loads(REC_PATH.read_text(encoding="utf-8"))

def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _text(value):
    return str(value or "").lower().strip()

def normalize_environment(env):
    env = env or {}
    result = {
        "soil": dict(env.get("soil") or {}),
        "climate": dict(env.get("climate") or {}),
        "land": dict(env.get("land") or {}),
        "biodiversity": dict(env.get("biodiversity") or {}),
        "human_impact": dict(env.get("human_impact") or {}),
        "location": env.get("location"),
    }
    aliases = {
        ("soil", "soc"): "organic_carbon",
        ("soil", "organic_carbon_percent"): "organic_carbon",
        ("climate", "rainfall_mm"): "rainfall",
        ("climate", "annual_rainfall"): "rainfall",
        ("climate", "temperature_c"): "temperature",
        ("land", "crop_type"): "crop",
        ("land", "type"): "land_use",
        ("biodiversity", "habitat"): "habitat_diversity",
    }
    for (section, old), new in aliases.items():
        if old in result[section] and new not in result[section]:
            result[section][new] = result[section][old]
    return result

def extract_environment(text, current=None):
    env = normalize_environment(current or {})
    t = (text or "").lower()

    m = re.search(r"(?:organic\s+carbon|soc)[^\d]{0,30}(\d+(?:\.\d+)?)\s*%?", t)
    if m:
        env["soil"]["organic_carbon"] = float(m.group(1))

    m = re.search(r"\bph\b[^\d]{0,10}(\d+(?:\.\d+)?)", t)
    if m:
        env["soil"]["ph"] = float(m.group(1))

    m = re.search(r"(?:soil\s+)?moisture[^\d]{0,15}(\d+(?:\.\d+)?)\s*%?", t)
    if m:
        env["soil"]["moisture"] = float(m.group(1))

    m = re.search(r"(?:rainfall|annual\s+rainfall)[^\d]{0,20}(\d+(?:\.\d+)?)\s*mm?", t)
    if m:
        env["climate"]["rainfall"] = float(m.group(1))
    elif "low rainfall" in t or "low rain" in t:
        env["climate"]["rainfall"] = "low"
    if "high rainfall" in t:
        env["climate"]["rainfall"] = "high"

    m = re.search(r"(?:temperature|temp)[^\d-]{0,15}(-?\d+(?:\.\d+)?)\s*(?:°?\s*c)?", t)
    if m:
        env["climate"]["temperature"] = float(m.group(1))

    for crop in ["wheat", "rice", "maize", "cotton", "soybean", "millet", "sorghum"]:
        if crop in t:
            env["land"]["crop"] = crop
            break

    if "monoculture" in t:
        env["land"]["land_use"] = "monoculture"
    elif "agroforestry" in t:
        env["land"]["land_use"] = "agroforestry"
    elif "mixed crop" in t or "intercrop" in t:
        env["land"]["land_use"] = "intercropping"

    if "low habitat diversity" in t:
        env["biodiversity"]["habitat_diversity"] = "low"
    elif "high habitat diversity" in t:
        env["biodiversity"]["habitat_diversity"] = "high"

    for level in ["high", "medium", "low"]:
        if f"{level} pollution" in t:
            env["human_impact"]["pollution"] = level

    if "deforestation" in t:
        env["human_impact"]["deforestation"] = "present"
    if "semi-arid" in t or "semi arid" in t:
        env["climate"]["zone"] = "semi-arid"
    return env

def missing_fields(env):
    checks = [
        ("soil", "organic_carbon", "soil organic carbon (%)"),
        ("climate", "rainfall", "annual rainfall (mm or low/medium/high)"),
        ("land", "land_use", "land-use type"),
        ("land", "crop", "crop or vegetation type"),
    ]
    return [
        label for section, key, label in checks
        if env.get(section, {}).get(key) in (None, "")
    ]

def severity_and_links(env):
    env = normalize_environment(env)
    signals, metrics = [], []
    soc = _num(env["soil"].get("organic_carbon"))
    rainfall = _num(env["climate"].get("rainfall"))
    moisture = _num(env["soil"].get("moisture"))
    temp = _num(env["climate"].get("temperature"))
    land_use = _text(env["land"].get("land_use"))
    habitat = _text(env["biodiversity"].get("habitat_diversity"))
    pollution = _text(env["human_impact"].get("pollution"))

    if soc is not None and soc < 0.5:
        signals.append("very_low_soil_carbon")
        metrics += ["soil organic carbon", "soil structure", "water retention"]
    if rainfall is not None and rainfall < 600:
        signals.append("low_rainfall")
        metrics += ["water availability", "plant water stress"]
    if _text(env["climate"].get("rainfall")) == "low":
        signals.append("low_rainfall")
        metrics += ["water availability", "plant water stress"]
    if moisture is not None and moisture < 15:
        signals.append("low_soil_moisture")
        metrics += ["soil moisture", "water stress"]
    if temp is not None and temp >= 30:
        signals.append("high_temperature")
        metrics += ["temperature stress", "water demand"]
    if land_use == "monoculture":
        signals.append("monoculture")
        metrics += ["habitat diversity", "functional diversity"]
    if habitat == "low":
        signals.append("low_habitat_diversity")
        metrics += ["habitat diversity", "species richness"]
    if pollution in {"high", "medium"}:
        signals.append("pollution_pressure")
        metrics += ["pollution pressure", "species survival"]
    if _text(env["human_impact"].get("deforestation")) in {"present", "high", "yes"}:
        signals.append("deforestation")
        metrics += ["habitat connectivity", "species richness"]

    return {"signals": sorted(set(signals)), "metrics": sorted(set(metrics))}

def score_recommendation(rec, state, signals):
    score = 0.0
    for trigger in rec.get("triggers", []):
        if trigger in set(signals):
            score += 3.0
    text_blob = json.dumps(state).lower()
    for keyword in rec.get("keywords", []):
        if keyword.lower() in text_blob:
            score += 0.5
    return score

def generate_recommendations(env, retrieved):
    env = normalize_environment(env)
    analysis = severity_and_links(env)
    ranked = []
    retrieved_topics = " ".join(
        f"{x.get('topic','')} {x.get('title','')} {x.get('text','')}" for x in retrieved
    ).lower()

    for rec in RECOMMENDATIONS:
        score = score_recommendation(rec, env, analysis["signals"])
        if score > 0:
            item = dict(rec)
            item["score"] = round(score, 2)
            item["retrieval_overlap"] = sum(
                1 for kw in item.get("keywords", []) if kw.lower() in retrieved_topics
            )
            ranked.append(item)

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:3], analysis

def build_explanation(env, analysis):
    signals = set(analysis["signals"])
    links = []
    if "very_low_soil_carbon" in signals and "low_rainfall" in signals:
        links.append(
            "Low soil organic carbon combined with low rainfall creates a linked "
            "soil-water constraint: soil structure and organic inputs can influence "
            "water-related soil functions during dry periods."
        )
    if "monoculture" in signals and (
        "low_habitat_diversity" in signals or "low_rainfall" in signals
    ):
        links.append(
            "Monoculture plus limited water availability can combine habitat "
            "simplification with climatic stress; adding functional and structural "
            "diversity addresses both dimensions."
        )
    if "deforestation" in signals:
        links.append(
            "Vegetation removal can reduce habitat area and connectivity, affecting "
            "movement and persistence of organisms across the landscape."
        )
    if "pollution_pressure" in signals:
        links.append(
            "Pollution is treated as an additional pressure and should be interpreted "
            "alongside habitat, soil and climate conditions."
        )
    if not links:
        links.append(
            "The system combines available soil, climate, land-use and biodiversity "
            "signals before selecting interventions."
        )
    return links
