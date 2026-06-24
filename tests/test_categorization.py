"""
Unit tests for the Smart Categorization Engine.
"""

from app.models.complaint import ComplaintCategory
from app.services.categorization_service import predict_category


def test_predict_category_network():
    assert predict_category("No WiFi", "I can't connect to the internet") == ComplaintCategory.NETWORK
    assert predict_category("Router broken", "The router is blinking red") == ComplaintCategory.NETWORK


def test_predict_category_electrical():
    assert predict_category("Power out", "No electricity in room 102") == ComplaintCategory.ELECTRICAL
    assert predict_category("AC not cooling", "The AC is blowing hot air") == ComplaintCategory.ELECTRICAL
    assert predict_category("Sparking switch", "The switch board is sparking") == ComplaintCategory.ELECTRICAL


def test_predict_category_plumbing():
    assert predict_category("Water leak", "The tap is leaking continuously") == ComplaintCategory.PLUMBING
    assert predict_category("Clogged drain", "The washroom drain is blocked") == ComplaintCategory.PLUMBING


def test_predict_category_hostel():
    assert predict_category("Mess food", "The mess food is very bad today") == ComplaintCategory.HOSTEL
    assert predict_category("Bed broken", "My mattress is torn") == ComplaintCategory.HOSTEL


def test_predict_category_classroom():
    assert predict_category("Projector issue", "Projector is not turning on") == ComplaintCategory.CLASSROOM
    assert predict_category("Broken desk", "The chair and desk are broken") == ComplaintCategory.CLASSROOM


def test_predict_category_general_fallback():
    # If no keywords match, it should fall back to GENERAL
    assert predict_category("Random issue", "Something is wrong with the system") == ComplaintCategory.GENERAL
    assert predict_category("Hello", "Just testing the application") == ComplaintCategory.GENERAL
