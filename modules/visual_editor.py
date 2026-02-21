"""Visual WYSIWYG editor component for email templates.

Renders the email template preview as a contenteditable area with a floating
toolbar. The user can format text, change colours, and then click **Apply**
to push the edits back into the Streamlit template (`session_state`).
"""

import os
import re
import streamlit.components.v1 as components

# ── Register the Streamlit custom component ─────────────────────────────────
_COMPONENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "components",
    "visual_editor",
)

_component_func = components.declare_component("visual_editor", path=_COMPONENT_DIR)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _split_template(html: str) -> dict:
    """Split a full HTML template into scoped *styles*, *body*, *prefix* and *suffix*.

    The *prefix* and *suffix* are everything outside the ``<body>`` content
    so the full document can be reconstructed later.
    """
    # Extract all <style> blocks
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    styles = '\n'.join(style_blocks) if style_blocks else ''

    # Scope the body selector → #editable-content so styles work inside the editor
    styles = re.sub(r'\bbody\s*\{', '#editable-content {', styles)

    # Extract <body> content
    body_match = re.search(r'(<body[^>]*>)(.*?)(</body>)', html, re.DOTALL)
    if body_match:
        body = body_match.group(2).strip()
        prefix = html[:body_match.start(2)]
        suffix = html[body_match.end(2):]
    else:
        body = html
        prefix = ''
        suffix = ''

    return dict(styles=styles, body=body, prefix=prefix, suffix=suffix)


def _wrap_placeholders(html: str) -> str:
    """Wrap ``{placeholder}`` tokens in non-editable styled spans.

    Only wraps placeholders that appear in *text content* (between ``>`` and
    ``<``), **not** inside HTML attribute values such as ``href="{link}"``.
    """
    parts = re.split(r'(<[^>]+>)', html)
    result = []
    for part in parts:
        if part.startswith('<'):
            result.append(part)          # HTML tag – leave intact
        else:
            # Text content – wrap placeholders
            result.append(
                re.sub(
                    r'\{(\w+)\}',
                    lambda m: (
                        f'<span contenteditable="false" '
                        f'class="tpl-placeholder" '
                        f'data-placeholder="{m.group(1)}">'
                        f'{m.group(0)}</span>'
                    ),
                    part,
                )
            )
    return ''.join(result)


def _unwrap_placeholders(html: str) -> str:
    """Strip placeholder span wrappers and restore ``{name}`` syntax."""
    return re.sub(
        r'<span[^>]*class="tpl-placeholder"[^>]*data-placeholder="(\w+)"[^>]*>[^<]*</span>',
        lambda m: '{' + m.group(1) + '}',
        html,
    )


# ── Public API ───────────────────────────────────────────────────────────────

def visual_editor(template_html: str, key: str = None):
    """Render an inline WYSIWYG editor for the email template.

    Parameters
    ----------
    template_html : str
        The full HTML email template (with ``{placeholders}``).
    key : str, optional
        Streamlit widget key.

    Returns
    -------
    str or None
        The full updated template HTML when the user clicks **Apply Changes**,
        otherwise ``None``.
    """
    parts = _split_template(template_html)
    wrapped_body = _wrap_placeholders(parts['body'])

    result = _component_func(
        body_html=wrapped_body,
        styles=parts['styles'],
        key=key,
        default=None,
    )

    if result and isinstance(result, dict) and 'body_html' in result:
        edited_body = _unwrap_placeholders(result['body_html'])
        return parts['prefix'] + edited_body + parts['suffix']

    return None
