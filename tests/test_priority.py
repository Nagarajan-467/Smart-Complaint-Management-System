"""
Unit tests for Priority Detection Engine.
"""

from app.models.complaint import ComplaintPriority
from app.services.priority_service import predict_priority


def test_predict_priority_high():
    # Should detect "fire" and upgrade LOW to HIGH
    assert predict_priority("Fire alarm", "There is a fire in the lab", ComplaintPriority.LOW) == ComplaintPriority.HIGH
    
    # Should detect "electric shock" and upgrade MEDIUM to HIGH
    assert predict_priority("Wire sparking", "I got an electric shock", ComplaintPriority.MEDIUM) == ComplaintPriority.HIGH


def test_predict_priority_medium():
    # Should detect "water leak" and upgrade LOW to MEDIUM
    assert predict_priority("Water leak", "The pipe is leaking", ComplaintPriority.LOW) == ComplaintPriority.MEDIUM


def test_predict_priority_low():
    # Should detect "wifi issue" and stay LOW
    assert predict_priority("WiFi issue", "Internet is slow", ComplaintPriority.LOW) == ComplaintPriority.LOW


def test_prevent_priority_downgrade():
    # If the user sets it to CRITICAL, a "wifi issue" shouldn't downgrade it to LOW
    assert predict_priority("WiFi issue", "Internet is slow", ComplaintPriority.CRITICAL) == ComplaintPriority.CRITICAL
    
    # If the user sets it to HIGH, a "water leak" (MEDIUM trigger) shouldn't downgrade it
    assert predict_priority("Water leak", "Pipe burst", ComplaintPriority.HIGH) == ComplaintPriority.HIGH


def test_no_keywords_found():
    # If no keywords are found, it should retain the current priority
    assert predict_priority("Normal issue", "Just testing", ComplaintPriority.LOW) == ComplaintPriority.LOW
    assert predict_priority("Another issue", "Testing again", ComplaintPriority.MEDIUM) == ComplaintPriority.MEDIUM
