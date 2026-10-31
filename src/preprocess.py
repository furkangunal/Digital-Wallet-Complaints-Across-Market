"""Language-aware text preprocessing for English and Turkish reviews.

Two text versions are produced per review:

* ``base_clean``  - light cleaning that keeps casing, punctuation and emojis.
  Used as input for transformer models (sentiment, sentence embeddings),
  which are trained on natural text and benefit from those signals.
* ``normalize``   - aggressive normalisation (lower-casing, emoji/URL removal,
  abbreviation and contraction expansion, Turkish deasciification). Used for
  keyword-based steps such as BERTopic's topic representations.
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

import emoji

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE_RE = re.compile(r"(?:\+?\d[\s().-]?){10,}")
ELONGATION_RE = re.compile(r"(.)\1{2,}")          # "sooooo" -> "soo", "!!!!" -> "!!"
WORD_RE = re.compile(r"[^\W\d_]+")                # letters only, Unicode-aware
WHITESPACE_RE = re.compile(r"\s+")
QUOTES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"'})

# --------------------------------------------------------------------------- #
# Language resources
# --------------------------------------------------------------------------- #
# Contractions typed without an apostrophe; apostrophe forms are handled in
# _expand_en_contractions because WORD_RE splits tokens at apostrophes.
EN_CONTRACTIONS = {
    "cant": "cannot", "wont": "will not", "dont": "do not", "doesnt": "does not",
    "didnt": "did not", "isnt": "is not", "wasnt": "was not", "arent": "are not",
    "werent": "were not", "havent": "have not", "hasnt": "has not",
    "couldnt": "could not", "wouldnt": "would not", "shouldnt": "should not",
    "im": "i am", "ive": "i have", "youre": "you are", "theyre": "they are",
}
EN_SUFFIXES = (("n't", " not"), ("'re", " are"), ("'ve", " have"),
               ("'ll", " will"), ("'m", " am"), ("'d", " would"))

EN_ABBREVIATIONS = {
    "u": "you", "ur": "your", "pls": "please", "plz": "please", "thx": "thanks",
    "ty": "thank you", "bc": "because", "cuz": "because", "idk": "i do not know",
    "asap": "as soon as possible", "acct": "account", "acc": "account",
    "txn": "transaction", "msg": "message", "cs": "customer service",
    "cust": "customer", "svc": "service", "govt": "government",
    "info": "information", "w": "with", "wo": "without",
}

TR_ABBREVIATIONS = {
    "slm": "selam", "mrb": "merhaba", "tşk": "teşekkürler", "tsk": "teşekkürler",
    "tşkler": "teşekkürler", "tskler": "teşekkürler", "saol": "sağol",
    "bi": "bir", "bişey": "bir şey", "birşey": "bir şey", "herşey": "her şey",
    "hiçbirşey": "hiçbir şey", "uyg": "uygulama", "app": "uygulama",
    "hsp": "hesap", "msj": "mesaj", "sn": "sayın", "dk": "dakika",
    "vs": "vesaire", "vb": "ve benzeri", "pls": "lütfen", "lutfen": "lütfen",
    "knk": "kanka", "cnm": "canım", "ins": "inşallah",
}

TR_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def base_clean(text: str | None) -> str:
    """Light, model-friendly cleaning: keeps case, punctuation and emojis."""
    if not text:
        return ""
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text).translate(QUOTES)
    text = ELONGATION_RE.sub(r"\1\1", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def extract_emojis(text: str) -> str:
    return "".join(e["emoji"] for e in emoji.emoji_list(text))


def strip_noise(text: str) -> str:
    """Remove URLs, e-mails, phone numbers and emojis."""
    text = URL_RE.sub(" ", text)
    text = EMAIL_RE.sub(" ", text)
    text = PHONE_RE.sub(" ", text)
    return emoji.replace_emoji(text, " ")


def count_words(text: str) -> int:
    """Number of alphabetic tokens, ignoring emojis, numbers and URLs."""
    return len(WORD_RE.findall(strip_noise(text)))


def tr_lower(text: str) -> str:
    """Turkish-aware lower-casing (I -> ı, İ -> i), which str.lower() gets wrong."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def _map_tokens(text: str, mapping: dict[str, str]) -> str:
    return WORD_RE.sub(lambda m: mapping.get(m.group(), m.group()), text)


class CorpusDeasciifier:
    """Restore Turkish characters in words typed without them ("cok" -> "çok").

    The mapping is learned from the corpus itself: an ASCII-only word is
    replaced by its Turkish-character spelling when that spelling appears in
    the corpus at least ``ratio`` times as often. Words with no attested
    Turkish spelling (e.g. "kart", "para") are left untouched.
    """

    def __init__(self, texts: Iterable[str], min_count: int = 5, ratio: float = 2.0):
        counts = Counter(tok for t in texts for tok in WORD_RE.findall(t))
        best: dict[str, str] = {}
        for tok, c in counts.items():
            ascii_form = tok.translate(TR_ASCII)
            if ascii_form != tok and c >= min_count and (
                    ascii_form not in best or c > counts[best[ascii_form]]):
                best[ascii_form] = tok
        self.mapping = {a: v for a, v in best.items()
                        if counts[v] >= ratio * counts.get(a, 0)}

    def __call__(self, text: str) -> str:
        return _map_tokens(text, self.mapping)


def _expand_en_contractions(text: str) -> str:
    text = _map_tokens(text, EN_CONTRACTIONS)
    text = text.replace("can't", "cannot").replace("won't", "will not")
    text = text.replace("it's", "it is").replace("that's", "that is")
    text = re.sub(r"'s\b", "", text)               # possessive: "paypal's" -> "paypal"
    for suffix, repl in EN_SUFFIXES:
        text = text.replace(suffix, repl)
    return text


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def normalize(text: str, lang: str, deasciify: CorpusDeasciifier | None = None) -> str:
    """Aggressive normalisation for keyword-based analysis.

    ``text`` is expected to have gone through ``base_clean`` already.
    """
    text = strip_noise(text)
    if lang == "tr":
        text = tr_lower(text)
        text = re.sub(r"(\w+)'\w+", r"\1", text)   # drop suffixes: "papara'ya" -> "papara"
        if deasciify is not None:
            text = deasciify(text)
        text = _map_tokens(text, TR_ABBREVIATIONS)
    else:
        text = text.lower().replace("w/o", "without").replace("w/", "with ")
        text = _expand_en_contractions(text)
        text = _map_tokens(text, EN_ABBREVIATIONS)
    text = re.sub(r"[^\w\s]|_|\d", " ", text)     # punctuation, digits
    return WHITESPACE_RE.sub(" ", text).strip()
