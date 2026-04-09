"""
Comprehensive Benchmark Script
Tests the optimized pipeline vs original and shows detailed metrics.
Run: python benchmark_optimized.py
"""

import logging
import sys
import time
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test texts (various AI complexity levels)
TEST_TEXTS = {
    "simple_ai": """
    Artificial intelligence has become increasingly important in modern society. 
    The technology is utilized across various industries to enhance productivity. 
    Furthermore, machine learning algorithms continue to advance at a rapid pace.
    """,
    
    "medium_ai": """
    The implementation of advanced AI systems presents both opportunities and challenges. 
    Organizations must leverage cutting-edge technology while maintaining ethical standards. 
    It is worth noting that the comprehensive approach to data management is crucial for success. 
    Moreover, the paradigm shift in how we approach automation requires careful consideration of 
    workforce implications. We must facilitate proper training and development for employees.
    """,
    
    "heavy_ai": """
    The utilization of sophisticated neural network architectures has facilitated unprecedented 
    advances in natural language processing. Furthermore, the comprehensive integration of 
    transformer-based models has demonstrated robust performance across heterogeneous datasets. 
    Notably, the leverage of attention mechanisms has enabled more nuanced semantic understanding. 
    In conclusion, it is crucial that organizations implement scalable solutions while maintaining 
    paradigm coherence. The aforementioned strategies, when implemented synergistically, demonstrate 
    substantial efficacy in optimizing computational efficiency.
    """,
}


def compare_outputs(original: str, humanized: str) -> Dict:
    """Compare two texts at various levels"""
    from humanization_scorer import HumanizationScorer
    
    scorer = HumanizationScorer()
    original_score = scorer.score_text(original)
    humanized_score = scorer.score_text(humanized)
    
    return {
        "original": original_score,
        "humanized": humanized_score,
        "improvement": {
            "overall": humanized_score['overall_score'] - original_score['overall_score'],
            "sentence_variance": humanized_score['sentence_variance'] - original_score['sentence_variance'],
            "ai_phrase_reduction": max(0, original_score['ai_phrase_penalty'] - humanized_score['ai_phrase_penalty']),
            "lexical_diversity": humanized_score['lexical_diversity'] - original_score['lexical_diversity'],
            "contraction_increase": humanized_score['contraction_score'] - original_score['contraction_score'],
            "human_signature_increase": humanized_score['human_signature_score'] - original_score['human_signature_score'],
        }
    }


def print_benchmark_results(test_name: str, original: str, humanized: str, elapsed: float, stats: Dict):
    """Print formatted benchmark results"""
    comparison = compare_outputs(original, humanized)
    
    print("\n" + "="*80)
    print(f"TEST: {test_name}")
    print("="*80)
    
    # Text samples
    print(f"\n📄 ORIGINAL TEXT:")
    print(f"  {original[:150]}...")
    print(f"\n✨ HUMANIZED TEXT:")
    print(f"  {humanized[:150]}...")
    
    # Metrics
    print(f"\n⏱️  Processing Time: {elapsed:.2f}s")
    print(f"📏 Length: {len(original)} → {len(humanized)} chars ({(len(humanized)-len(original)):+d})")
    
    # Scores
    print(f"\n📊 HUMANIZATION SCORES:")
    print(f"  {'Metric':<35} {'Original':>10} {'Humanized':>10} {'Change':>10}")
    print(f"  {'-'*65}")
    
    metrics = [
        ('Overall Score', 'overall_score'),
        ('Sentence Variance', 'sentence_variance'),
        ('Lexical Diversity', 'lexical_diversity'),
        ('Contraction Score', 'contraction_score'),
        ('Human Signatures', 'human_signature_score'),
    ]
    
    for label, key in metrics:
        orig = comparison['original'].get(key, 0)
        hum = comparison['humanized'].get(key, 0)
        change = hum - orig
        
        change_pct = (change / orig * 100) if orig > 0 else 0
        change_str = f"{change:+.2f} ({change_pct:+.0f}%)" if abs(change) > 0.01 else "—"
        
        print(f"  {label:<35} {orig:>10.2f} {hum:>10.2f} {change_str:>10}")
    
    # AI Phrase Penalty (lower is better)
    print(f"\n  {'AI Phrases (penalty)':<35} {comparison['original'].get('ai_phrase_penalty', 0):>10.1f} {comparison['humanized'].get('ai_phrase_penalty', 0):>10.1f} {comparison['improvement']['ai_phrase_reduction']:>+10.1f}")
    
    # Stages applied
    if 'stages_applied' in stats:
        print(f"\n🔧 Pipeline Stages Applied:")
        for stage in stats.get('stages_applied', []):
            print(f"  ✓ {stage}")
    
    # Retries if any
    if stats.get('retries', 0) > 0:
        print(f"\n  ⚠️  Retried {stats['retries']} time(s) to improve score")
    
    print(f"\n✅ Overall Improvement: {comparison['improvement']['overall']:+.1f} points")
    
    return comparison


def benchmark_optimized_pipeline():
    """Run full benchmark on optimized pipeline"""
    from optimized_humanization_pipeline import humanize_text_optimized
    
    print("\n" + "="*80)
    print("🚀 OPTIMIZED PIPELINE BENCHMARK")
    print("="*80)
    
    all_results = {}
    
    for test_name, original_text in TEST_TEXTS.items():
        original_text = original_text.strip()
        
        logger.info(f"\n📌 Running test: {test_name}...")
        
        # Run humanization
        start = time.time()
        humanized, stats = humanize_text_optimized(original_text, intensity=0.85)
        elapsed = time.time() - start
        
        # Print results
        comparison = print_benchmark_results(test_name, original_text, humanized, elapsed, stats)
        all_results[test_name] = {
            "original": original_text,
            "humanized": humanized,
            "comparison": comparison,
            "stats": stats,
            "elapsed": elapsed
        }
    
    # SUMMARY
    print("\n" + "="*80)
    print("📈 SUMMARY")
    print("="*80)
    print(f"\n{'Test Case':<20} {'Score Gain':>12} {'Best Metric':>20} {'Time':>10}")
    print(f"{'-'*62}")
    
    for test_name, result in all_results.items():
        improvement = result['comparison']['improvement']['overall']
        
        # Find best improvement
        improvements = result['comparison']['improvement']
        best_metric = max(improvements.items(), key=lambda x: abs(x[1]) if x[0] != 'overall' else 0)
        best_metric_name = best_metric[0].replace('_', ' ').title()[:15]
        best_value = best_metric[1]
        
        print(f"{test_name:<20} {improvement:>+11.1f} pts {best_metric_name:<20} {result['elapsed']:>9.2f}s")
    
    print("\n✅ Benchmark Complete!\n")
    return all_results


def benchmark_specific_text(text: str):
    """Benchmark a specific custom text"""
    from optimized_humanization_pipeline import humanize_and_score
    
    print("\n" + "="*80)
    print("🔍 CUSTOM TEXT BENCHMARK")
    print("="*80)
    
    start = time.time()
    result = humanize_and_score(text)
    elapsed = time.time() - start
    
    print(f"\n⏱️  Processing Time: {elapsed:.2f}s")
    print(f"\n📝 Original ({len(text)} chars):")
    print(f"  {text[:200]}...")
    print(f"\n✨ Humanized ({len(result['humanized_text'])} chars):")
    print(f"  {result['humanized_text'][:200]}...")
    
    print(f"\n📊 Final Score: {result['scores']['after']['overall_score']:.1f}/100")
    print(f"   Improvement: {result['scores']['after']['overall_score'] - result['scores']['before']['overall_score']:+.1f} points")
    
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Custom text provided
        custom_text = " ".join(sys.argv[1:])
        benchmark_specific_text(custom_text)
    else:
        # Run full benchmark
        try:
            results = benchmark_optimized_pipeline()
            
            # Save results to file
            import json
            with open("benchmark_results.json", "w") as f:
                json.dump({
                    k: {
                        "original": v["original"],
                        "humanized": v["humanized"],
                        "improvement": v["comparison"]["improvement"],
                        "elapsed": v["elapsed"]
                    }
                    for k, v in results.items()
                }, f, indent=2)
            
            print("💾 Results saved to benchmark_results.json")
        
        except Exception as e:
            logger.error(f"❌ Benchmark failed: {str(e)}", exc_info=True)
            sys.exit(1)
