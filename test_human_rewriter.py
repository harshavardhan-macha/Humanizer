#!/usr/bin/env python3
"""Test aggressive human-style rewriter"""

from human_rewriter import apply_human_style_rewrite

# Test 1: Short text
short_text = "Artificial Intelligence is changing the world rapidly."
print("="*80)
print("TEST 1: Short Text")
print("="*80)
print("Original:")
print(short_text)
print("\nHuman-style rewritten:")
result, error = apply_human_style_rewrite(short_text, intensity=0.85)
print(result)

# Test 2: Medium text
medium_text = "Artificial Intelligence is changing the world rapidly. AI technology is advancing very fast. Machine learning improves performance automatically."
print("\n" + "="*80)
print("TEST 2: Medium Text")
print("="*80)
print("Original:")
print(medium_text)
print("\nHuman-style rewritten:")
result, error = apply_human_style_rewrite(medium_text, intensity=0.85)
print(result)

# Test 3: Longer text
long_text = "The development of artificial intelligence has significantly impacted modern society. AI systems are being deployed across numerous industries. These technologies enable organizations to automate complex tasks and improve operational efficiency. However, there are also important considerations regarding privacy and security that must be addressed."
print("\n" + "="*80)
print("TEST 3: Longer Text")
print("="*80)
print("Original:")
print(long_text)
print("\nHuman-style rewritten:")
result, error = apply_human_style_rewrite(long_text, intensity=0.85)
print(result)
