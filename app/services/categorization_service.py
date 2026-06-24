"""
Smart Categorization Engine.
Automatically classifies complaints based on keyword matching.
"""

from app.models.complaint import ComplaintCategory

# Mapping of categories to their indicative keywords
# Using sets for faster lookup if needed, but simple string matching works well
KEYWORD_MAPPING = {
    ComplaintCategory.NETWORK: [
        "wifi", "internet", "network", "router", "lan", "connection", "ping", "broadband"
    ],
    ComplaintCategory.ELECTRICAL: [
        "power", "electricity", "light", "fan", "ac", "switch", "socket", "electrical",
        "short circuit", "voltage", "wire"
    ],
    ComplaintCategory.PLUMBING: [
        "water", "leak", "pipe", "plumbing", "washroom", "toilet", "tap", "drain", "sink"
    ],
    ComplaintCategory.HOSTEL: [
        "hostel", "room", "bed", "mess", "warden", "mattress", "dorm", "corridor"
    ],
    ComplaintCategory.CLASSROOM: [
        "projector", "board", "desk", "chair", "classroom", "chalk", "duster", "podium"
    ],
}


def predict_category(title: str, description: str) -> ComplaintCategory:
    """
    Predict the category of a complaint based on keyword matching.
    Scans both title and description. Returns GENERAL if no match is found.
    """
    # Combine and normalize text
    combined_text = f"{title} {description}".lower()
    
    # Check for keywords
    # We check in order; if multiple categories might match, the first one wins.
    # In a more advanced system, we might use NLP/TF-IDF or count frequencies.
    for category, keywords in KEYWORD_MAPPING.items():
        if any(keyword in combined_text for keyword in keywords):
            return category
            
    return ComplaintCategory.GENERAL
