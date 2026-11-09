"""LoCoMo category-aware F1, following pinned task_eval/evaluation.py.

Source: https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/task_eval/evaluation.py
The repository's simpler set-token F1 is retained separately for audit.
"""
from collections import Counter
import re
import statistics
import string
from nltk.stem import PorterStemmer

_stemmer = PorterStemmer()


def normalized_tokens(text):
    text = ''.join(c for c in str(text).lower().replace(',', '') if c not in string.punctuation)
    text = re.sub(r'\b(a|an|the|and)\b', ' ', text)
    return [_stemmer.stem(token) for token in text.split()]


def token_f1(prediction, reference):
    a, b = normalized_tokens(prediction), normalized_tokens(reference)
    overlap = sum((Counter(a) & Counter(b)).values())
    return 2 * overlap / (len(a) + len(b)) if overlap else 0.0


def locomo_f1(prediction, reference, category):
    if category == 1:
        answers = [a.strip() for a in str(prediction).split(',')]
        references = [r.strip() for r in str(reference).split(',')]
        return statistics.mean(max(token_f1(a, r) for a in answers) for r in references)
    if category == 3:
        reference = str(reference).split(';')[0].strip()
    if category not in [2, 3, 4]:
        raise ValueError('Formal experiment covers only categories 1–4.')
    return token_f1(prediction, reference)
