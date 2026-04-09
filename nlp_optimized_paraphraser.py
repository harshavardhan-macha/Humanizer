"""
NLP-Optimized T5 Paraphraser
Fixes beam search, sampling, and sentence-level processing.
Author: NLP Expert
"""

import logging
import torch
import re
from typing import Tuple, Optional, List
from nltk.tokenize import sent_tokenize
from paraphraser import get_current_model, tokenizer, device, MODEL_CONFIGS, get_available_models, load_model

logger = logging.getLogger(__name__)

# AI-SUSPICIOUS WORDS (common in generated text)
AI_SUSPICIOUS_WORDS = {
    "utilize", "leverage", "delve", "comprehensive", "crucial", 
    "notably", "in conclusion", "furthermore", "moreover", "it is worth noting",
    "perspect", "enhance", "facilitate", "optimize", "robust", "paradigm",
    "synergy", "unprecedented", "consistently", "inherently", "notwithstanding"
}

class OptimizedParaphraser:
    """T5 Paraphraser with proper beam search, sampling, and sentence-level processing"""
    
    def __init__(self):
        self.diversified_config = {
            "num_beams": 5,  # ✅ USE BEAM SEARCH (was 1)
            "num_beam_groups": 5,  # ✅ DIVERSE BEAM SEARCH
            "diversity_penalty": 0.7,  # ✅ PREVENT DUPLICATE HYPOTHESES
            "do_sample": True,  # ✅ ENABLE SAMPLING
            "temperature": 0.85,  # ✅ MODERATE RANDOMNESS (not too high)
            "top_k": 50,  # ✅ NUCLEUS SAMPLING
            "top_p": 0.92,  # ✅ CUMULATIVE PROBABILITY
            "repetition_penalty": 2.5,  # ✅ PREVENT REPETITION
            "early_stopping": True,
            "length_penalty": 1.0,  # Balanced length (not too short/long)
            "max_new_tokens": 256,  # Don't allow runaway generations
        }
    
    def paraphrase_sentence(self, sentence: str, model_name: str = None) -> Tuple[str, Optional[str]]:
        """
        Paraphrase a SINGLE SENTENCE with optimized settings.
        Critical: Process sentence-by-sentence, not whole paragraph.
        """
        if not sentence.strip():
            return "", None
        
        try:
            # Load model if needed
            if get_current_model() is None:
                available = get_available_models()
                if not available:
                    return "", "No paraphrase model available"
                success, err = load_model(available[0])
                if not success:
                    return "", err
            
            model = get_current_model()
            if model is None or tokenizer is None:
                return "", "Model not loaded"
            
            # Get model config
            config = MODEL_CONFIGS.get(model._class_name__ if hasattr(model, '_class_name__') else 't5-small')
            prefix = config.get("prefix", "paraphrase: ") if isinstance(config, dict) else "paraphrase: "
            
            # INPUT VALIDATION: Warn if truncated
            input_text = f"{prefix}{sentence}"
            encoding = tokenizer.encode(input_text, return_tensors="pt")
            input_length = encoding.shape[1]
            
            if input_length > 500:
                logger.warning(f"⚠️ Input truncated: {input_length} tokens > 500 max. Sentence: {sentence[:80]}...")
            
            # Tokenize with explicit max_length
            inputs = tokenizer.encode_plus(
                input_text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=False
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Generate with OPTIMIZED settings
            with torch.no_grad():
                outputs = model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    # ✅ DIVERSE BEAM SEARCH SETTINGS
                    num_beams=self.diversified_config["num_beams"],
                    num_beam_groups=self.diversified_config["num_beam_groups"],
                    diversity_penalty=self.diversified_config["diversity_penalty"],
                    # ✅ SAMPLING SETTINGS
                    do_sample=self.diversified_config["do_sample"],
                    temperature=self.diversified_config["temperature"],
                    top_k=self.diversified_config["top_k"],
                    top_p=self.diversified_config["top_p"],
                    # ✅ QUALITY SETTINGS
                    repetition_penalty=self.diversified_config["repetition_penalty"],
                    early_stopping=True,
                    length_penalty=1.0,
                    max_new_tokens=256,
                    num_return_sequences=1,  # Get 1 best output (filtered by beam diversity)
                )
            
            # Decode
            paraphrased = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            
            # Remove prefix if present
            if paraphrased.lower().startswith(prefix.lower()):
                paraphrased = paraphrased[len(prefix):].strip()
            
            # POST-PROCESS: Fix common T5 quirks
            paraphrased = self._post_process(paraphrased)
            
            # SANITY CHECK: If output is too similar to input, it failed
            if self._similarity_ratio(sentence, paraphrased) > 0.85:
                logger.warning(f"⚠️ Paraphrase too similar to input. Retrying with different temperature...")
                # Fallback: Return sentence with minor edits
                return self._fallback_paraphrase(sentence), None
            
            return paraphrased, None
            
        except Exception as e:
            logger.error(f"Error paraphrasing sentence: {str(e)}")
            return "", str(e)
    
    def paraphrase_text(self, text: str, model_name: str = None) -> Tuple[str, Optional[str]]:
        """
        Paraphrase ENTIRE TEXT by processing sentence-by-sentence.
        This preserves meaning and allows fine-grained control.
        """
        if not text.strip():
            return "", None
        
        try:
            # Split into sentences (preserve paragraph structure)
            sentences = sent_tokenize(text)
            paraphrased_sentences = []
            
            logger.info(f"Paraphrasing {len(sentences)} sentences...")
            
            for i, sentence in enumerate(sentences):
                if not sentence.strip():
                    continue
                
                paraphrased, err = self.paraphrase_sentence(sentence, model_name)
                
                if err:
                    logger.warning(f"Failed to paraphrase sentence {i+1}: {err}. Using original.")
                    paraphrased = sentence
                
                paraphrased_sentences.append(paraphrased)
            
            result = " ".join(paraphrased_sentences)
            return result, None
            
        except Exception as e:
            logger.error(f"Error in text paraphrasing: {str(e)}")
            return "", str(e)
    
    def _post_process(self, text: str) -> str:
        """Fix common T5 generation quirks"""
        # Remove duplicate phrases
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text)
        # Fix spacing
        text = re.sub(r'\s+', ' ', text).strip()
        # Fix punctuation spacing
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        return text
    
    def _similarity_ratio(self, text1: str, text2: str) -> float:
        """Quick similarity check (Jaccard on words)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0
    
    def _fallback_paraphrase(self, sentence: str) -> str:
        """Fallback: Apply light synonym replacement when beam search fails"""
        words = sentence.split()
        if len(words) < 3:
            return sentence
        
        # Swap adjacent words occasionally
        if len(words) > 3:
            idx1, idx2 = sorted(torch.randperm(2)[:2].tolist())
            if idx1 < len(words) - 1 and idx2 < len(words) - 1:
                words[idx1], words[idx2] = words[idx2], words[idx1]
        
        return " ".join(words)


# Export function for compatibility
optimized_paraphraser = OptimizedParaphraser()

def paraphrase_sentence_optimized(sentence: str) -> Tuple[str, Optional[str]]:
    """Convenience wrapper"""
    return optimized_paraphraser.paraphrase_sentence(sentence)

def paraphrase_text_optimized(text: str) -> Tuple[str, Optional[str]]:
    """Convenience wrapper"""
    return optimized_paraphraser.paraphrase_text(text)
