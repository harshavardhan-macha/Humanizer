"""
Humanization Scorer
Measures how human-like text is by checking:
- Sentence length variance
- AI keyword presence
- Lexical diversity
- Contraction usage
- Readability metrics
Author: NLP Expert
"""

import logging
import re
from typing import Dict, Tuple
from collections import Counter
from nltk.tokenize import sent_tokenize, word_tokenize
import statistics

logger = logging.getLogger(__name__)

# AI-SPECIFIC PHRASES THAT ARE RED FLAGS
AI_PHRASES = {
    "in conclusion": 1.5,
    "furthermore": 1.2,
    "moreover": 1.2,
    "it is worth noting": 2.0,
    "in summary": 1.5,
    "as mentioned": 1.2,
    "the fact that": 0.8,
    "utilize": 1.5,
    "leverage": 1.5,
    "comprehensive": 1.0,
    "crucial": 0.8,
    "delve into": 1.5,
    "paradigm shift": 2.0,
    "cutting-edge": 0.8,
    "state-of-the-art": 1.0,
}

# HUMAN-SIGNATURE WORDS/PATTERNS
HUMAN_SIGNATURES = {
    "I think": 1.0,
    "you know": 0.8,
    "I mean": 0.8,
    "like": 0.6,
    "basically": 0.7,
    "honestly": 1.0,
    "I don't": 0.8,
    "don't": 0.6,
    "can't": 0.6,
    "won't": 0.6,
    "it's": 0.8,
    "that's": 0.8,
    "I'm": 0.8,
}

class HumanizationScorer:
    """
    Scores text on humanization quality.
    
    Metrics:
    - Sentence length variance (0-1): humans vary sentence length
    - AI phrase penalty (0-20): detects formal AI language
    - Lexical diversity (0-1): ratio of unique words
    - Contraction presence (0-10): use of contractions
    - Overall score (0-100)
    """
    
    @staticmethod
    def score_text(text: str) -> Dict:
        """
        Score text on humanization quality.
        
        Returns dict with:
        {
            'overall_score': 0-100,
            'sentence_variance': 0-1,
            'ai_phrase_penalty': 0-20,
            'lexical_diversity': 0-1,
            'contraction_score': 0-10,
            'human_signature_score': 0-10,
            'details': {...}
        }
        """
        try:
            # Calculate each component
            sentence_variance = HumanizationScorer._sentence_length_variance(text)
            ai_phrase_penalty = HumanizationScorer._ai_phrase_detection(text)
            lexical_diversity = HumanizationScorer._lexical_diversity(text)
            contraction_score = HumanizationScorer._contraction_score(text)
            human_signature_score = HumanizationScorer._human_signature_score(text)
            
            # Weighted overall score (0-100)
            # Higher is better
            score = (
                (sentence_variance * 0.2) * 100 +        # 20% for variety
                (max(0, 20 - ai_phrase_penalty) * 0.25) * 100 + # 25% for avoiding AI language
                (lexical_diversity * 0.2) * 100 +         # 20% for vocabulary diversity
                (contraction_score * 0.15) * 100 +        # 15% for natural contractions
                (human_signature_score * 0.2) * 100       # 20% for human patterns
            ) / 100
            
            # Normalize to 0-100
            overall_score = min(100, max(0, score))
            
            return {
                'overall_score': overall_score,
                'sentence_variance': sentence_variance,
                'ai_phrase_penalty': ai_phrase_penalty,  # Lower is better
                'lexical_diversity': lexical_diversity,
                'contraction_score': contraction_score,
                'human_signature_score': human_signature_score,
                'details': {
                    'timestamp': __import__('datetime').datetime.now().isoformat(),
                    'text_length': len(text),
                    'word_count': len(text.split()),
                    'sentence_count': len(sent_tokenize(text)),
                }
            }
        
        except Exception as e:
            logger.error(f"Error scoring text: {str(e)}")
            return {
                'overall_score': 0,
                'error': str(e)
            }
    
    @staticmethod
    def _sentence_length_variance(text: str) -> float:
        """
        Score sentence length variance.
        Humans write with varied sentence lengths.
        Return: 0-1 (higher is more varied)
        """
        try:
            sentences = sent_tokenize(text)
            if len(sentences) < 2:
                return 0.5  # Default for very short text
            
            lengths = [len(sent.split()) for sent in sentences]
            
            # Calculate coefficient of variation (std / mean)
            mean_length = __import__('statistics').mean(lengths)
            if mean_length == 0:
                return 0.0
            
            variance = __import__('statistics').variance(lengths) if len(lengths) > 1 else 0
            std_dev = variance ** 0.5
            cv = std_dev / mean_length
            
            # Normalize: cv > 0.8 is good variety, < 0.3 is robotic
            # Map to 0-1 scale
            variety_score = min(1.0, cv / 0.8)
            return variety_score
        
        except Exception as e:
            logger.debug(f"Error computing sentence variance: {e}")
            return 0.5
    
    @staticmethod
    def _ai_phrase_detection(text: str) -> float:
        """
        Penalize presence of AI phrases.
        Return: penalty score (0-20, lower is better)
        """
        penalty = 0.0
        text_lower = text.lower()
        
        for phrase, weight in AI_PHRASES.items():
            count = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
            penalty += count * weight
        
        # Cap at 20 to not dominate score
        return min(20.0, penalty)
    
    @staticmethod
    def _lexical_diversity(text: str) -> float:
        """
        Score lexical diversity.
        Higher unique words / total words = more diverse vocabulary.
        Return: 0-1
        """
        try:
            words = word_tokenize(text.lower())
            # Filter stop-words-ish tokens
            words = [w for w in words if w.isalnum() and len(w) > 2]
            
            if not words:
                return 0.0
            
            unique_words = len(set(words))
            total_words = len(words)
            
            # Type-token ratio
            diversity = unique_words / total_words if total_words > 0 else 0
            
            # Humans typically have 0.4-0.7 diversity
            # Clamp to 0-1 scale
            return min(1.0, diversity)  # Higher is better
        
        except Exception as e:
            logger.debug(f"Error computing lexical diversity: {e}")
            return 0.5
    
    @staticmethod
    def _contraction_score(text: str) -> float:
        """
        Score presence of contractions.
        Contractions are signature of human writing.
        Return: 0-10 (higher is more human)
        """
        contractions = [
            "don't", "doesn't", "didn't",
            "can't", "couldn't", "won't", "wouldn't",
            "isn't", "aren't", "wasn't", "weren't",
            "haven't", "hasn't", "hadn't",
            "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
            "i've", "you've", "we've", "they've",
            "i'll", "you'll", "he'll", "she'll", "it'll", "we'll", "they'll",
            "that's", "there's", "what's", "who's",
        ]
        
        text_lower = text.lower()
        count = sum(1 for c in contractions if c in text_lower)
        
        # Scale: more contractions = higher score
        # 0-5 contractions = 0-10 points
        score = min(10.0, (count / 5.0) * 10.0)
        return score
    
    @staticmethod
    def _human_signature_score(text: str) -> float:
        """
        Score presence of typical human language patterns.
        Return: 0-10
        """
        text_lower = text.lower()
        score = 0.0
        
        for phrase, weight in HUMAN_SIGNATURES.items():
            occurrences = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
            score += occurrences * weight
        
        # Cap at 10
        return min(10.0, score)


def compute_humanization_score(text: str) -> Dict:
    """Convenience wrapper"""
    return HumanizationScorer.score_text(text)


def print_score_report(before: str, after: str):
    """Print before/after comparison"""
    scorer = HumanizationScorer()
    before_score = scorer.score_text(before)
    after_score = scorer.score_text(after)
    
    logger.info("\n" + "="*60)
    logger.info("HUMANIZATION SCORE REPORT")
    logger.info("="*60)
    logger.info(f"{'Metric':<30} {'Before':>10} {'After':>10} {'Change':>10}")
    logger.info("-"*60)
    
    metrics = [
        ('Overall Score', 'overall_score'),
        ('Sentence Variance', 'sentence_variance'),
        ('AI Phrases (penalty)', 'ai_phrase_penalty'),
        ('Lexical Diversity', 'lexical_diversity'),
        ('Contraction Score', 'contraction_score'),
        ('Human Signature', 'human_signature_score'),
    ]
    
    for label, key in metrics:
        before_val = before_score.get(key, 0)
        after_val = after_score.get(key, 0)
        change = after_val - before_val
        
        # Special handling for penalty (lower is better)
        if 'penalty' in key:
            change = before_val - after_val
            logger.info(f"{label:<30} {before_val:>10.2f} {after_val:>10.2f} {change:>10.2f}")
        else:
            logger.info(f"{label:<30} {before_val:>10.2f} {after_val:>10.2f} {change:>10.2f}")
    
    logger.info("="*60 + "\n")
    
    return before_score, after_score
