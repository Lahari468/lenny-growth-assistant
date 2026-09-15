"""
Security & Untrusted HTML Sanitization Tests.
Verifies XSS defense, script tag stripping, event handler removal, and iframe security.
"""

import pytest
from app.security.sanitizer import sanitize_html

def test_sanitizer_removes_script_tags():
    malicious_html = """<div>
        <h1>Welcome</h1>
        <script>alert('XSS Attack!');</script>
        <p>Safe content</p>
    </div>"""
    clean = sanitize_html(malicious_html)
    assert "<script>" not in clean
    assert "alert('XSS Attack!')" not in clean
    assert "Safe content" in clean

def test_sanitizer_removes_event_handlers():
    malicious_html = """<img src="valid.png" onerror="stealCookies()" onload="trackUser()" alt="banner">"""
    clean = sanitize_html(malicious_html)
    assert "onerror" not in clean
    assert "onload" not in clean
    assert "stealCookies" not in clean
    assert "banner" in clean

def test_sanitizer_removes_javascript_schemes():
    malicious_html = """<a href="javascript:void(0)" onclick="exploit()">Click Here</a>"""
    clean = sanitize_html(malicious_html)
    assert "javascript:" not in clean
    assert "onclick" not in clean

def test_sanitizer_strips_nested_iframes():
    malicious_html = """<div><iframe src="http://evil.com/phish"></iframe><p>Dashboard</p></div>"""
    clean = sanitize_html(malicious_html)
    assert "<iframe" not in clean
    assert "evil.com" not in clean
    assert "Dashboard" in clean

def test_sanitizer_secures_links():
    raw_html = """<a href="https://example.com/pricing">Check Pricing</a>"""
    clean = sanitize_html(raw_html)
    assert 'target="_blank"' in clean
    assert 'rel="noopener noreferrer nofollow"' in clean
