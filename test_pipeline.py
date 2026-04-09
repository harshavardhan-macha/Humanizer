#!/usr/bin/env python3
"""Test the complete humanization pipeline with all enhancements"""

import sys
import logging
from main import HumanizerService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pipeline():
    """Test the complete pipeline"""
    print("="*80)
    print("TESTING COMPLETE HUMANIZATION PIPELINE")
    print("="*80)
    
    # Initialize service
    humanizer = HumanizerService()
    
    # Test text
    test_text = "This article discusses the impact of artificial intelligence on modern society. AI has revolutionized many industries by automating tasks and improving efficiency. Machine learning models can now process complex data and make accurate predictions."
    
    print(f"\nOriginal Text ({len(test_text)} chars):")
    print(test_text)
    print("\n" + "="*80 + "\n")
    
    # Test with high variation intensity and all enhancements
    print("Testing with HIGH INTENSITY (0.85) configuration:")
    print("- Default model: Vamsi/T5_Paraphrase_Paws (high quality)")
    print("- Paraphrasing: enabled")
    print("- Rewriting: enabled")
    print("- Aggressive rewriting: enabled")
    print("- Human variations: enabled (0.85 intensity)")
    print("\n")
    
    humanized_text, stats = humanizer.humanize_text(
        text=test_text,
        use_paraphrasing=True,
        use_enhanced_rewriting=True,
        paraphrase_model="Vamsi/T5_Paraphrase_Paws",
        add_variations=True,
        variation_intensity=0.85
    )
    
    print(f"Humanized Text ({len(humanized_text)} chars):")
    print(humanized_text)
    
    print("\n" + "="*80)
    print("PROCESSING STATISTICS:")
    print("="*80)
    for key, value in stats.items():
        if key == "processing_steps":
            print(f"{key}: {' -> '.join(value)}")
        elif key != "error":
            print(f"{key}: {value}")
    
    if "error" in stats:
        print(f"\nError: {stats['error']}")
    
    print("\n" + "="*80)
    print("Pipeline test completed successfully!")
    print("="*80)

if __name__ == "__main__":
    try:
        test_pipeline()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
