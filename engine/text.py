"""
Text pipeline shared by training and inference (pure Python, no dependencies).

The SAME logic is ported 1:1 to webapp/engine.js. tests/parity_test.py checks
that both produce identical tokens, features and scores. If you change
anything here, change engine.js too and re-run the parity test.

Steps
  1. tokenize the ORIGINAL text, keeping offsets (for highlighting):
       URLs, e-mails and phone numbers become single protected tokens
  2. normalize each word token:
       NFKC -> lowercase -> strip accents & Arabic diacritics -> unify Arabic
       letters (أإآ->ا, ة->ه, ى->ي, ڭ->ك ...) -> Arabic digits -> ASCII ->
       collapse "saaaalam" -> "saalam" -> digit runs (>=2) -> "0"
     Arabizi digits inside words (3afak, 7it, 9bel) are kept: they are letters.
  3. features: char n-grams (2..5) inside each token + word unigrams/bigrams
"""
import re
import unicodedata

# ----------------------------------------------------------------- tokenizer
# Order matters: URL first (may contain digits/@), then e-mail, then phone.
TLDS = "university|education|solutions|business|delivery|exchange|services|software|training|academy|careers|company|digital|express|finance|monster|network|reviews|support|systems|tickets|trading|website|africa|agency|center|credit|design|events|global|invest|london|market|moscow|online|photos|review|school|social|stream|studio|click|cloud|codes|deals|email|games|gifts|group|loans|media|money|movie|music|ninja|pages|paris|photo|press|promo|quest|space|store|today|tools|trade|video|works|world|arab|asia|bank|best|blog|bond|buzz|cash|chat|club|cyou|free|game|gift|gold|help|host|info|jobs|life|link|live|loan|mobi|name|news|page|pics|rest|sale|shop|site|tech|wiki|work|zone|app|art|bar|bet|biz|cam|cfd|com|dev|edu|fit|fun|gov|icu|inc|ink|int|llc|lol|ltd|mil|mom|net|one|org|pro|run|sbs|tel|top|uno|vip|win|xyz|ac|ad|ae|af|ag|ai|al|am|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|za|zm|zw"
# NOTE: no look-behind and no \w / \d / \b (they differ between Python and JavaScript);
# boundaries are checked in code instead (see _boundary_ok).
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"'«»]+"
    r"|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:" + TLDS + r")(?![a-z0-9-])(?:[/?#][^\s<>\"'«»]*)?",
    re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+")
PHONE_RE = re.compile(r"(?:\+|00)[0-9]{1,3}[ .-]?[0-9](?:[ .-]?[0-9]){6,12}|0[5-8](?:[ .-]?[0-9]){8}")
BEFORE_URL = re.compile(r"[A-Za-z0-9_@.-]")
ALNUM = re.compile(r"[A-Za-z0-9]")
# a "word" is a run of Latin letters/digits, accented Latin, or Arabic letters/digits
WORD_RE = re.compile(r"[0-9A-Za-zÀ-ɏ̀-ͯء-غـ-ٟ٠-٩ٰ-ۓۖ-ۭ۰-۹ﭐ-﷿ﹰ-ﻼ]+")
TRAILING = ".,;:!?)]}»\"'…،؛؟"

AR_MAP = {"ة": "ه", "ى": "ي", "ٱ": "ا", "ک": "ك", "ی": "ي", "ڭ": "ك", "گ": "ك", "ڤ": "ف", "پ": "ب", "چ": "ج",
          "ھ": "ه", "ۀ": "ه", "ے": "ي", "ئ": "ي", "ؤ": "و", "أ": "ا", "إ": "ا", "آ": "ا", "ء": ""}
DIGITS = {**{chr(0x0660 + i): str(i) for i in range(10)}, **{chr(0x06F0 + i): str(i) for i in range(10)}}
MARKS_RE = re.compile(r"[̀-ͯؐ-ًؚ-ٰٟۖ-ۭـ]")
REPEAT_RE = re.compile(r"(.)\1{2,}")
DIGITRUN_RE = re.compile(r"[0-9]{2,}")


def normalize_token(tok: str) -> str:
    s = unicodedata.normalize("NFKC", tok).lower()
    s = unicodedata.normalize("NFD", s)
    s = MARKS_RE.sub("", s)
    s = unicodedata.normalize("NFC", s)
    s = "".join(AR_MAP.get(c, DIGITS.get(c, c)) for c in s)
    s = REPEAT_RE.sub(r"\1\1", s)
    s = DIGITRUN_RE.sub("0", s)
    return s


def _u16(text: str, i: int) -> int:
    """code-point index -> UTF-16 index (what JavaScript uses)"""
    return len(text[:i].encode("utf-16-le")) // 2


def tokenize(text: str):
    """Return a list of tokens: dict(raw, norm, kind, s, e) where s/e are UTF-16 offsets."""
    text = text or ""
    spans = []  # (start, end, kind)
    taken = [False] * (len(text) + 1)

    def claim(regex, kind):
        for m in regex.finditer(text):
            s, e = m.start(), m.end()
            if any(taken[s:e]):
                continue
            prev = text[s - 1] if s > 0 else ""
            nxt = text[e] if e < len(text) else ""
            if kind == "url" and prev and BEFORE_URL.match(prev):
                continue
            if kind == "phone" and ((prev and ALNUM.match(prev)) or (nxt and ALNUM.match(nxt))):
                continue
            raw = text[s:e]
            while raw and raw[-1] in TRAILING:
                raw, e = raw[:-1], e - 1
            if kind == "url" and "." not in raw:
                continue
            if kind == "phone" and len(re.sub(r"[^0-9]", "", raw)) < 9:
                continue
            spans.append((s, e, kind))
            for k in range(s, e):
                taken[k] = True

    claim(URL_RE, "url")
    claim(EMAIL_RE, "email")
    claim(PHONE_RE, "phone")
    for m in WORD_RE.finditer(text):
        s, e = m.start(), m.end()
        # split a word that overlaps a protected span (rare) - keep only free parts
        if any(taken[s:e]):
            continue
        spans.append((s, e, "word"))
    spans.sort()
    toks = []
    for s, e, kind in spans:
        raw = text[s:e]
        if kind == "url":
            norm = "lnk"
        elif kind == "email":
            norm = "eml"
        elif kind == "phone":
            norm = "tel"
        else:
            norm = normalize_token(raw)
            if not norm:
                continue
        toks.append({"raw": raw, "norm": norm, "kind": kind, "s": _u16(text, s), "e": _u16(text, e)})
    return toks


def ngram_features(norm_tokens, nmin=2, nmax=5):
    """List of (feature, token_index_or_pair) - char n-grams per token + word uni/bigrams."""
    feats = []
    for i, t in enumerate(norm_tokens):
        w = " " + t + " "
        L = len(w)
        for n in range(nmin, nmax + 1):
            if L < n:
                if n == nmin:
                    feats.append(("c:" + w, i))
                break
            for k in range(L - n + 1):
                feats.append(("c:" + w[k:k + n], i))
        feats.append(("w:" + t, i))
        if i + 1 < len(norm_tokens):
            feats.append(("b:" + t + " " + norm_tokens[i + 1], i))
    return feats


def analyzer(text: str):
    """sklearn-compatible analyzer: text -> list of feature strings."""
    return [f for f, _ in ngram_features([t["norm"] for t in tokenize(text)])]


if __name__ == "__main__":
    for s in ["Salam mama, 3afak sift liya 1500dh daba!! https://cih-securite.top/login",
              "وزارة العدل: لديكم مخالفة مرورية غير مؤداة. أدّوا قبل 48 ساعة: justice-amendes.icu/v/4471",
              "📦 Votre colis est bloqué, réglez 12,99 DH : bit.ly/abc  — +44 7520 113 284 / 0661234567"]:
        print([(t["norm"], t["kind"]) for t in tokenize(s)])
