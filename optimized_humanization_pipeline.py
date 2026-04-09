"""
Optimized Humanization Pipeline
Orchestrates the full humanization process with:
- Sentence-by-sentence T5 paraphrasing (with diverse beam search)
- Smart synonym replacement (POS-aware, AI-word detection)
- Intelligent dataset injection (probability-gated)
- Humanization scoring
- Retry loop if score is too low
Author: NLP Expert
"""

import logging
import random
from typing import Tuple, Dict, Optional
from nltk.tokenize import sent_tokenize

from nlp_optimized_paraphraser import paraphrase_text_optimized, OptimizedParaphraser
from smart_synonym_replacer import replace_ai_words
from humanization_scorer import compute_humanization_score, print_score_report
from human_variations import humanize_with_natural_variations

logger = logging.getLogger(__name__)

class OptimizedHumanizationPipeline:
    """
    End-to-end humanization pipeline with quality control.
    
    Pipeline stages:
    1. PARAPHRASE (sentence-by-sentence) - diverse beam search
    2. SYNONYM REPLACE - smart, POS-aware replacement of AI words
    3. NATURAL VARIATIONS - probability-gated dataset injection
    4. SCORE - measure humanization quality
    5. RETRY (optional) - if score < threshold, retry pipeline
    """
    
    def __init__(self, 
                 paraphrase_enabled: bool = True,
                 synonym_replacement_enabled: bool = True,
                 variations_enabled: bool = True,
                 scoring_enabled: bool = True,
                 retry_enabled: bool = True,
                 score_threshold: float = 60.0,
                 max_retries: int = 2):
        """
        Initialize the pipeline.
        
        Args:
            paraphrase_enabled: Enable T5 paraphrasing
            synonym_replacement_enabled: Enable smart synonym replacement
            variations_enabled: Enable natural variations injection
            scoring_enabled: Enable quality scoring
            retry_enabled: Enable retry if score is low
            score_threshold: Target humanization score (0-100)
            max_retries: Maximum retry attempts
        """
        self.paraphrase_enabled = paraphrase_enabled
        self.synonym_replacement_enabled = synonym_replacement_enabled
        self.variations_enabled = variations_enabled
        self.scoring_enabled = scoring_enabled
        self.retry_enabled = retry_enabled
        self.score_threshold = score_threshold
        self.max_retries = max_retries
        
        self.paraphraser = OptimizedParaphraser()
        
        logger.info("✅ Optimized Humanization Pipeline Initialized")
        logger.info(f"   Paraphrasing: {paraphrase_enabled}")
        logger.info(f"   Synonym Replacement: {synonym_replacement_enabled}")
        logger.info(f"   Variations: {variations_enabled}")
        logger.info(f"   Scoring & Retry: {scoring_enabled and retry_enabled}")
    
    def humanize(self, text: str, intensity: float = 0.85) -> Tuple[str, Dict]:
        """
        Run full humanization pipeline.
        
        Args:
            text: Input text to humanize
            intensity: Humanization intensity (0.0-1.0)
        
        Returns:
            (humanized_text, pipeline_stats)
        """
        if not text.strip():
            return "", {"error": "Empty text"}
        
        original_text = text
        stats = {
            "original_length": len(text),
            "stages_applied": [],
            "retries": 0,
            "final_score": 0,
            "score_improved": False
        }
        
        try:
            # STAGE 1: PARAPHRASE
            if self.paraphrase_enabled:
                logger.info("📝 Stage 1: Paraphrasing (sentence-by-sentence with diverse beam search)...")
                text, error = self.paraphraser.paraphrase_text(text)
                if error:
                    logger.warning(f"   ⚠️ Paraphrasing failed: {error}")
                else:
                    stats["stages_applied"].append("paraphrase")
                    logger.info(f"   ✓ Paraphrased: {len(original_text)} → {len(text)} chars")
            
            # STAGE 2: SMART SYNONYM REPLACEMENT
            if self.synonym_replacement_enabled:
                logger.info("🔄 Stage 2: Smart Synonym Replacement (POS-aware, AI-word detection)...")
                text, replacement_stats = replace_ai_words(text)
                stats["synonym_stats"] = replacement_stats
                stats["stages_applied"].append("synonym_replacement")
                logger.info(f"   ✓ Replaced {replacement_stats['replacements']} words")
            
            # STAGE 3: NATURAL VARIATIONS (WITH PROBABILITY GATING)
            if self.variations_enabled:
                logger.info("✨ Stage 3: Natural Variations (probability-gated, max 30% of sentences)...")
                # Apply variations with intensity cap (~30% injection rate)
                variation_intensity = min(0.5, intensity * 0.6)  # Cap to prevent over-humanization
                text, var_error = humanize_with_natural_variations(
                    text,
                    variation_intensity=variation_intensity,
                    add_mistakes=False  # Don't add mistakes by default
                )
                if var_error:
                    logger.warning(f"   ⚠️ Variations failed: {var_error}")
                else:
                    stats["stages_applied"].append("variations")
                    logger.info(f"   ✓ Applied natural variations")
            
            # STAGE 4: SCORE & RETRY
            if self.scoring_enabled:
                logger.info("📊 Stage 4: Quality Scoring...")
                
                # Initial score
                initial_score = compute_humanization_score(text)
                stats["initial_score"] = initial_score['overall_score']
                logger.info(f"   ✓ Humanization Score: {initial_score['overall_score']:.1f}/100")
                
                # Show detailed metrics
                logger.info(f"     - Sentence Variance: {initial_score['sentence_variance']:.2f}")
                logger.info(f"     - AI Phrases Penalty: {initial_score['ai_phrase_penalty']:.1f}")
                logger.info(f"     - Lexical Diversity: {initial_score['lexical_diversity']:.2f}")
                logger.info(f"     - Contractions: {initial_score['contraction_score']:.1f}")
                logger.info(f"     - Human Signatures: {initial_score['human_signature_score']:.1f}")
                
                # RETRY LOOP if score is below threshold
                if (self.retry_enabled and 
                    initial_score['overall_score'] < self.score_threshold and 
                    stats["retries"] < self.max_retries):
                    
                    logger.info(f"\n⚠️  Score {initial_score['overall_score']:.1f} < threshold {self.score_threshold}")
                    logger.info(f"   🔄 Retrying humanization (attempt {stats['retries'] + 1}/{self.max_retries})...")
                    
                    # Re-run pipeline on original text with adjusted intensity
                    text, retry_stats = self.humanize(
                        original_text,
                        intensity=intensity + 0.1  # Increase intensity
                    )
                    stats["retries"] += 1
                    stats.update(retry_stats)
                else:
                    stats["final_score"] = initial_score['overall_score']
                    
                    # Calculate improvement over original
                    original_score = compute_humanization_score(original_text)
                    stats["score_improved"] = initial_score['overall_score'] > original_score['overall_score']
            
            stats["final_length"] = len(text)
            stats["length_change"] = stats["final_length"] - stats["original_length"]
            
            logger.info(f"\n✅ Pipeline Complete")
            logger.info(f"   Original: {stats['original_length']} chars")
            logger.info(f"   Final: {stats['final_length']} chars")
            logger.info(f"   Stages Applied: {', '.join(stats['stages_applied'])}")
            
            return text, stats
        
        except Exception as e:
            logger.error(f"❌ Pipeline error: {str(e)}")
            return text, {**stats, "error": str(e)}


# Global instance
pipeline = OptimizedHumanizationPipeline(
    paraphrase_enabled=True,
    synonym_replacement_enabled=True,
    variations_enabled=True,
    scoring_enabled=True,
    retry_enabled=True,
    score_threshold=65.0,  # Aim for score >= 65
    max_retries=2
)


def humanize_text_optimized(text: str, intensity: float = 0.85) -> Tuple[str, Dict]:
    """
    Convenience wrapper for optimized humanization.
    
    Args:
        text: Text to humanize
        intensity: 0.0-1.0 intensity
    
    Returns:
        (humanized_text, stats)
    """
    return pipeline.humanize(text, intensity)


def humanize_and_score(text: str) -> Dict:
    """
    Humanize text and return full score report before/after.
    """
    logger.info("\n" + "="*70)
    logger.info("RUNNING OPTIMIZED HUMANIZATION PIPELINE")
    logger.info("="*70 + "\n")
    
    humanized, stats = pipeline.humanize(text)
    
    # Print detailed score report
    before_score, after_score = print_score_report(text, humanized)
    
    stats["detailed_scores"] = {
        "before": before_score,
        "after": after_score
    }
    
    return {
        "original_text": text,
        "humanized_text": humanized,
        "stats": stats,
        "scores": {
            "before": before_score,
            "after": after_score
        }
    }
