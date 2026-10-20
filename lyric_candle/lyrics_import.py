"""Deterministic import of paired lyrics. Never guess the language of a line."""
from __future__ import annotations

import math

from .i18n import tr
from .model import Cue


def parse_alternating(text: str) -> list[tuple[str, str]]:
    """Two lines per blank-separated block, or alternating lines without separators."""
    lines = text.removeprefix('\ufeff').splitlines()
    groups = []
    block = []
    for number, line in enumerate(lines, 1):
        if line.strip():
            block.append((number, line))
        elif block:
            groups.append(block)
            block = []
    if block:
        groups.append(block)
    if not groups:
        raise ValueError(tr('Abre o pega un TXT con original y traducción alternados.'))
    result = []
    if len(groups) > 1:
        for index, group in enumerate(groups, 1):
            if len(group) != 2:
                raise ValueError(tr('Bloque {0}, desde el renglón {1}: tiene {2} renglón(es); se esperan 2 (original y traducción). Corrige el bloque para evitar desplazar las parejas. Si faltan traducciones, utiliza «Dos columnas».').format(index, group[0][0], len(group)))
            result.append((group[0][1], group[1][1]))
    else:
        group = groups[0]
        if len(group) % 2:
            raise ValueError(tr('El renglón {0} queda sin pareja. Cada original necesita su traducción en el siguiente renglón.').format(group[-1][0]))
        result = [(group[i][1], group[i+1][1]) for i in range(0, len(group), 2)]
    return result


def parse_columns(original: str, translation: str) -> list[tuple[str, str]]:
    a = original.removeprefix('\ufeff').splitlines()
    b = translation.removeprefix('\ufeff').splitlines() if translation.strip() else [''] * len(a)
    if not any(v.strip() for v in a):
        raise ValueError(tr('Introduce al menos una frase original.'))
    if len(a) != len(b):
        raise ValueError(tr('Original: {0} renglones. Traducción: {1}. Usa la misma cantidad, incluidos los vacíos intermedios.').format(len(a), len(b)))
    return [(x, y) for x, y in zip(a, b) if x.strip() or y.strip()]


def uniform_cues(pairs: list[tuple[str, str]], duration: float) -> list[Cue]:
    if not pairs or not math.isfinite(duration) or duration <= 0:
        raise ValueError(tr('Falta la letra o la duración del proyecto.'))
    step = duration / len(pairs)
    if step < .05:
        raise ValueError(tr('Amplía la duración del proyecto: hay demasiadas frases para ese intervalo.'))
    return [Cue(start=i*step, end=(i+1)*step, original=x, translation=y, timed=False)
            for i, (x, y) in enumerate(pairs)]
