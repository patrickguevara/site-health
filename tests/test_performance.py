# tests/test_performance.py
from site_health.performance import select_stratified_sample

def test_stratified_sample_includes_homepage():
    pages = [
        "https://example.com",
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/deep/page3"
    ]
    depth_map = {
        "https://example.com": 0,
        "https://example.com/page1": 1,
        "https://example.com/page2": 1,
        "https://example.com/deep/page3": 2
    }

    sample = select_stratified_sample(
        pages,
        "https://example.com",
        depth_map,
        sample_rate=0.5
    )

    # Homepage must be included
    assert "https://example.com" in sample
    # All depth-1 pages must be included
    assert "https://example.com/page1" in sample
    assert "https://example.com/page2" in sample

def test_stratified_sample_respects_rate():
    pages = [f"https://example.com/page{i}" for i in range(100)]
    pages.insert(0, "https://example.com")

    depth_map = {pages[0]: 0}
    for i in range(1, 6):
        depth_map[pages[i]] = 1
    for i in range(6, 100):
        depth_map[pages[i]] = 2

    sample = select_stratified_sample(
        pages,
        "https://example.com",
        depth_map,
        sample_rate=0.1
    )

    # Should be close to 10% (at least homepage + 5 depth-1 = 6 minimum)
    assert len(sample) >= 6
    assert len(sample) <= 15  # Reasonable upper bound for 10% of 100
