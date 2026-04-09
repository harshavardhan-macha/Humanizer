"""
Aggressive Text Rewriting Module
Rewrites text to sound more naturally human by:
- Changing passive to active voice and vice versa
- Rearranging sentence structure
- Splitting long sentences into shorter ones
- Merging short sentences
- Adding subjective language
- Varying word order
- Using more casual transitions
"""

import random
import re
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)

class AggressiveRewriter:
    """Aggressive text rewriting to simulate human writing patterns"""
    
    def __init__(self, intensity: float = 0.8):
        """
        Initialize aggressive rewriter
        
        Args:
            intensity: 0.0 to 1.0 - how much rewriting to apply
        """
        self.intensity = max(0.0, min(1.0, intensity))
        
    def split_long_sentences(self, text: str) -> str:
        """Split long sentences into shorter, more natural chunks"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        rewritten = []
        
        for sentence in sentences:
            # If sentence is very long and has commas, split it
            if len(sentence) > 100 and ',' in sentence:
                if random.random() < self.intensity * 0.3:
                    parts = sentence.split(',')
                    if len(parts) > 1:
                        # Randomly reconnect some parts or keep split
                        if random.random() < 0.5:
                            rewritten.append('. '.join([p.strip() for p in parts]))
                        else:
                            rewritten.extend([p.strip() + '.' for p in parts if p.strip()])
                    else:
                        rewritten.append(sentence)
                else:
                    rewritten.append(sentence)
            else:
                rewritten.append(sentence)
        
        return ' '.join([s for s in rewritten if s])
    
    def merge_short_sentences(self, text: str) -> str:
        """Merge consecutive very short sentences"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if len(sentences) < 2:
            return text
        
        merged = []
        i = 0
        while i < len(sentences):
            current = sentences[i]
            
            # If current sentence is short and next exists, maybe merge
            if i < len(sentences) - 1 and len(current.split()) < 8:
                if random.random() < self.intensity * 0.2:
                    # Use different connectors
                    connector = random.choice(['. ', ', ', '. However, ', '. But ', '; '])
                    current = current.rstrip('.!?') + connector + sentences[i + 1].lstrip()
                    i += 2
                else:
                    merged.append(current)
                    i += 1
            else:
                merged.append(current)
                i += 1
        
        return ' '.join(merged)
    
    def reorder_phrases(self, text: str) -> str:
        """Reorder phrases within sentences for variety"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        rewritten = []
        
        for sentence in sentences:
            if random.random() < self.intensity * 0.15:
                # Find independent clauses
                parts = re.split(r',|;', sentence)
                
                if len(parts) > 1:
                    # Randomly shuffle some parts
                    if random.random() < 0.5:
                        shuffled = parts.copy()
                        random.shuffle(shuffled)
                        sentence = ', '.join([p.strip() for p in shuffled if p.strip()])
                        sentence = sentence.rstrip(',').rstrip(';')
            
            rewritten.append(sentence)
        
        return '. '.join([s.strip() for s in rewritten if s.strip()])
    
    def add_subjective_language(self, text: str) -> str:
        """Add subjective observations and opinions"""
        subjective_phrases = [
            "It seems that ",
            "Apparently, ",
            "I'd say ",
            "One might argue that ",
            "In my view, ",
            "Notably, ",
            "Interestingly, ",
            "The thing is, ",
            "To my mind, ",
            "It appears ",
        ]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        rewritten = []
        
        for sentence in sentences:
            if random.random() < self.intensity * 0.1 and not any(sentence.startswith(p) for p in subjective_phrases):
                sentence = random.choice(subjective_phrases) + sentence[0].lower() + sentence[1:]
            
            rewritten.append(sentence)
        
        return ' '.join(rewritten)
    
    def vary_conjunction_usage(self, text: str) -> str:
        """Replace and vary conjunctions and transitions more aggressively"""
        result = text
        
        # More aggressive replacements with higher probability
        replacements = {
            r'\bAlso[\s,]': [', Furthermore, ', ', Moreover, ', ', In addition, ', ', What\'s more, '],
            r'\bBut[\s,]': [', Yet, ', ', Though, ', ', Still, ', ', On the other hand, '],
            r'\bHowever[\s,]': [', Yet, ', ', Though, ', ', Still, ', ', Conversely, '],
            r'\bTherefore[\s,]': [', So, ', ', Thus, ', ', Consequently, ', ', As a result, '],
            r'\bFurthermore[\s,]': [', Moreover, ', ', Additionally, ', ', In addition, ', ', What\'s more, '],
            r'\bMoreover[\s,]': [', Furthermore, ', ', Additionally, ', ', Plus, ', ', In addition to that, '],
            r'\bAnd\s': [' Plus, ', ' So, ', ' Likewise, ', ' What\'s more, '],
        }
        
        for pattern, replacement_list in replacements.items():
            if random.random() < self.intensity * 0.5:
                matches = list(re.finditer(pattern, result, re.IGNORECASE))
                for match in matches:
                    if random.random() < 0.7:  # 70% chance to replace each match
                        replacement = random.choice(replacement_list)
                        result = result[:match.start()] + replacement + result[match.end():]
        
        return result
    
    def add_emphasis_variety(self, text: str) -> str:
        """Add varied emphasis and intensity words"""
        emphasis_add = {
            r'\bvery\s': [' really ', ' quite ', ' rather ', ' fairly ', ' pretty '],
            r'\bimportant': ['crucial', 'significant', 'vital', 'essential', 'key'],
            r'\breally': ['truly', 'actually', 'genuinely', 'certainly'],
        }
        
        result = text
        for pattern, replacements in emphasis_add.items():
            if random.random() < self.intensity * 0.15:
                matches = list(re.finditer(pattern, result, re.IGNORECASE))
                if matches:
                    match = random.choice(matches)
                    replacement = random.choice(replacements)
                    result = result[:match.start()] + replacement + result[match.end():]
        
        return result
    
    def randomize_word_order(self, text: str) -> str:
        """Slightly randomize word order for natural variation"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        rewritten = []
        
        for sentence in sentences:
            if random.random() < self.intensity * 0.1:
                words = sentence.split()
                if len(words) > 4:
                    # Swap two random adjacent words occasionally
                    idx = random.randint(0, len(words) - 2)
                    words[idx], words[idx + 1] = words[idx + 1], words[idx]
                sentence = ' '.join(words)
            
            rewritten.append(sentence)
        
        return '. '.join([s.strip() for s in rewritten if s.strip()])
    
    def apply_all_rewrites(self, text: str) -> str:
        """Apply all rewriting techniques in sequence"""
        logger.info(f"Applying aggressive rewriting with intensity: {self.intensity}")
        
        try:
            result = text
            result = self.split_long_sentences(result)
            result = self.merge_short_sentences(result)
            result = self.vary_conjunction_usage(result)
            result = self.add_subjective_language(result)
            result = self.add_emphasis_variety(result)
            result = self.reorder_phrases(result)
            result = self.randomize_word_order(result)
            
            # Clean up
            result = re.sub(r'\s+', ' ', result).strip()
            result = re.sub(r'([.!?])\s+([.!?])', r'\1', result)
            
            logger.info("Aggressive rewriting completed")
            return result
        
        except Exception as e:
            logger.error(f"Error in aggressive rewriting: {e}")
            return text

def apply_aggressive_rewriting(text: str, intensity: float = 0.8) -> Tuple[str, Optional[str]]:
    """
    Apply aggressive rewriting to make text more naturally human
    
    Args:
        text: Text to rewrite
        intensity: How aggressive (0.0 to 1.0)
    
    Returns:
        Tuple of (rewritten_text, error_message)
    """
    try:
        if not text or not text.strip():
            return "", "No text provided"
        
        rewriter = AggressiveRewriter(intensity=intensity)
        result = rewriter.apply_all_rewrites(text)
        
        return result, None
    
    except Exception as e:
        error_msg = f"Error applying aggressive rewriting: {str(e)}"
        logger.error(error_msg)
        return text, error_msg
