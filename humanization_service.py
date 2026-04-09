"""
Flask Integration Layer for Optimized Humanization Pipeline
Bridges the optimized pipeline with your Flask backend.
Author: NLP Expert
"""

import logging
from typing import Dict, Tuple, Optional
from optimized_humanization_pipeline import humanize_text_optimized, humanize_and_score

logger = logging.getLogger(__name__)


class HumanizationService:
    """
    Service wrapper for optimized humanization.
    Integrates with Flask endpoints.
    """
    
    def __init__(self, enable_scoring: bool = True):
        self.enable_scoring = enable_scoring
        logger.info("✅ HumanizationService initialized with optimized pipeline")
    
    def humanize(self, 
                 text: str, 
                 intensity: float = 0.85,
                 paraphrase: bool = True,
                 synonyms: bool = True,
                 variations: bool = True,
                 return_scores: bool = False) -> Tuple[str, Dict]:
        """
        Humanize text using optimized pipeline.
        
        Args:
            text: Input text
            intensity: 0.0-1.0 intensity
            paraphrase: Enable paraphrasing
            synonyms: Enable synonym replacement
            variations: Enable natural variations
            return_scores: Include scoring in response
        
        Returns:
            (humanized_text, stats_dict)
        """
        if not text.strip():
            return "", {"error": "Empty text"}
        
        try:
            logger.info(f"Humanizing {len(text)} chars with intensity={intensity}")
            
            # Run optimized pipeline
            humanized, stats = humanize_text_optimized(text, intensity)
            
            # Add configuration info
            stats["config"] = {
                "paraphrase": paraphrase,
                "synonyms": synonyms,
                "variations": variations,
                "scoring_enabled": self.enable_scoring
            }
            
            # Optionally include detailed scoring
            if self.enable_scoring and return_scores:
                from humanization_scorer import compute_humanization_score
                original_score = compute_humanization_score(text)
                final_score = compute_humanization_score(humanized)
                
                stats["scoring"] = {
                    "original_score": original_score['overall_score'],
                    "final_score": final_score['overall_score'],
                    "improvement": final_score['overall_score'] - original_score['overall_score'],
                    "metrics": {
                        "original": original_score,
                        "final": final_score
                    }
                }
            
            logger.info(f"✅ Humanization complete: {len(humanized)} chars")
            return humanized, stats
        
        except Exception as e:
            logger.error(f"❌ Humanization failed: {str(e)}")
            return text, {"error": str(e)}


# Global service instance
humanization_service = HumanizationService(enable_scoring=True)


def get_humanization_service() -> HumanizationService:
    """Get the global humanization service"""
    return humanization_service
