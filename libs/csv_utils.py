import csv
from io import StringIO
from typing import List, Dict
import re

REQUIRED_COLUMNS = ["match_number","date","opponents_team","home_or_away","place"]

# common alias mapping to normalize headers that users may paste
ALIASES = {
    'matchnumber': 'match_number',
    'match_num': 'match_number',
    'matchno': 'match_number',
    'match': 'match_number',
    'date': 'date',
    'opponent': 'opponents_team',
    'opponents': 'opponents_team',
    'opponents_team': 'opponents_team',
    'home_or_away': 'home_or_away',
    'home-away': 'home_or_away',
    'homeoraway': 'home_or_away',
    'place': 'place',
}


def _normalize_key(k: str) -> str:
    if not isinstance(k, str):
        return k
    s = k.strip().lower()
    # replace punctuation and spaces with underscore
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    if s in ALIASES:
        return ALIASES[s]
    # try to match prefix/suffix forms
    for alias, target in ALIASES.items():
        if s.replace('_', '') == alias.replace('_', ''):
            return target
    return s


def parse_pasted_csv(text: str) -> List[Dict]:
    """Parse CSV text into list of dicts with normalized header keys.

    This function is tolerant of header variations like "Match Number", "match_number",
    "match number", or "Match#" and maps them to the canonical keys listed in REQUIRED_COLUMNS.
    It also attempts to auto-correct a common paste issue where rows are separated by
    whitespace instead of newlines (e.g. "header row row1 row2 ..." all on one line).
    """
    if not text or not text.strip():
        return []

    import re

    normalized_text = text.strip()

    # If no explicit newline present, attempt to auto-insert newlines before row starts
    # (a row commonly starts with a digit followed by a comma, e.g. "1,")
    if "\n" not in normalized_text and re.search(r"\d+,", normalized_text):
        # insert a newline before digits that look like the start of a row
        fixed = re.sub(r"\s+(?=\d+,)", "\n", normalized_text)
        # if this produced newlines, use the fixed text and inform caller via a special marker
        normalized_text = fixed

    f = StringIO(normalized_text)
    reader = csv.DictReader(f)
    rows = []
    # normalize fieldnames from the reader
    if reader.fieldnames:
        normalized_names = [_normalize_key(fn) for fn in reader.fieldnames]
    else:
        normalized_names = []

    for i, raw in enumerate(reader, start=1):
        normalized = {}
        for orig_key, val in raw.items():
            norm = _normalize_key(orig_key) if orig_key is not None else orig_key
            if isinstance(val, str):
                v = val.strip()
            else:
                v = val
            normalized[norm] = v
            # keep original fields accessible as _orig_<name>
            normalized[f"_orig_{norm}"] = raw.get(orig_key)
        rows.append(normalized)
    return rows


def validate_row(row: Dict) -> List[str]:
    errs = []
    for col in REQUIRED_COLUMNS:
        if col not in row or row.get(col) in (None, ""):
            errs.append(f"Missing {col}")
    # numeric match_number check
    if 'match_number' in row and row.get('match_number') not in (None, ''):
        try:
            int(str(row.get('match_number')))
        except Exception:
            errs.append('match_number must be an integer')
    return errs
