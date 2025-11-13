import re

CATEGORIES = {
    "politics": [
        "bundesregierung", "wahl", "kanzler", "minister",
        "eu", "russland", "krieg", "ukraine", "parlament",
        "regierung", "afd", "spd", "fdp", "cdu", "grüne",
    ],
    "economy": [
        "inflation", "wirtschaft", "unternehmen", "handel",
        "industrie", "arbeitsmarkt", "energiepreise",
        "gas", "strom", "lieferkette",
    ],
    "tech": [
        "ki", "künstliche intelligenz", "digitalisierung",
        "software", "hardware", "cyber", "hacker", "internet",
        "startup", "forschung"
    ],
    "world": [
        "usa", "china", "frankreich",
        "nahost", "israel", "afrika", "indien",
    ],
    "society": [
        "gesellschaft", "migration", "kultur", "schule",
        "gesundheit", "soziales", "familie",
    ]
}

def categorize(text: str) -> str:
    text = text.lower()

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                return category

    return "other"
