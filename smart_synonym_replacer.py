"""
Smart Synonym Replacement with POS Tagging and AI-Word Detection
Replaces only AI-suspicious words with natural alternatives, respecting grammar.
Author: NLP Expert
"""

import logging
import random
import re
from typing import Tuple, Optional, List, Dict
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
import requests
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

# HIGH-CONFIDENCE AI WORDS RANKED BY SUSPICION LEVEL
AI_WORD_REGISTRY = {
    # Level 1: ALMOST ALWAYS AI
    "utilize": (1, ["use", "employ"]),
    "leverage": (1, ["use", "take advantage of"]),
    "delve": (1, ["dive", "explore", "get into"]),
    "notwithstanding": (1, ["despite", "despite", "though"]),
    "heretofore": (1, ["before", "previously"]),
    
    # Level 2: VERY LIKELY AI
    "comprehensive": (2, ["complete", "full", "thorough"]),
    "crucial": (2, ["critical", "key", "important"]),
    "notably": (2, ["especially", "particularly", "importantly"]),
    "facilitate": (2, ["help", "make easier", "enable"]),
    "robust": (2, ["strong", "solid", "tough"]),
    
    # Level 3: PROBABLY AI
    "paradigm": (3, ["model", "example", "pattern"]),
    "synergy": (3, ["teamwork", "working together"]),
    "optimize": (3, ["improve", "make better"]),
    "enhance": (3, ["improve", "make better"]),
    "implement": (3, ["put into place", "do", "carry out"]),
    "furthermore": (3, ["also", "plus", "besides"]),
    "moreover": (3, ["also", "plus", "and"]),
}

# NLTK POS TAGS TO WORDNET POS
POS_MAP = {
    'NN': wordnet.NOUN,      # Noun
    'NNS': wordnet.NOUN,     # Plural noun
    'NNP': wordnet.NOUN,     # Proper noun
    'NNPS': wordnet.NOUN,    # Plural proper noun
    'VB': wordnet.VERB,      # Verb
    'VBD': wordnet.VERB,     # Past tense
    'VBG': wordnet.VERB,     # Gerund
    'VBN': wordnet.VERB,     # Past participle
    'VBP': wordnet.VERB,     # Present
    'VBZ': wordnet.VERB,     # 3rd person singular
    'JJ': wordnet.ADJ,       # Adjective
    'JJR': wordnet.ADJ,      # Comparative
    'JJS': wordnet.ADJ,      # Superlative
    'RB': wordnet.ADV,       # Adverb
    'RBR': wordnet.ADV,      # Comparative
    'RBS': wordnet.ADV,      # Superlative
}

class SmartSynonymReplacer:
    """
    Replaces only AI-suspicious words with natural synonyms.
    Features:
    - POS-tag aware (noun→noun, verb→verb)
    - Prefers shorter, more casual synonyms
    - Caps replacements per sentence
    - Avoids proper nouns and short words
    """
    
    def __init__(self, oxford_app_id: str = None, oxford_app_key: str = None):
        load_dotenv()
        self.oxford_app_id = oxford_app_id or os.getenv("OXFORD_APP_ID")
        self.oxford_app_key = oxford_app_key or os.getenv("OXFORD_APP_KEY")
        self.synonym_cache: Dict[str, List[str]] = {}
        self.replaced_words: set = set()  # Track words already replaced
        
        if self.oxford_app_id and self.oxford_app_key:
            logger.info("✅ Smart Synonym Replacer: Oxford API enabled")
        else:
            logger.info("⚠️ Smart Synonym Replacer: Oxford API unavailable, using WordNet only")
    
    def replace_in_text(self, text: str, max_replacements_per_sentence: int = 2) -> Tuple[str, Dict]:
        """
        Replace AI words in text with smart synonym selection.
        
        Args:
            text: Input text
            max_replacements_per_sentence: Cap on replacements (prevent over-substitution)
        
        Returns:
            (humanized_text, stats)
        """
        if not text.strip():
            return text, {"replacements": 0, "words_targeted": [], "words_skipped": []}
        
        stats = {
            "replacements": 0,
            "words_targeted": [],
            "words_skipped": []
        }
        
        try:
            # Split into sentences for per-sentence caps
            sentences = text.split('. ')
            result_sentences = []
            
            for sentence in sentences:
                if not sentence.strip():
                    result_sentences.append(sentence)
                    continue
                
                # Tokenize and tag
                tokens = word_tokenize(sentence)
                pos_tags = pos_tag(tokens)
                
                # Track replacements in this sentence
                sentence_replacements = 0
                new_tokens = []
                
                for i, (token, pos) in enumerate(pos_tags):
                    # Check if word should be replaced
                    lower_token = token.lower()
                    
                    if (lower_token in AI_WORD_REGISTRY and 
                        sentence_replacements < max_replacements_per_sentence and
                        lower_token not in self.replaced_words and
                        len(token) >= 4 and  # Skip short words
                        not token[0].isupper()):  # Skip proper nouns
                        
                        # Get POS category
                        pos_category = POS_MAP.get(pos, None)
                        
                        # Find synonym
                        synonym, was_replaced = self._find_synonym(token, pos_category)
                        
                        if was_replaced and synonym != token:
                            # Preserve capitalization
                            if token[0].isupper():
                                synonym = synonym.capitalize()
                            
                            new_tokens.append(synonym)
                            sentence_replacements += 1
                            self.replaced_words.add(lower_token)
                            stats["replacements"] += 1
                            stats["words_targeted"].append((token, synonym))
                            logger.debug(f"  ✓ {token} → {synonym}")
                        else:
                            new_tokens.append(token)
                            stats["words_skipped"].append(token)
                    else:
                        new_tokens.append(token)
                
                # Reconstruct sentence
                result_sentence = ' '.join(new_tokens)
                # Fix punctuation spacing
                result_sentence = re.sub(r'\s+([.,!?])', r'\1', result_sentence)
                result_sentences.append(result_sentence)
            
            result_text = '. '.join(result_sentences)
            return result_text, stats
            
        except Exception as e:
            logger.error(f"Error in synonym replacement: {str(e)}")
            return text, stats
    
    def _find_synonym(self, word: str, pos_category: Optional[int] = None) -> Tuple[str, bool]:
        """
        Find the best synonym for a word.
        
        Returns:
            (synonym, was_replaced)
        """
        word_lower = word.lower()
        
        # Check AI registry first (highest confidence)
        if word_lower in AI_WORD_REGISTRY:
            level, replacements = AI_WORD_REGISTRY[word_lower]
            # Use provided replacements (highest quality)
            best = self._select_best_synonym(replacements, pos_category)
            if best and best != word_lower:
                return best, True
        
        # Try Oxford API
        if self.oxford_app_id and self.oxford_app_key:
            oxford_syns = self._get_oxford_synonyms(word_lower)
            if oxford_syns:
                best = self._select_best_synonym(oxford_syns, pos_category)
                if best and best != word_lower:
                    return best, True
        
        # Fallback to WordNet
        wordnet_syns = self._get_wordnet_synonyms(word_lower, pos_category)
        if wordnet_syns:
            best = self._select_best_synonym(wordnet_syns, pos_category)
            if best and best != word_lower:
                return best, True
        
        return word, False
    
    def _select_best_synonym(self, candidates: List[str], pos_category: Optional[int] = None) -> str:
        """
        Select BEST synonym from candidates.
        Preference: shorter, more common, casual-sounding words.
        """
        if not candidates:
            return ""
        
        # Prefer shorter words (more casual)
        candidates = sorted(candidates, key=lambda x: (len(x.split()), len(x)))
        
        # Return first (shortest)
        return candidates[0] if candidates else ""
    
    def _get_oxford_synonyms(self, word: str) -> List[str]:
        """Fetch synonyms from Oxford Dictionary API"""
        if word in self.synonym_cache:
            return self.synonym_cache[word]
        
        try:
            url = f"https://od-api.oxforddictionaries.com/api/v2/thesaurus/en/{word}"
            headers = {
                "app_id": self.oxford_app_id,
                "app_key": self.oxford_app_key,
            }
            response = requests.get(url, headers=headers, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                synonyms = []
                
                # Extract from senses
                for entry in data.get("results", [{}])[0].get("lexicalEntries", []):
                    for sense in entry.get("entries", [{}])[0].get("senses", []):
                        for syn in sense.get("synonyms", []):
                            text = syn.get("text", "").lower()
                            if text and text.isalpha() and text != word:
                                synonyms.append(text)
                
                # Cache and return unique
                unique_syns = list(set(synonyms))[:5]
                self.synonym_cache[word] = unique_syns
                return unique_syns
        
        except Exception as e:
            logger.debug(f"Oxford API error for '{word}': {str(e)}")
        
        return []
    
    def _get_wordnet_synonyms(self, word: str, pos_category: Optional[int] = None) -> List[str]:
        """Fetch synonyms from WordNet"""
        try:
            synonyms = []
            synsets = wordnet.synsets(word, pos=pos_category)
            
            for synset in synsets[:3]:  # Check first 3 synsets
                for lemma in synset.lemmas():
                    synonym = lemma.name().replace('_', ' ').lower()
                    
                    # Quality checks
                    if (synonym != word and 
                        synonym.isalpha() and
                        len(synonym.split()) == 1):  # Single word only
                        synonyms.append(synonym)
            
            return list(set(synonyms))[:5]
        
        except Exception as e:
            logger.debug(f"WordNet error for '{word}': {str(e)}")
            return []


# Export global instance
smart_replacer = SmartSynonymReplacer()

def replace_ai_words(text: str) -> Tuple[str, Dict]:
    """Convenience wrapper"""
    return smart_replacer.replace_in_text(text)
