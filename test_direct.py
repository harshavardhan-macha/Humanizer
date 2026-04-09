#!/usr/bin/env python3
"""Direct test of humanization without slow imports"""

from human_rewriter import apply_human_style_rewrite
from human_variations import humanize_with_natural_variations

text = "Artificial Intelligence is changing the world rapidly. AI technology is advancing very fast. These systems are deployed across industries."

print("="*80)
print("ORIGINAL:")
print(text)
print("\n" + "="*80)

# Step 1: Human-style rewriting
print("\nSTEP 1: Human-Style Rewriting (intensity 0.85)...")
result1, _ = apply_human_style_rewrite(text, intensity=0.85)
print(result1)

# Step 2: Human variations
print("\n" + "="*80)
print("STEP 2: Adding Human Variations (intensity 0.6)...")
result2, _ = humanize_with_natural_variations(result1, variation_intensity=0.6)
print(result2)

print("\n" + "="*80)
print("FINAL TRANSFORMATION:")
print("Original length: ", len(text), "chars")
print("Final length:   ", len(result2), "chars")
print("Changed:        ", len(text) != len(result2))
