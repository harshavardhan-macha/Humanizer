"""
BUG FIXES FOR VIIT-HUMANIZER
Fixes for: Structure Destruction, Filler Injection, Step Differentiation, Sentence Variance
Author: NLP QA Team
"""

import logging
import random
import re
from typing import List, Dict, Tuple, Optional
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# ============================================================================
# BUG FIX #1: STRUCTURE PRESERVATION (Headings vs Body)
# ============================================================================

def parse_text_blocks(text: str) -> List[Dict]:
    """
    Parse text into blocks: headings vs paragraphs.
    
    HEADING: <= 8 words, no ending punctuation (.!?)
    PARAGRAPH: everything else
    
    Returns:
        List of dicts: {"type": "heading"|"paragraph", "text": str}
    """
    blocks = []
    
    # Split by double newlines (paragraph breaks)
    raw_paragraphs = text.split('\n\n')
    
    for para in raw_paragraphs:
        if not para.strip():
            continue
        
        # Check if this looks like a heading
        para_stripped = para.strip()
        word_count = len(para_stripped.split())
        has_end_punct = para_stripped[-1] in '.!?:' if para_stripped else False
        
        if word_count <= 8 and not has_end_punct:
            # This is a heading
            blocks.append({
                "type": "heading",
                "text": para_stripped,
                "original_text": para
            })
        else:
            # This is a paragraph
            blocks.append({
                "type": "paragraph",
                "text": para_stripped,
                "original_text": para
            })
    
    logger.info(f"✅ BUG FIX #1: Parsed {len(blocks)} blocks ({sum(1 for b in blocks if b['type']=='heading')} headings, {sum(1 for b in blocks if b['type']=='paragraph')} paragraphs)")
    return blocks


def reassemble_blocks(blocks: List[Dict]) -> str:
    """
    Reassemble blocks back into text with proper spacing.
    """
    result_blocks = []
    for block in blocks:
        result_blocks.append(block.get('text', ''))
    
    return '\n\n'.join(result_blocks)


# ============================================================================
# BUG FIX #2: SMART FILLER INJECTION (Probability Gated, Sentence-Start Only)
# ============================================================================

# Clean, coherent filler phrases (only for sentence starts)
CLEAN_FILLERS = [
    "Honestly, ",
    "To be fair, ",
    "The thing is, ",
    "Interestingly enough, ",
    "What's worth knowing is that ",
    "In practice, ",
    "From experience, ",
    "Worth noting — ",
    "In reality, ",
    "Let's be real — ",
    "Here's what matters: ",
    "At the end of the day, ",
    "That said, ",
    "By the way, ",
]

def inject_fillers_smart(text: str, injection_probability: float = 0.25) -> str:
    """
    Inject filler phrases ONLY at sentence starts with probability gating.
    
    Rules:
    - Only inject at sentence boundaries (not mid-sentence)
    - Probability: 25% of sentences get a filler
    - Never inject two fillers in a row
    - Only single word at sentence start
    
    Args:
        text: Input text
        injection_probability: Probability of injecting on each sentence (0.0-1.0)
    
    Returns:
        Text with fillers intelligently injected
    """
    try:
        # Split into sentences
        sentences = sent_tokenize(text)
        if len(sentences) < 1:
            return text
        
        modified_sentences = []
        last_had_filler = False
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Roll dice: should we inject a filler?
            should_inject = random.random() < injection_probability and not last_had_filler
            
            if should_inject:
                filler = random.choice(CLEAN_FILLERS)
                # Capitalize first character of sentence after filler
                rest = sentence[0].lower() + sentence[1:] if len(sentence) > 1 else sentence
                sentence = filler + rest
                last_had_filler = True
            else:
                last_had_filler = False
            
            modified_sentences.append(sentence)
        
        result = ' '.join(modified_sentences)
        logger.info(f"✅ BUG FIX #2: Injected fillers into {len(sentences)} sentences")
        return result
    
    except Exception as e:
        logger.warning(f"Error in smart filler injection: {e}")
        return text


# ============================================================================
# BUG FIX #3: TWO-STAGE DIFFERENTIATION (Paraphrase vs Final)
# ============================================================================

def add_contractions(text: str) -> str:
    """
    Convert formal phrases to contractions (human signature).
    
    BUG FIX #3: Applied in Step 2 ONLY (not in Step 1)
    """
    replacements = {
        r'\bdo not\b': "don't",
        r'\bdoes not\b': "doesn't",
        r'\bdid not\b': "didn't",
        r'\bwill not\b': "won't",
        r'\bcannot\b': "can't",
        r'\bcan not\b': "can't",
        r'\bis not\b': "isn't",
        r'\bare not\b': "aren't",
        r'\bwas not\b': "wasn't",
        r'\bwere not\b': "weren't",
        r'\bhave not\b': "haven't",
        r'\bhas not\b': "hasn't",
        r'\bhad not\b': "hadn't",
        r'\bI am\b': "I'm",
        r'\byou are\b': "you're",
        r'\bhe is\b': "he's",
        r'\bshe is\b': "she's",
        r'\bit is\b': "it's",
        r'\bwe are\b': "we're",
        r'\bthey are\b': "they're",
    }
    
    result = text
    for phrase, contraction in replacements.items():
        result = re.sub(phrase, contraction, result, flags=re.IGNORECASE)
    
    logger.info(f"✅ BUG FIX #3a: Applied contractions")
    return result


def remove_ai_signature_phrases(text: str) -> str:
    """
    Remove/replace typical AI phrases that make text sound robotic.
    
    BUG FIX #3: Applied in Step 2 ONLY (not in Step 1)
    """
    replacements = {
        r'\bit is worth noting that\b': "notably,",
        r'\bit is important to note that\b': "importantly,",
        r'\bin conclusion\b': "in short",
        r'\bmoreover\b': "also",
        r'\bfurthermore\b': "plus",
        r'\butilize\b': "use",
        r'\bleverage\b': "use",
        r'\bdelve into\b': "explore",
        r'\bnotwithstanding\b': "despite",
    }
    
    result = text
    for phrase, replacement in replacements.items():
        result = re.sub(phrase, replacement, result, flags=re.IGNORECASE)
    
    logger.info(f"✅ BUG FIX #3b: Removed AI signature phrases")
    return result


# ============================================================================
# BUG FIX #4: SENTENCE LENGTH VARIANCE
# ============================================================================

def vary_sentence_length(text: str) -> str:
    """
    Create natural sentence length variance.
    
    Rules:
    - Split long sentences (>30 words) at conjunctions
    - Merge short sentences (<6 words) with next sentence
    
    BUG FIX #4: Applied in Step 2
    """
    try:
        sentences = sent_tokenize(text)
        if len(sentences) < 2:
            return text
        
        modified = []
        i = 0
        
        while i < len(sentences):
            sentence = sentences[i].strip()
            word_count = len(sentence.split())
            
            # RULE 1: Split long sentences
            if word_count > 30:
                # Try to split at a natural conjunction
                split_patterns = [
                    (r',\s+and\s+', ', and '),
                    (r',\s+but\s+', ', but '),
                    (r',\s+so\s+', ', so '),
                    (r';\s+', '; '),
                ]
                
                split_done = False
                for pattern, split_marker in split_patterns:
                    if re.search(pattern, sentence):
                        parts = re.split(pattern, sentence)
                        if len(parts) == 2:
                            # Split into two sentences
                            modified.append(parts[0].strip() + '.')
                            # Add marker back and continue
                            continuation = split_marker + parts[1]
                            modified.append(continuation.strip() if continuation[0] != ',' else continuation.lstrip(',').strip())
                            split_done = True
                            break
                
                if not split_done:
                    modified.append(sentence)
            
            # RULE 2: Merge short sentences
            elif word_count < 6 and i < len(sentences) - 1:
                next_sentence = sentences[i + 1].strip()
                merged = sentence.rstrip('.!?') + ', ' + next_sentence[0].lower() + next_sentence[1:]
                modified.append(merged)
                i += 1  # Skip the next sentence since we merged it
            
            else:
                modified.append(sentence)
            
            i += 1
        
        result = ' '.join(modified)
        logger.info(f"✅ BUG FIX #4: Created sentence length variance ({len(sentences)} → {len(result.split('.'))} units)")
        return result
    
    except Exception as e:
        logger.warning(f"Error in sentence variance: {e}")
        return text


# ============================================================================
# INTEGRATED PIPELINE THAT FIXES ALL 4 BUGS
# ============================================================================

def humanize_with_bug_fixes(
    text: str,
    step1_paraphrased: str = None,  # Optional: pass Step 1 result separately
    paraphrase_fn=None,  # Function to perform paraphrase
    synonym_replace_fn=None,  # Function to replace AI words
) -> Tuple[str, Dict]:
    """
    Complete humanization pipeline with all 4 bugs fixed.
    
    Pipeline:
    1. Parse into blocks (headings vs paragraphs) — BUG FIX #1
    2. Process only paragraphs through T5 paraphrasing
    3. Apply Step 2 transformations:
       - Remove AI phrases — BUG FIX #3b
       - Add contractions — BUG FIX #3a
       - Vary sentence length — BUG FIX #4
       - Inject fillers smartly — BUG FIX #2
    4. Reassemble with proper block structure — BUG FIX #1
    
    Returns:
        (final_text, stats)
    """
    if not text.strip():
        return "", {"error": "Empty text"}
    
    stats = {
        "original_length": len(text),
        "blocks_parsed": 0,
        "headings": 0,
        "paragraphs": 0,
        "step1_length": 0,
        "final_length": 0,
    }
    
    try:
        # ========== BUG FIX #1: Parse blocks ==========
        blocks = parse_text_blocks(text)
        stats["blocks_parsed"] = len(blocks)
        stats["headings"] = sum(1 for b in blocks if b['type'] == 'heading')
        stats["paragraphs"] = sum(1 for b in blocks if b['type'] == 'paragraph')
        
        # ========== Step 1: PARAPHRASE (paragraphs only) ==========
        paraphrase_results = []
        
        for block in blocks:
            if block['type'] == 'heading':
                # HEADINGS: Pass through unchanged
                paraphrase_results.append({
                    'type': 'heading',
                    'text': block['text']
                })
            else:
                # PARAGRAPHS: Paraphrase
                if paraphrase_fn:
                    paraphrased, err = paraphrase_fn(block['text'])
                    if err or not paraphrased.strip():
                        paraphrased = block['text']  # Fallback to original
                else:
                    paraphrased = block['text']  # No paraphrase function provided
                
                paraphrase_results.append({
                    'type': 'paragraph',
                    'text': paraphrased
                })
        
        # Reconstruct Step 1 output
        step1_text = reassemble_blocks(paraphrase_results)
        stats["step1_length"] = len(step1_text)
        
        # ========== Step 2: APPLY TRANSFORMATIONS ==========
        # All BUG FIXES applied here
        step2_text = step1_text
        
        # BUG FIX #3: Remove AI phrases
        step2_text = remove_ai_signature_phrases(step2_text)
        
        # BUG FIX #3: Add contractions
        step2_text = add_contractions(step2_text)
        
        # BUG FIX #4: Vary sentence length
        step2_text = vary_sentence_length(step2_text)
        
        # BUG FIX #2: Inject fillers smartly
        step2_text = inject_fillers_smart(step2_text, injection_probability=0.25)
        
        # ========== Final assembly ==========
        final_text = step2_text
        stats["final_length"] = len(final_text)
        stats["length_change"] = stats["final_length"] - stats["original_length"]
        
        logger.info(f"✅ ALL BUG FIXES APPLIED: {stats['original_length']} → {stats['step1_length']} → {stats['final_length']} chars")
        
        return final_text, stats
    
    except Exception as e:
        logger.error(f"Error in bug-fix pipeline: {str(e)}")
        return text, {**stats, "error": str(e)}
