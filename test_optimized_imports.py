"""
Test: Validate all imports and basic functionality
Run: python test_optimized_imports.py
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test all new modules can be imported"""
    tests = []
    
    # Test 1: Import paraphraser
    try:
        from nlp_optimized_paraphraser import OptimizedParaphraser, paraphrase_sentence_optimized
        logger.info("✅ nlp_optimized_paraphraser imported successfully")
        tests.append(("paraphraser", True, None))
    except Exception as e:
        logger.error(f"❌ nlp_optimized_paraphraser import failed: {str(e)}")
        tests.append(("paraphraser", False, str(e)))
    
    # Test 2: Import synonym replacer
    try:
        from smart_synonym_replacer import SmartSynonymReplacer, replace_ai_words
        logger.info("✅ smart_synonym_replacer imported successfully")
        tests.append(("synonym_replacer", True, None))
    except Exception as e:
        logger.error(f"❌ smart_synonym_replacer import failed: {str(e)}")
        tests.append(("synonym_replacer", False, str(e)))
    
    # Test 3: Import scorer
    try:
        from humanization_scorer import HumanizationScorer, compute_humanization_score
        logger.info("✅ humanization_scorer imported successfully")
        tests.append(("scorer", True, None))
    except Exception as e:
        logger.error(f"❌ humanization_scorer import failed: {str(e)}")
        tests.append(("scorer", False, str(e)))
    
    # Test 4: Import pipeline
    try:
        from optimized_humanization_pipeline import OptimizedHumanizationPipeline, humanize_text_optimized
        logger.info("✅ optimized_humanization_pipeline imported successfully")
        tests.append(("pipeline", True, None))
    except Exception as e:
        logger.error(f"❌ optimized_humanization_pipeline import failed: {str(e)}")
        tests.append(("pipeline", False, str(e)))
    
    # Test 5: Import service
    try:
        from humanization_service import HumanizationService, get_humanization_service
        logger.info("✅ humanization_service imported successfully")
        tests.append(("service", True, None))
    except Exception as e:
        logger.error(f"❌ humanization_service import failed: {str(e)}")
        tests.append(("service", False, str(e)))
    
    # Summary
    logger.info("\n" + "="*60)
    passed = sum(1 for _, status, _ in tests if status)
    total = len(tests)
    
    if passed == total:
        logger.info(f"✅ ALL TESTS PASSED ({passed}/{total})")
        return True
    else:
        logger.error(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        for name, status, error in tests:
            if not status:
                logger.error(f"   - {name}: {error}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
