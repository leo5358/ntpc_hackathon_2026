"""Text-layer extraction that keeps table rows intact."""
import pypdfium2 as pdfium


def page_lines(page: pdfium.PdfPage, y_tol: float = 2.0) -> list[str]:
    """Visual rows of a page: text segments clustered by vertical centre, ordered by x.

    Plain text extraction interleaves the columns of these statements; clustering on segment
    geometry keeps each account's figures on its own line. pdfium is used rather than pypdf,
    which fails on ~4–11% of 決算書 pages with an IndirectObject font error.
    """
    textpage = page.get_textpage()
    segments = []
    for i in range(textpage.count_rects()):
        left, bottom, right, top = textpage.get_rect(i)
        text = textpage.get_text_bounded(left, bottom, right, top).strip()
        if text:
            segments.append(((bottom + top) / 2, left, text))
    segments.sort(key=lambda s: (-s[0], s[1]))

    rows, current, row_y = [], [], None
    for y, x, text in segments:
        if row_y is None or abs(y - row_y) <= y_tol:
            current.append((x, text))
            row_y = y if row_y is None else row_y
        else:
            rows.append(current)
            current, row_y = [(x, text)], y
    if current:
        rows.append(current)
    return ["  ".join(text for _, text in sorted(row)) for row in rows]
