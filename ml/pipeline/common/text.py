"""Normalisation for OCR output and PDF text."""
import re

# Simplified forms RapidOCR emits for Traditional characters that occur on these statements.
_PAIRS = (
    "费費 税稅 减減 额額 预預 决決 务務 发發 项項 余餘 计計 总總 营營 运運 资資 产產 负負 债債 净淨 损損 "
    "调調 补補 贴貼 经經 济濟 业業 维維 护護 杂雜 购購 缮繕 员員 劳勞 险險 设設 备備 应應 实實 际際 数數 "
    "执執 结結 绌絀 后後 园園 长長 责責 会會 细細 来來 较較 帐帳 类類 别別 奖獎 励勵 问問 规規 芦蘆 课課"
)
_S2T = str.maketrans({pair[0]: pair[1] for pair in _PAIRS.split()})
_AMOUNT = re.compile(r"^-?\(?-?[\d,]+\)?$")


def to_traditional(s: str) -> str:
    return s.translate(_S2T)


def squash(s: str) -> str:
    """Remove all whitespace, including the full-width space used in headings."""
    return "".join(s.split()).replace("　", "")


def fullwidth_parens(s: str) -> str:
    return s.replace("(", "（").replace(")", "）")


def parse_amount(token: str) -> int | None:
    """'$(1,822,676)' -> -1822676, '-103,818' -> -103818; anything that is not an amount -> None."""
    t = token.replace("$", "").replace(" ", "")
    if not _AMOUNT.match(t) or not any(c.isdigit() for c in t):
        return None
    value = int(re.sub(r"\D", "", t))
    return -value if t.startswith("-") or "(" in t else value
