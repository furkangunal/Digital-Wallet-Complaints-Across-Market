"""Candidate sentiment models and a common scoring interface.

Every model, whatever its native label scheme (2-class, 3-class or 1-5
stars), is mapped to the same output: probabilities for negative, neutral
and positive, plus a polarity score ``p_pos - p_neg`` in [-1, 1]. This lets
models with different label sets be compared and swapped freely.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch
from tqdm.auto import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# (neg, neu, pos) weight of each native label
NEG, NEU, POS = (1, 0, 0), (0, 1, 0), (0, 0, 1)
THREE_CLASS = {"negative": NEG, "neutral": NEU, "positive": POS}


@dataclass(frozen=True)
class ModelSpec:
    key: str
    hf_id: str
    langs: tuple[str, ...]
    label_map: dict[str, tuple[int, int, int]] = field(default_factory=lambda: THREE_CLASS)
    note: str = ""


MODELS: dict[str, ModelSpec] = {
    m.key: m
    for m in [
        ModelSpec("xlmr", "cardiffnlp/twitter-xlm-roberta-base-sentiment", ("en", "tr"),
                  note="multilingual XLM-R, fine-tuned on tweets in 8 languages"),
        ModelSpec("mbert_stars", "nlptown/bert-base-multilingual-uncased-sentiment", ("en", "tr"),
                  label_map={"1 star": NEG, "2 stars": NEG, "3 stars": NEU,
                             "4 stars": POS, "5 stars": POS},
                  note="multilingual BERT, fine-tuned on product reviews (1-5 stars)"),
        ModelSpec("en_roberta", "cardiffnlp/twitter-roberta-base-sentiment-latest", ("en",),
                  note="English RoBERTa, fine-tuned on tweets"),
        ModelSpec("tr_bert", "savasy/bert-base-turkish-sentiment-cased", ("tr",),
                  label_map={"negative": NEG, "positive": POS, "label_0": NEG, "label_1": POS},
                  note="Turkish BERT, fine-tuned on Turkish product reviews and tweets (binary)"),
    ]
}


def device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class SentimentScorer:
    def __init__(self, spec: ModelSpec, max_length: int = 256):
        self.spec = spec
        self.max_length = max_length
        self.tokenizer = AutoTokenizer.from_pretrained(spec.hf_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(spec.hf_id)
        self.model.to(device()).eval()
        if device().type == "cuda":
            self.model.half()

        labels = [self.model.config.id2label[i].lower()
                  for i in range(self.model.config.num_labels)]
        missing = [l for l in labels if l not in spec.label_map]
        if missing:
            raise ValueError(f"{spec.key}: no mapping for labels {missing}")
        # (num_labels x 3) matrix that folds native probabilities into neg/neu/pos
        self.fold = np.array([spec.label_map[l] for l in labels], dtype=np.float32)

    @torch.inference_mode()
    def score(self, texts: list[str], batch_size: int = 32, progress: bool = True) -> np.ndarray:
        """Return an (n, 3) array of negative / neutral / positive probabilities."""
        # Sorting by length keeps padding (and therefore memory and time) low.
        order = np.argsort([len(t) for t in texts])
        out = np.zeros((len(texts), 3), dtype=np.float32)
        batches = range(0, len(texts), batch_size)
        for start in tqdm(batches, desc=self.spec.key, disable=not progress):
            idx = order[start:start + batch_size]
            enc = self.tokenizer([texts[i] for i in idx], padding=True, truncation=True,
                                 max_length=self.max_length, return_tensors="pt").to(device())
            probs = torch.softmax(self.model(**enc).logits.float(), dim=-1).cpu().numpy()
            out[idx] = probs @ self.fold
        return out

    def unload(self) -> None:
        del self.model
        if device().type == "cuda":
            torch.cuda.empty_cache()
