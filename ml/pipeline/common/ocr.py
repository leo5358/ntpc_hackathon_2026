"""RapidOCR wrapper: a rendered PDF page -> positioned text boxes, grouped into lines."""
from dataclasses import dataclass

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from .text import to_traditional


@dataclass(frozen=True)
class Box:
    x: float  # horizontal centre, px
    y: float  # vertical centre, px
    h: float  # height, px
    text: str  # Traditional-normalised, whitespace removed
    score: float


_engine = None
_engine_kwargs: dict = {}


def configure(**kwargs) -> None:
    """Engine options such as intra_op_num_threads; call before the first OCR in a process."""
    global _engine, _engine_kwargs
    _engine, _engine_kwargs = None, kwargs


def _get_engine() -> RapidOCR:
    global _engine
    if _engine is None:
        try:
            _engine = RapidOCR(**_engine_kwargs)
        except (TypeError, KeyError, ValueError):
            _engine = RapidOCR()
    return _engine


def ocr_page(page, scale: float) -> list[Box]:
    # Red channel as grey: the red seals stamped across statement headers turn as light as the paper,
    # while black print stays dark. Without this the 預算數/決算數 header is often unreadable.
    red = np.array(page.render(scale=scale).to_pil().convert("RGB"))[:, :, 0]
    result, _ = _get_engine()(np.ascontiguousarray(np.stack([red, red, red], axis=-1)))
    return [
        Box((b[0][0] + b[2][0]) / 2, (b[0][1] + b[2][1]) / 2, b[2][1] - b[0][1],
            "".join(to_traditional(text).split()), score)
        for b, text, score in (result or [])
    ]


def page_string(boxes: list[Box]) -> str:
    return "".join(b.text for b in boxes)


def group_lines(boxes: list[Box], tol: float = 0.6) -> list[list[Box]]:
    """Cluster boxes into lines, left to right; tolerance is a fraction of the median box height."""
    if not boxes:
        return []
    limit = tol * float(np.median([b.h for b in boxes]))
    lines, current, line_y = [], [], None
    for box in sorted(boxes, key=lambda b: b.y):
        if line_y is None or abs(box.y - line_y) <= limit:
            current.append(box)
            line_y = box.y if line_y is None else line_y
        else:
            lines.append(sorted(current, key=lambda b: b.x))
            current, line_y = [box], box.y
    if current:
        lines.append(sorted(current, key=lambda b: b.x))
    return lines
