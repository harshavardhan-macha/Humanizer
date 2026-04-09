"""
Human Error & Variation Generator
Adds subtle, natural human writing patterns to humanized text to make it sound more authentic
"""

import random
import re
import logging
from typing import Tuple, List, Optional
from nltk.tokenize import sent_tokenize, word_tokenize
import nltk

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

logger = logging.getLogger(__name__)

# Natural variations mapping
INFORMAL_CONTRACTIONS = {
    "cannot": ["can't", "cannot"],
    "will not": ["won't", "will not"],
    "shall not": ["shan't", "shall not"],
    "do not": ["don't", "do not"],
    "does not": ["doesn't", "does not"],
    "did not": ["didn't", "did not"],
    "have not": ["haven't", "have not"],
    "has not": ["hasn't", "has not"],
    "had not": ["hadn't", "had not"],
    "is not": ["isn't", "is not"],
    "are not": ["aren't", "are not"],
    "was not": ["wasn't", "was not"],
    "were not": ["weren't", "were not"],
    "should not": ["shouldn't", "should not"],
    "would not": ["wouldn't", "would not"],
    "could not": ["couldn't", "could not"],
    "might not": ["mightn't", "might not"],
    "must not": ["mustn't", "must not"],
    "I am": ["I'm", "I am"],
    "you are": ["you're", "you are"],
    "he is": ["he's", "he is"],
    "she is": ["she's", "she is"],
    "it is": ["it's", "it is"],
    "we are": ["we're", "we are"],
    "they are": ["they're", "they are"],
    "I have": ["I've", "I have"],
    "you have": ["you've", "you have"],
    "we have": ["we've", "we have"],
    "they have": ["they've", "they have"],
    "would have": ["would've", "would have"],
    "could have": ["could've", "could have"],
    "should have": ["should've", "should have"],
    "it has": ["it's", "it has"],
    "are going to": ["gonna", "are going to"],
    "want to": ["wanna", "want to"],
    "going to": ["gonna", "going to"],
    "going to": ["gotta", "got to"],  # "I've gotta go" → "I've got to go"
    "let us": ["let's", "let us"],
    "I would": ["I'd", "I would"],
    "you would": ["you'd", "you would"],
    "he would": ["he'd", "he would"],
    "she would": ["she'd", "she would"],
    "we would": ["we'd", "we would"],
    "they would": ["they'd", "they would"],
    "I had": ["I'd", "I had"],
    "you had": ["you'd", "you had"],
    "we had": ["we'd", "we had"],
    "they had": ["they'd", "they had"],
    "you will": ["you'll", "you will"],
    "I will": ["I'll", "I will"],
    "he will": ["he'll", "he will"],
    "she will": ["she'll", "she will"],
    "it will": ["it'll", "it will"],
    "we will": ["we'll", "we will"],
    "they will": ["they'll", "they will"],
    "there is": ["there's", "there is"],
    "there are": ["there's", "there are"],  # informal, common in speech
    "there was": ["there's", "there was"],
    "there were": ["there's", "there were"],  # also colloquial
    "there has": ["there's", "there has"],
    "there have": ["there's", "there have"],
    "there will": ["there'll", "there will"],
    "what is": ["what's", "what is"],
    "what are": ["what're", "what are"],
    "what has": ["what's", "what has"],
    "what have": ["what've", "what have"],
    "what will": ["what'll", "what will"],
    "who is": ["who's", "who is"],
    "who has": ["who's", "who has"],
    "who will": ["who'll", "who will"],
    "who have": ["who've", "who have"],
    "where is": ["where's", "where is"],
    "when is": ["when's", "when is"],
    "why is": ["why's", "why is"],
    "how is": ["how's", "how is"],
    "how are": ["how're", "how are"],
    "how will": ["how'll", "how will"],

    # Extra “human‑like” casual phrases / slang variants
    "I am going to": ["I'm gonna", "I'm going to", "I am going to"],
    "I do not know": ["I dunno", "I don't know", "I do not know"],
    "you know": ["y'know", "you know"],
    "for example": ["for e.g.", "for example"],
    "because": ["'cause", "because"],
    "cannot see": ["can't see", "cannot see"],
    "I cannot believe": ["I can't believe", "I cannot believe"],
    "do not worry": ["don't worry", "do not worry"],
    "I am not": ["I'm not", "I'm not gonna", "I am not"],
    "I do not think": ["I don't think", "I do not think"],
    "I am just": ["I'm just", "I am just"],
    "I have been": ["I've been", "I have been"],
    "you have been": ["you've been", "you have been"],
    "we have been": ["we've been", "we have been"],
    "they have been": ["they've been", "they have been"],
    "there will be": ["there'll be", "there will be"],
    "that is": ["that's", "that is"],
    "that has": ["that's", "that has"],
    "that will": ["that'll", "that will"],
    "that would": ["that'd", "that would"],
    "that should": ["that should've", "that should have"],
    "that could": ["that could've", "that could have"],
    "that would have": ["that would've", "that would have"],
    "oh my god": ["omg", "oh my god", "OMG"],
    "as soon as possible": ["ASAP", "asap", "as soon as possible"],
    "by the way": ["btw", "BTW", "by the way"],
    "laugh out loud": ["lol", "LOL", "laugh out loud"],
    "see you later": ["cya", "see ya", "see you later"],
    "I am okay": ["I'm okay", "I'm ok", "I am okay"],
    "good night": ["gn", "good night"],
    "good morning": ["gm", "good morning", "very good morning"],
    "see you soon": ["cu soon", "see you soon"],
}

FORMAL_TO_INFORMAL = {
    "certainly": ["sure", "definitely", "yeah"],
    "perhaps": ["maybe", "possibly"],
    "utilize": ["use"],
    "regarding": ["about"],
    "commence": ["start", "begin"],
    "terminate": ["end", "stop"],
    "inquire": ["ask"],
    "assistance": ["help"],
    "procure": ["get", "obtain"],
    "substantial": ["big", "large"],
    "consequently": ["so", "then"],
    "furthermore": ["also", "plus"],
    "however": ["but", "though"],
    "therefore": ["so"],
    "majority": ["most"],
    "implement": ["do", "carry out"],
    "demonstrate": ["show"],
    "numerous": ["many", "lots of"],
    "sufficient": ["enough"],
    "eliminate": ["remove", "get rid of"],
}

# Sentence starters to add variety
SENTENCE_STARTERS = {
    "formal": [
        "According to research,",
        "It is important to note that",
        "In conclusion,",
        "Furthermore,",
        "As mentioned earlier,",
    ],
    "informal": [
        "So basically,",
        "You know,",
        "I mean,",
        "Like,",
        "Honestly,",
        "Honestly speaking,",
        "In my opinion,",
    ]
}

# Filler words that appear naturally in human writing
FILLER_WORDS = ["you know", "like", "basically", "actually", "really", "just", "kind of", "sort of"]

# Uncommon letter/word variations (rare typos that still look natural)
SUBTLE_VARIATIONS = {
    "th": ["th"],  # Keep most
    "the ": ["the "],
}

class HumanVariationEngine:
    """Engine to add natural human variations to text"""
    
    def __init__(self, variation_intensity: float = 0.5):
        """
        Initialize the engine
        
        Args:
            variation_intensity: 0.0 to 1.0, how much variation to add
                0.0 = no variation, 1.0 = maximum variation
        """
        self.variation_intensity = max(0.0, min(1.0, variation_intensity))
        logger.info(f"HumanVariationEngine initialized with intensity: {self.variation_intensity}")
    
    def add_informal_contractions(self, text: str) -> str:
        """Add informal contractions to text"""
        result = text
        word_count = len(text.split())
        intensity = max(1, int(word_count * self.variation_intensity * 0.15))  # More aggressive: ~15% of words
        
        for formal, informal_options in INFORMAL_CONTRACTIONS.items():
            # Find all occurrences
            pattern = re.compile(r'\b' + re.escape(formal) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(result))
            
            if matches:
                # Apply to some matches based on intensity
                num_to_replace = min(max(1, intensity // 3), len(matches))
                for match in random.sample(matches, num_to_replace):
                    start, end = match.span()
                    replacement = random.choice(informal_options)
                    result = result[:start] + replacement + result[end:]
        
        return result
    
    def add_informal_vocabulary(self, text: str) -> str:
        """Replace some formal words with informal alternatives"""
        result = text
        words = text.split()
        num_replacements = max(1, int(len(words) * self.variation_intensity * 0.05))
        
        for formal, informal_options in FORMAL_TO_INFORMAL.items():
            pattern = re.compile(r'\b' + re.escape(formal) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(result))
            
            for match in random.sample(matches, min(num_replacements // 5 + 1, len(matches))):
                start, end = match.span()
                replacement = random.choice(informal_options)
                result = result[:start] + replacement + result[end:]
        
        return result
    
    def add_sentence_length_variation(self, text: str) -> str:
        """Add variation in sentence length and filler words"""
        try:
            sentences = sent_tokenize(text)
            if len(sentences) < 1:
                return text
            
            modified_sentences = []
            for sentence in sentences:
                should_modify = random.random() < (self.variation_intensity * 0.4)
                
                if should_modify:
                    # Sometimes add filler words at sentence start
                    if random.random() < 0.6:
                        filler = random.choice(FILLER_WORDS)
                        sentence = f"{filler}, {sentence}"
                    # Or add filler within the sentence
                    elif random.random() < 0.4:
                        words = sentence.split()
                        if len(words) > 2:
                            filler = random.choice(FILLER_WORDS)
                            insert_pos = random.randint(1, len(words) - 1)
                            words.insert(insert_pos, filler)
                            sentence = ' '.join(words)
                
                modified_sentences.append(sentence)
            
            return " ".join(modified_sentences)
        except Exception as e:
            logger.warning(f"Error in sentence variation: {e}")
            return text
    
    def add_subtle_imperfections(self, text: str) -> str:
        """Add very subtle natural imperfections (rarely noticeable)"""
        result = text
        words = result.split()
        num_imperfections = max(0, int(len(words) * self.variation_intensity * 0.01))  # ~1% of words
        
        if num_imperfections == 0:
            return result
        
        # Randomly duplicate or slightly alter words (very rarely)
        indices = random.sample(range(len(words)), min(num_imperfections, len(words)))
        
        for idx in sorted(indices, reverse=True):
            word = words[idx]
            variation_type = random.choice(['repeat', 'rephrase'])
            
            if variation_type == 'repeat' and random.random() < 0.3:
                # Very rarely repeat a word (like a natural speech pattern)
                words[idx] = f"{word} {word}" if len(word) > 4 else word
            elif variation_type == 'rephrase' and random.random() < 0.2:
                # Minor word swaps that are almost imperceptible
                if idx > 0 and random.random() < 0.1:
                    words[idx], words[idx - 1] = words[idx - 1], words[idx]
        
        return " ".join(words).replace(" . ", ".").replace(" , ", ",")
    
    def add_natural_punctuation_variations(self, text: str) -> str:
        """Add natural punctuation variations (ellipsis, dashes, etc.)"""
        result = text
        intensity_factor = int(len(result.split('.')) * self.variation_intensity * 0.1)
        
        # Randomly replace some periods with other punctuation
        sentences = result.split('.')
        modified = []
        
        for i, sentence in enumerate(sentences[:-1]):  # Don't modify last part
            if random.random() < self.variation_intensity * 0.15:
                # Sometimes use ellipsis or em dash
                variation = random.choice(['...', '—'])
                modified.append(sentence + variation)
            else:
                modified.append(sentence + '.')
        
        if sentences[-1]:
            modified.append(sentences[-1])
        
        return ''.join(modified)
    def add_intentional_mistakes(self, text: str, mistakes_intensity: float = 0.2) -> str:
        """Introduce light grammatical mistakes without changing sentence meaning.

        Mistakes are intentionally subtle: article omission, auxiliary drops,
        minor verb agreement errors, and occasional missing `to` in infinitives.
        The function avoids meaning-changing substitutions.
        """
        result = text
        sentences = sent_tokenize(result)
        modified = []

        for sentence in sentences:
            s = sentence
            if random.random() < mistakes_intensity * 0.9:
                # Omit some articles (a, an, the) occasionally
                if random.random() < 0.6:
                    s = re.sub(r'\b(the|a|an)\s+', lambda m: '' if random.random() < mistakes_intensity else m.group(0), s, flags=re.IGNORECASE)

                # Drop simple auxiliaries in casual speech (do/does/did/have/has)
                if random.random() < 0.4:
                    s = re.sub(r'\b(do|does|did|have|has|had)\b\s+', lambda m: '' if random.random() < (mistakes_intensity * 0.6) else m.group(0), s, flags=re.IGNORECASE)

                # Minor verb-s errors for 3rd person (remove or add 's')
                if random.random() < 0.2:
                    s = re.sub(r'\b(\w+?)(s)\b', lambda m: m.group(1) if random.random() < 0.3 * mistakes_intensity else m.group(0), s)

                # Occasionally drop 'to' in infinitives: 'to go' -> 'go'
                if random.random() < 0.25:
                    s = re.sub(r'\bto\s+(\w+)', lambda m: m.group(1) if random.random() < 0.35 * mistakes_intensity else m.group(0), s, flags=re.IGNORECASE)

            modified.append(s)

        result = ' '.join(modified)
        # Lightweight cleanup
        result = re.sub(r'\s+', ' ', result).strip()
        return result

    def apply_all_variations(self, text: str, add_mistakes: bool = False, mistakes_intensity: float = 0.2) -> str:
        """Apply all human variations to text

        Args:
            add_mistakes: whether to introduce intentional grammatical mistakes
            mistakes_intensity: 0.0 to 1.0, how many mistakes to add
        """
        logger.info("Applying human variations...")

        try:
            # Apply variations in order
            result = text
            result = self.add_informal_contractions(result)
            result = self.add_informal_vocabulary(result)
            result = self.add_sentence_length_variation(result)
            result = self.add_subtle_imperfections(result)
            result = self.add_natural_punctuation_variations(result)

            # Optionally add intentional grammatical mistakes
            if add_mistakes and mistakes_intensity > 0:
                result = self.add_intentional_mistakes(result, mistakes_intensity)

            # Clean up any double spaces
            result = re.sub(r'\s+', ' ', result).strip()

            logger.info("Human variations applied successfully")
            return result

        except Exception as e:
            logger.error(f"Error applying variations: {e}")
            return text

def humanize_with_natural_variations(
    text: str, 
    variation_intensity: float = 0.5,
    add_mistakes: bool = False,
    mistakes_intensity: float = 0.2
) -> Tuple[str, Optional[str]]:
    """
    Add natural human variations to already humanized text
    
    Args:
        text: The text to add variations to
        variation_intensity: How much variation to add (0.0 to 1.0)
    
    Returns:
        Tuple of (varied_text, error_message)
    """
    try:
        if not text or not text.strip():
            return "", "No text provided"
        
        engine = HumanVariationEngine(variation_intensity=variation_intensity)
        varied_text = engine.apply_all_variations(text, add_mistakes=add_mistakes, mistakes_intensity=mistakes_intensity)
        
        return varied_text, None
    
    except Exception as e:
        error_msg = f"Error adding variations: {str(e)}"
        logger.error(error_msg)
        return text, error_msg
