# tests/test_vitals_model.py
from datetime import datetime
from site_health.models import PageVitals

def test_page_vitals_creation():
    vitals = PageVitals(
        url="https://example.com",
        lcp=2.1,
        cls=0.05,
        inp=150,
        measured_at=datetime.now(),
        status="success"
    )
    assert vitals.url == "https://example.com"
    assert vitals.get_lcp_rating() == "good"
    assert vitals.get_cls_rating() == "good"
    assert vitals.get_inp_rating() == "good"

def test_page_vitals_ratings():
    # Test poor ratings
    vitals = PageVitals(
        url="https://slow.com",
        lcp=5.0,
        cls=0.3,
        inp=600,
        measured_at=datetime.now(),
        status="success"
    )
    assert vitals.get_lcp_rating() == "poor"
    assert vitals.get_cls_rating() == "poor"
    assert vitals.get_inp_rating() == "poor"

def test_page_vitals_needs_improvement():
    vitals = PageVitals(
        url="https://medium.com",
        lcp=3.0,
        cls=0.15,
        inp=300,
        measured_at=datetime.now(),
        status="success"
    )
    assert vitals.get_lcp_rating() == "needs-improvement"
    assert vitals.get_cls_rating() == "needs-improvement"
    assert vitals.get_inp_rating() == "needs-improvement"

def test_page_vitals_failed():
    vitals = PageVitals(
        url="https://broken.com",
        lcp=None,
        cls=None,
        inp=None,
        measured_at=datetime.now(),
        status="failed",
        error_message="Timeout"
    )
    assert vitals.status == "failed"
    assert vitals.get_lcp_rating() == "unknown"
