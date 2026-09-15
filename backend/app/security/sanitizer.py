"""
Security sanitizer for untrusted LLM-generated HTML and Markdown.
Enforces defense-in-depth isolation before rendering in the browser.
"""

import re
import logging
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("lenny_growth.security")

# Tags that are completely disallowed and will be stripped along with their content
DISALLOWED_TAGS = [
    "script",
    "iframe",
    "object",
    "embed",
    "form",
    "input",
    "button",
    "select",
    "textarea",
    "frame",
    "frameset",
    "applet",
    "base",
]

# Attributes starting with 'on' (event handlers like onclick, onload, onerror)
EVENT_HANDLER_REGEX = re.compile(r"^on[a-z]+", re.IGNORECASE)

# Dangerous URL schemes
DANGEROUS_SCHEMES_REGEX = re.compile(r"^\s*(javascript|data|vbscript):", re.IGNORECASE)

def sanitize_html(html_content: str) -> str:
    """
    Sanitize untrusted HTML content:
    1. Removes all executable script/iframe/embed/form elements.
    2. Strips all inline event handlers (onerror, onload, onclick, etc.).
    3. Strips javascript: and data: pseudo-protocols from href/src.
    4. Ensures safe target attributes on links (_blank with rel="noopener noreferrer").
    """
    if not html_content or not html_content.strip():
        return ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Remove dangerous tags and their content
        for tag_name in DISALLOWED_TAGS:
            for element in soup.find_all(tag_name):
                logger.warning("Sanitizer stripped dangerous tag: <%s>", tag_name)
                element.decompose()

        # 2. Inspect all remaining elements for dangerous attributes
        for element in soup.find_all(True):
            if not isinstance(element, Tag):
                continue
            attrs_to_remove = []
            for attr, val in element.attrs.items():
                # Remove event handlers
                if EVENT_HANDLER_REGEX.match(attr):
                    attrs_to_remove.append(attr)
                    continue

                # Inspect URLs in href or src
                if attr in ("href", "src", "action", "formaction") and isinstance(val, str):
                    if DANGEROUS_SCHEMES_REGEX.match(val):
                        attrs_to_remove.append(attr)

            for attr in attrs_to_remove:
                logger.warning("Sanitizer stripped dangerous attribute '%s' from <%s>", attr, element.name)
                del element[attr]

            # Secure all external links
            if element.name == "a":
                element["target"] = "_blank"
                element["rel"] = "noopener noreferrer nofollow"

        # Return sanitized HTML string
        return str(soup)
    except Exception as e:
        logger.error("Failed to sanitize HTML, returning safe escaped fallback: %s", e)
        import html
        return f"<pre>{html.escape(html_content)}</pre>"
