"""Interface language. Spanish is the source text; English comes from i18n_en.EN.

The language is chosen once at startup (see app.main): the LYRIC_CANDLE_LANG environment
variable wins, then the saved option (auto / es / en), then the system's interface
language: Spanish for any Spanish variant, English for everything else. Changing it
in Options applies on the next start. No Qt dependency, so the model can use it too.
"""
from __future__ import annotations

import os

from .i18n_en import EN

LANGUAGES = ('es', 'en')
_language = os.environ.get('LYRIC_CANDLE_LANG', 'es') if os.environ.get('LYRIC_CANDLE_LANG') in LANGUAGES else 'es'


def tr(text: str) -> str:
    """Translate a Spanish source string; unknown strings stay in Spanish."""
    if _language == 'en':
        return EN.get(text, text)
    return text


def language() -> str:
    return _language


def set_language(code: str):
    global _language
    _language = code if code in LANGUAGES else 'en'


def resolve(choice: str, system_languages) -> str:
    """Language to use for a saved choice ('auto', 'es', 'en') and the system's UI languages
    (BCP-47 names such as 'es-CO' or 'en-US', most preferred first)."""
    forced = os.environ.get('LYRIC_CANDLE_LANG')
    if forced in LANGUAGES:
        return forced
    if choice in LANGUAGES:
        return choice
    first = next(iter(system_languages), '') or ''
    return 'es' if first.lower().replace('_', '-').split('-')[0] == 'es' else 'en'
