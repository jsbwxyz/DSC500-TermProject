"""
Keyword Extraction Module
Extracts meaningful keywords from text using NLTK with confidence scores
"""

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist

# Download required NLTK data (run once)
def ensure_nltk_data():
    """Download necessary NLTK data if not already present"""
    required_data = [
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('tokenizers/punkt', 'punkt'),
        ('corpora/stopwords', 'stopwords'),
        ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger'),
        ('taggers/averaged_perceptron_tagger_eng', 'averaged_perceptron_tagger_eng')
    ]
    
    for path, name in required_data:
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                print(f"Downloading NLTK data: {name}")
                nltk.download(name, quiet=True)
            except Exception as e:
                print(f"  Note: {name} download attempt completed (may already exist)")

# Ensure NLTK data is available
ensure_nltk_data()

def extract_keywords(text, num_keywords=10):
    """
    Extract keywords from text using NLTK with confidence scores
    
    Args:
        text (str or list): Text content to analyze (can be a list of paragraphs)
        num_keywords (int): Number of top keywords to return
        
    Returns:
        list: List of dicts with 'keyword', 'frequency', and 'confidence' keys
    """
    if not text:
        return []
    
    try:
        # Combine all text if it's a list
        if isinstance(text, list):
            text = " ".join(text)
        
        # Convert to lowercase and tokenize
        tokens = word_tokenize(text.lower())
        
        # Remove stopwords and non-alphabetic tokens
        stop_words = set(stopwords.words('english'))
        
        # Add common words that aren't meaningful keywords
        stop_words.update([
            'said', 'would', 'could', 'also', 'may', 'one', 'two', 'three',
            'first', 'last', 'new', 'year', 'years', 'time', 'get', 'make',
            'like', 'just', 'know', 'people', 'think', 'going', 'want',
            'told', 'according', 'say', 'says'
        ])
        
        # Filter tokens: only alphabetic, not stopwords, length > 3
        filtered_tokens = [
            word for word in tokens 
            if word.isalpha() and word not in stop_words and len(word) > 3
        ]
        
        if not filtered_tokens:
            return []
        
        # POS tagging to prioritize nouns and proper nouns
        pos_tags = nltk.pos_tag(filtered_tokens)
        
        # Weight different POS tags to prioritize important word types
        weighted_words = []
        for word, tag in pos_tags:
            if tag.startswith('NN'):  # Nouns (NN, NNS, NNP, NNPS)
                weighted_words.extend([word] * 3)  # Triple weight for nouns
            elif tag.startswith('JJ'):  # Adjectives (JJ, JJR, JJS)
                weighted_words.extend([word] * 2)  # Double weight for adjectives
            else:
                weighted_words.append(word)
        
        # Calculate frequency distribution
        freq_dist = FreqDist(weighted_words)
        
        # Get top keywords
        most_common = freq_dist.most_common(num_keywords)

        # ^^ this piece would possibly be improved to more than just "most common"
        
        if not most_common:
            return []
        
        # Calculate total for confidence scores
        total_count = sum(count for word, count in most_common)
        
        # Format with confidence scores (normalized 0-1)
        keywords_with_confidence = [
            {
                'keyword': word,
                'frequency': count,
                'confidence': round(count / total_count, 3) if total_count > 0 else 0
            }
            for word, count in most_common
        ]
        
        return keywords_with_confidence
    
    except Exception as e:
        print(f"Error extracting keywords: {str(e)}")
        return []

def extract_keywords_from_article(article_dict, num_keywords=15):
    """
    Extract keywords from an article dictionary
    
    Args:
        article_dict (dict): Article with 'paragraphs' key
        num_keywords (int): Number of keywords to extract
        
    Returns:
        list: Keywords with confidence scores
    """
    paragraphs = article_dict.get('paragraphs', [])
    
    if not paragraphs:
        return []
    
    return extract_keywords(paragraphs, num_keywords=num_keywords)

def add_keywords_to_articles(articles, num_keywords=15, verbose=True):
    """
    Add keywords to a list of article dictionaries
    
    Args:
        articles (list): List of article dicts with 'paragraphs' key
        num_keywords (int): Number of keywords per article
        verbose (bool): Print progress messages
        
    Returns:
        list: Articles with 'keywords' field added
    """
    if verbose:
        print(f"\nExtracting keywords from {len(articles)} articles...")
    
    for i, article in enumerate(articles, 1):
        if verbose and i % 5 == 0:
            print(f"  Processing article {i}/{len(articles)}...")
        
        keywords = extract_keywords_from_article(article, num_keywords=num_keywords)
        article['keywords'] = keywords
        
        if verbose and keywords:
            top_3 = ', '.join([k['keyword'] for k in keywords[:3]])
            print(f"    [{i}] Top keywords: {top_3}")
    
    if verbose:
        successful = sum(1 for a in articles if a.get('keywords'))
        print(f"✓ Extracted keywords for {successful} articles")
    
    return articles

# Example usage
if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    Amazon announced a major expansion of its retail operations today.
    The e-commerce giant plans to open new distribution centers across the United States.
    Retail analysts say this move will strengthen Amazon's competitive position in the market.
    The company's retail strategy focuses on faster delivery and improved customer service.
    """
    
    print("Testing keyword extraction...")
    keywords = extract_keywords(sample_text, num_keywords=10)
    
    print(f"\nExtracted {len(keywords)} keywords:")
    for kw in keywords:
        print(f"  - {kw['keyword']}: frequency={kw['frequency']}, confidence={kw['confidence']}")