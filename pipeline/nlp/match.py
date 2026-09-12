"""L0 Entity Matching: Normalize kindergarten names, aliases, and disambiguation."""
import re
from typing import Dict, List, Optional, Set, Tuple

KINDERGARTEN_AFFIXES = [
    r"新北市立?",
    r"私立",
    r"非營利幼兒園",
    r"幼兒園",
    r"附設幼兒園",
    r"附幼",
]

CONTEXT_ANCHORS = [
    "幼兒園",
    "幼兒",
    "公幼",
    "非營利",
    "老師",
    "教保員",
    "班級",
    "小朋友",
    "學費",
    "抽籤",
    "違規",
    "裁罰",
]


def extract_core_name(raw_name: str) -> str:
    """Strip operators and institutional affixes to find core brand/school name."""
    # 1. Remove bracketed operator e.g. (委託...辦理)
    name = re.sub(r"[\(（].*?[\)）]", "", raw_name).strip()

    # 2. Strip standard administrative affixes
    for affix in KINDERGARTEN_AFFIXES:
        name = re.sub(affix, "", name)

    return name.strip()


class EntityMatcher:
    """Matches text documents against institutional rosters with disambiguation."""

    def __init__(self, institutions: Optional[List[Dict[str, str]]] = None):
        """institutions: list of dicts with keys: id, name, district, operator."""
        self.roster = institutions or []
        self._build_index()

    def _build_index(self):
        self.lookup: Dict[str, Dict] = {}
        for inst in self.roster:
            inst_id = inst.get("id", "")
            raw_name = inst.get("name", "")
            core_name = extract_core_name(raw_name)
            district = inst.get("district", "")

            aliases = {raw_name, core_name, f"{core_name}非營利", f"{core_name}幼兒園"}
            if district:
                aliases.add(f"{district}{core_name}")

            self.lookup[inst_id] = {
                "id": inst_id,
                "name": raw_name,
                "core_name": core_name,
                "district": district,
                "aliases": [a for a in aliases if len(a) >= 2],
            }

    def match_document(self, text: str, inst_id: str) -> Tuple[bool, float, List[str]]:
        """Verify if text belongs to target institution with confidence and matched terms.

        Returns: (matched: bool, confidence: float, matched_terms: list)
        """
        inst_meta = self.lookup.get(inst_id)
        if not inst_meta:
            return False, 0.0, []

        core_name = inst_meta["core_name"]
        district = inst_meta.get("district")

        matched_terms = []

        # 1. Must match core name or aliases
        found_name = False
        for alias in inst_meta["aliases"]:
            if alias in text:
                found_name = True
                matched_terms.append(alias)
                break

        if not found_name:
            return False, 0.0, []

        # 2. Check context anchors (e.g. 幼兒園, 老師) to avoid general homonyms
        context_count = sum(1 for anchor in CONTEXT_ANCHORS if anchor in text)
        if context_count == 0 and len(core_name) <= 2:
            # High false positive risk for 2-character names without context
            return False, 0.0, []

        # 3. District disambiguation bonus
        confidence = 0.6 + min(context_count * 0.08, 0.3)
        if district and district in text:
            confidence = min(confidence + 0.1, 1.0)
            matched_terms.append(district)

        return True, round(confidence, 2), matched_terms
