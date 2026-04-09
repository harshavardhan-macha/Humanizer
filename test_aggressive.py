#!/usr/bin/env python3
"""Quick test of aggressive rewriter module"""

from aggressive_rewriter import AggressiveRewriter, apply_aggressive_rewriting

# Test the aggressive rewriter
test_text = "The artificial intelligence system was designed to process large amounts of data. It could analyze patterns and make predictions. The model was trained on millions of examples."

print("Original text:")
print(test_text)
print("\n" + "="*80 + "\n")

# Test with high intensity
result_high, error_high = apply_aggressive_rewriting(test_text, intensity=0.9)
print("Aggressive rewriting (intensity 0.9):")
print(result_high)
print(f"\nError: {error_high}")
print("\n" + "="*80 + "\n")

# Test with medium intensity
result_med, error_med = apply_aggressive_rewriting(test_text, intensity=0.5)
print("Aggressive rewriting (intensity 0.5):")
print(result_med)
print(f"\nError: {error_med}")
