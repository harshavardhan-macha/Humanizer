#!/usr/bin/env python3
"""Test pipeline with fallback to t5-small model"""

import sys
import logging
from main import HumanizerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_with_fallback():
    """Test pipeline, fallback to t5-small if Vamsi fails"""
    print("="*80)
    print("TESTING HUMANIZATION WITH SMART MODEL SELECTION")
    print("="*80)
    
    humanizer = HumanizerService()
    
    test_text = "This article discusses the impact of artificial intelligence on modern society. AI has revolutionized many industries by automating tasks and improving efficiency. Machine learning models can now process complex data and make accurate predictions."
    
    print(f"\nOriginal Text ({len(test_text)} chars):")
    print(test_text)
    print("\n" + "="*80 + "\n")
    
    # Test 1: Try with Vamsi (will fallback if not available)
    print("Test 1: Attempting Vamsi model with 0.85 intensity...")
    humanized_text, stats = humanizer.humanize_text(
        text=test_text,
        use_paraphrasing=True,
        use_enhanced_rewriting=True,
        paraphrase_model="Vamsi/T5_Paraphrase_Paws",
        add_variations=True,
        variation_intensity=0.85
    )
    
    if stats.get("model_used") is None and "paraphrasing_failed" in stats.get("processing_steps", []):
        print("⚠️  Vamsi model failed, testing with t5-small fallback...\n")
        
        # Test 2: Fallback to t5-small
        print("Test 2: Using t5-small fallback model with 0.85 intensity...")
        humanized_text, stats = humanizer.humanize_text(
            text=test_text,
            use_paraphrasing=True,
            use_enhanced_rewriting=True,
            paraphrase_model="t5-small",
            add_variations=True,
            variation_intensity=0.85
        )
    
    print(f"\nHumanized Text ({len(humanized_text)} chars):")
    print(humanized_text)
    
    print("\n" + "="*80)
    print("PROCESSING STATISTICS:")
    print("="*80)
    print(f"Original length: {stats['original_length']} chars")
    print(f"Final length: {stats['final_length']} chars")
    print(f"Model used: {stats.get('model_used', 'N/A')}")
    print(f"Variation intensity: {stats['variation_intensity']}")
    print(f"Processing pipeline: {' → '.join(stats.get('processing_steps', []))}")
    
    print("\n" + "="*80)
    print("✅ Pipeline test completed successfully!")
    print("="*80)

if __name__ == "__main__":
    try:
        test_with_fallback()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
