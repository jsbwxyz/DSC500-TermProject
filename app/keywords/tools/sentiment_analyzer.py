"""
Sentiment Analysis Module
Entity-level sentiment analysis for articles using spaCy NER + RoBERTa.

Identifies named entities (organizations, people, products) within article
text and scores the sentiment of sentences containing those entities.
Mirrors the article dict interface used by keyword_extractor.py.

Pipeline:
    article dict (paragraphs) → spaCy NER → entities
                              → RoBERTa   → sentiment per entity
"""

import warnings
warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Model setup
# The model needs preparation loading the models
#   and weights needed
# ---------------------------------------------------------------------------

def ensure_models():
    """
    Download spaCy model and HuggingFace weights on first run.
    Safe to call repeatedly — skips if already present.
    """
    import subprocess, sys

    # spaCy English model (medium — includes NER)
    try:
        import spacy
        spacy.load("en_core_web_md")
    except OSError:
        print("Downloading spaCy model: en_core_web_md")
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", "en_core_web_md"],
            check=True
        )

    # HuggingFace transformers (RoBERTa sentiment)
    try:
        from transformers import pipeline as hf_pipeline
        hf_pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            truncation=True
        )
    except Exception:
        print("Downloading RoBERTa model (first run only — ~500MB)...")
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        AutoTokenizer.from_pretrained(
            "cardiffnlp/twitter-roberta-base-sentiment-latest"
        )
        AutoModelForSequenceClassification.from_pretrained(
            "cardiffnlp/twitter-roberta-base-sentiment-latest"
        )


# ---------------------------------------------------------------------------
# Label mapping
# RoBERTa cardiffnlp labels: LABEL_0 = negative, LABEL_1 = neutral, LABEL_2 = positive
# ---------------------------------------------------------------------------

_LABEL_MAP = {
    "LABEL_0": "negative",
    "LABEL_1": "neutral",
    "LABEL_2": "positive",
    # model may also return these directly
    "negative": "negative",
    "neutral":  "neutral",
    "positive": "positive",
}

# Entity types to track — focus on named real-world entities
_ENTITY_TYPES = {"ORG", "PERSON", "PRODUCT", "GPE", "NORP"}


# ---------------------------------------------------------------------------
# Core analysis
#   A RoBERTa algorithm is ran on each sentence
#       then it is tokenized
# ---------------------------------------------------------------------------

def analyze_entity_sentiment(text, top_n=10):
    """
    Extract named entities from text and score sentiment per entity.

    For each entity, find every sentence that mentions it, run RoBERTa
    on those sentences, and return averaged compound sentiment.

    Args:
        text (str or list): Article text or list of paragraphs.
        top_n (int): Maximum number of entities to return.

    Returns:
        list: Dicts sorted by mention count, each containing:
            {
                'entity':          str,   # entity surface form
                'entity_type':     str,   # spaCy NER label
                'sentiment':       str,   # 'positive' | 'neutral' | 'negative'
                'confidence':      float, # model confidence for winning label (0–1)
                'mentions':        int,   # sentences entity appears in
            }
    """
    import nltk
    import spacy
    from transformers import pipeline as hf_pipeline
    from nltk.tokenize import sent_tokenize

    nltk.download("punkt_tab", quiet=True)

    if not text:
        return []

    # if the instance is a paragraph list,
    #   flatten it
    if isinstance(text, list):
        text = " ".join(text)

    # core spacey models are loaded
    #    primarily in English
    #    more languages can be added in the future
    nlp = spacy.load("en_core_web_md")
    classifier = hf_pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-roberta-base-sentiment-latest",
        truncation=True,
        max_length=512,
    )

    # --- Named entity recognition ---
    doc = nlp(text)
    entity_map = {}  # canonical_name → {'type': ..., 'variants': set()}

    # ensure labels are not in the known entity types
    for ent in doc.ents:
        if ent.label_ not in _ENTITY_TYPES:
            continue
        name = ent.text.strip()
        key  = name.lower()
        if key not in entity_map:
            entity_map[key] = {"canonical": name, "type": ent.label_}

    if not entity_map:
        return []

    # --- Sentence tokenization ---
    sentences = sent_tokenize(text)

    # --- Score each entity ---
    results = []

    for key, meta in entity_map.items():
        entity_name = meta["canonical"]

        # Find sentences mentioning this entity (case-insensitive)
        relevant = [s for s in sentences if key in s.lower()]

        if not relevant:
            continue

        # Run classifier on each relevant sentence
        raw_scores = classifier(relevant)

        # Map labels and average confidence per sentiment class
        pos_scores, neu_scores, neg_scores = [], [], []
        for score_dict in raw_scores:
            label = _LABEL_MAP.get(score_dict["label"], "neutral")
            conf  = score_dict["score"]
            if label == "positive":
                pos_scores.append(conf)
            elif label == "negative":
                neg_scores.append(conf)
            else:
                neu_scores.append(conf)

        # Determine dominant sentiment by total weighted score
        totals = {
            "positive": sum(pos_scores),
            "negative": sum(neg_scores),
            "neutral":  sum(neu_scores),
        }
        dominant = max(totals, key=totals.get)
        dominant_scores = pos_scores if dominant == "positive" \
                     else neg_scores if dominant == "negative" \
                     else neu_scores

        avg_confidence = round(
            sum(dominant_scores) / len(dominant_scores), 3
        ) if dominant_scores else 0.0

        results.append({
            "entity":      entity_name,
            "entity_type": meta["type"],
            "sentiment":   dominant,
            "confidence":  avg_confidence,
            "mentions":    len(relevant),
        })

    # Sort by mention count descending, return top_n
    results.sort(key=lambda x: x["mentions"], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# Article dict interface — mirrors keyword_extractor.py
# ---------------------------------------------------------------------------

def analyze_article_sentiment(article_dict, top_n=10):
    """
    Run entity sentiment analysis on an article dictionary.

    Args:
        article_dict (dict): Article with 'paragraphs' key (same format
                             as keyword_extractor.py expects).
        top_n (int): Maximum entities to return.

    Returns:
        list: Entity sentiment results.
    """
    paragraphs = article_dict.get("paragraphs", [])
    if not paragraphs:
        return []
    return analyze_entity_sentiment(paragraphs, top_n=top_n)


def add_sentiment_to_articles(articles, top_n=10, verbose=True):
    """
    Add entity sentiment to a list of article dicts.

    Mirrors add_keywords_to_articles() in keyword_extractor.py.
    Adds an 'entity_sentiment' key to each article dict in-place.

    Args:
        articles (list): List of article dicts with 'paragraphs' key.
        top_n (int): Max entities per article.
        verbose (bool): Print progress.

    Returns:
        list: Articles with 'entity_sentiment' field added.
    """
    if verbose:
        print(f"\nAnalyzing entity sentiment for {len(articles)} articles...")

    for i, article in enumerate(articles, 1):
        if verbose and i % 5 == 0:
            print(f"  Processing article {i}/{len(articles)}...")

        sentiment_results = analyze_article_sentiment(article, top_n=top_n)
        article["entity_sentiment"] = sentiment_results

        if verbose and sentiment_results:
            preview = ", ".join(
                f"{e['entity']} ({e['sentiment']})"
                for e in sentiment_results[:3]
            )
            print(f"    [{i}] Top entities: {preview}")

    if verbose:
        successful = sum(1 for a in articles if a.get("entity_sentiment"))
        print(f"✓ Sentiment analyzed for {successful} articles")

    return articles


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ensure_models()

    sample_text = """
    Apple reported record earnings this quarter, exceeding analyst expectations.
    Tim Cook credited strong iPhone sales and the growing services division.
    Meanwhile, Microsoft announced sweeping layoffs affecting thousands of employees.
    Satya Nadella defended the decision, citing a need to refocus on AI investment.
    The European Union has raised concerns about both companies' data practices,
    with regulators signaling potential fines under the Digital Markets Act.
    """

    print("Testing entity sentiment analysis...")
    results = analyze_entity_sentiment(sample_text, top_n=10)

    print(f"\nFound {len(results)} entities:\n")
    for r in results:
        print(
            f"  {r['entity']:<20} [{r['entity_type']:<7}] "
            f"{r['sentiment']:<9} confidence={r['confidence']:.3f}  "
            f"mentions={r['mentions']}"
        )
