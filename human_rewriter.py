"""
Aggressive Human-Style Rewriter
Completely rewrite text to sound naturally human by restructuring sentences,
changing vocabulary, and adding conversational elements
"""

import random
import re
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)

class HumanStyleRewriter:
    """Rewrites text to sound completely human"""
    
    def __init__(self, intensity: float = 0.85):
        self.intensity = max(0.0, min(1.0, intensity))
    
    def break_into_chunks(self, text: str) -> List[str]:
        """Break text into sentences"""
        # Split by periods, exclamation, question marks
        chunks = re.split(r'(?<=[.!?])\s+', text)
        return [c.strip() for c in chunks if c.strip()]
    
    def rewrite_sentence(self, sentence: str) -> str:
        """Completely rewrite a single sentence in human style"""
        # Remove extra punctuation
        sentence = sentence.rstrip('.!?')
        
        if not sentence:
            return ""
        
        # Use multiple transformation techniques together
        result = sentence
        
        # Always add conversational element
        result = self.add_conversational_start(result)
        
        # Randomly rearrange for additional change
        if random.random() < 0.5:
            result = self.use_casual_language(result)
        
        # Add emphasis words
        if random.random() < 0.6:
            result = self.emphasize_differently(result)
        
        # Randomly end with different punctuation
        if random.random() < 0.4:
            ending = random.choice(['!', '?', '...'])
            return result.rstrip('.!?') + ending
        
        return result + '.'
    
    def rearrange_structure(self, sentence: str) -> str:
        """Rearrange sentence structure completely"""
        words = sentence.split()
        if len(words) < 3:
            return sentence
        
        # Randomly shuffle and reconnect
        if random.random() < 0.5:
            # Put object/subject emphasis first
            return ' '.join(random.sample(words, len(words)))
        else:
            return sentence
    
    def add_conversational_start(self, sentence: str) -> str:
        """Add conversational opening with high probability"""
        starters = [
            "You know, ",
            "So basically, ",
            "Look, ",
            "Here's the thing: ",
            "Honestly, ",
            "Pretty much, ",
            "Truth is, ",
            "What I mean is, ",
            "Think about it - ",
            "Consider this: ",
            "I reckon ",
            "From what I see, ",
            "The fact is, ",
            "In my view, ",
            "Seems to me, ",
            "I'm telling you, ",
            "Get this - ",
            "Believe it or not, ",
        ]
        
        starter = random.choice(starters)
        first_char = sentence[0].lower() if sentence else ""
        rest = sentence[1:] if len(sentence) > 1 else ""
        
        return starter + first_char + rest
    
    def split_and_reconnect(self, sentence: str) -> str:
        """Split sentence and reconnect with casual connectors"""
        # Find comma positions or split at certain points
        parts = sentence.split(',')
        if len(parts) > 1:
            connectors = ['and', 'plus', 'also', 'so', 'then', 'but']
            return random.choice(connectors).capitalize() + ' ' + sentence
        return sentence
    
    def emphasize_differently(self, sentence: str) -> str:
        """Emphasize different parts of sentence"""
        words = sentence.split()
        if len(words) < 2:
            return sentence
        
        # Pick a random word and emphasize it
        idx = random.randint(0, len(words) - 1)
        emphasis_words = ['really', 'very', 'quite', 'so', 'totally', 'kinda', 'basically']
        words.insert(idx, random.choice(emphasis_words))
        return ' '.join(words)
    
    def add_personal_tone(self, sentence: str) -> str:
        """Add personal, subjective tone"""
        personal_opens = [
            "From what I see, ",
            "In my experience, ",
            "I believe ",
            "I reckon ",
            "Seems like ",
            "Appears to be that ",
            "If I'm honest, ",
            "Personally, ",
        ]
        return random.choice(personal_opens) + sentence[0].lower() + sentence[1:]
    
    def use_casual_language(self, sentence: str) -> str:
        """Replace formal words with casual ones - AGGRESSIVE"""
        casual_replacements = {
            r'\b(is|are|was|were)\b': 'is like',
            r'\b(significant|important|substantial)\b': 'huge',
            r'\b(facilitate|enable|allow)\b': 'let',
            r'\b(utilize|utilization)\b': 'use',
            r'\b(numerous|multiple|several)\b': 'tons of',
            r'\b(obtain|acquire|attain)\b': 'get',
            r'\b(commence|begin|start)\b': 'kick off',
            r'\b(terminate|end|conclude)\b': 'wrap up',
            r'\b(significantly)\b': 'hugely',
            r'\b(regarding|concerning|about)\b': 'on',
            r'\b(despite|although|though)\b': 'even though',
            r'\b(consequently|therefore|thus)\b': 'so',
            r'\b(furthermore|moreover)\b': 'plus',
            r'\b(however|nevertheless)\b': 'but',
        }
        
        result = sentence
        replacements_made = []
        for pattern, replacement in casual_replacements.items():
            if random.random() < 0.75:  # 75% chance to make each replacement
                matches = list(re.finditer(pattern, result, re.IGNORECASE))
                if matches:
                    # Replace the first match we find
                    match = matches[0]
                    result = result[:match.start()] + replacement + result[match.end():]
                    replacements_made.append(True)
                    break  # Only do one major replacement per sentence
        
        return result
    
    def apply_human_rewrite(self, text: str) -> str:
        """Rewrite entire text in human style - more aggressive"""
        logger.info(f"Human-style rewriting with intensity: {self.intensity}")
        
        try:
            chunks = self.break_into_chunks(text)
            rewritten_chunks = []
            
            for sentence in chunks:
                if not sentence.strip():
                    continue
                
                # More aggressive: always rewrite with high probability
                rewrite_probability = min(1.0, 0.6 + self.intensity * 0.4)  # 0.6 to 1.0 range
                
                if random.random() < rewrite_probability:
                    rewritten = self.rewrite_sentence(sentence)
                    rewritten_chunks.append(rewritten)
                else:
                    # Apply at least some basic transformation
                    rewritten_chunks.append(self.add_conversational_start(sentence) + ".")
            
            result = ' '.join(rewritten_chunks)
            
            # Aggressive cleanup - don't be too strict
            result = re.sub(r'\.\.+', '.', result)  # Double periods to single
            result = re.sub(r'\s+([.,!?])', r'\1', result)
            result = re.sub(r'\s+', ' ', result).strip()
            
            logger.info("Human-style rewriting completed")
            return result
        
        except Exception as e:
            logger.error(f"Error in human-style rewriting: {e}")
            return text

def apply_human_style_rewrite(text: str, intensity: float = 0.85) -> Tuple[str, Optional[str]]:
    """Apply aggressive human-style rewriting"""
    try:
        if not text or not text.strip():
            return "", "No text provided"
        
        rewriter = HumanStyleRewriter(intensity=intensity)
        result = rewriter.apply_human_rewrite(text)
        
        return result, None
    
    except Exception as e:
        error_msg = f"Error in human-style rewriting: {str(e)}"
        logger.error(error_msg)
        return text, error_msg
