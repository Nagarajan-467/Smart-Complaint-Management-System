"""
Priority Detection Engine.
Scans complaint content for urgent keywords to automatically set priority.
"""

from app.models.complaint import ComplaintPriority

# Keyword rules based on severity
# Using lists of phrases for exact or partial matching
HIGH_PRIORITY_KEYWORDS = [
    "fire", "electric shock", "sparking", "smoke", "accident", "emergency", "danger"
]

MEDIUM_PRIORITY_KEYWORDS = [
    "water leak", "water leakage", "overflow", "broken pipe", "blocked drain", "no water"
]

LOW_PRIORITY_KEYWORDS = [
    "wifi issue", "internet slow", "fan not working", "cleaning", "dust"
]


def predict_priority(title: str, description: str, current_priority: ComplaintPriority) -> ComplaintPriority:
    """
    Analyzes the text and suggests an updated priority.
    We return the highest matched priority, but we NEVER downgrade a priority
    that was explicitly set higher by the user.
    """
    combined_text = f"{title} {description}".lower()
    
    suggested_priority = ComplaintPriority.LOW

    # Check for High Priority triggers first
    if any(keyword in combined_text for keyword in HIGH_PRIORITY_KEYWORDS):
        suggested_priority = ComplaintPriority.HIGH
    # Then Medium
    elif any(keyword in combined_text for keyword in MEDIUM_PRIORITY_KEYWORDS):
        suggested_priority = ComplaintPriority.MEDIUM
    # Then Low (explicitly mapped ones, though LOW is default anyway)
    elif any(keyword in combined_text for keyword in LOW_PRIORITY_KEYWORDS):
        suggested_priority = ComplaintPriority.LOW

    # Logic to prevent downgrading an explicitly set priority
    # Define a hierarchy for comparison
    priority_levels = {
        ComplaintPriority.LOW: 1,
        ComplaintPriority.MEDIUM: 2,
        ComplaintPriority.HIGH: 3,
        ComplaintPriority.CRITICAL: 4
    }
    
    # If the suggested priority is higher than the user's current one, upgrade it.
    if priority_levels[suggested_priority] > priority_levels[current_priority]:
        return suggested_priority
        
    return current_priority
