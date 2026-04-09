#!/usr/bin/env python3
"""Test complete humanization pipeline with aggressive rewriter"""

from main import HumanizerService
import logging

logging.basicConfig(level=logging.WARNING)

text = "Artificial Intelligence is changing the world rapidly. AI technology is advancing very fast. These systems are being deployed across numerous industries and are having significant impact."

print("="*80)
print("ORIGINAL TEXT:")
print(text)
print("\nLength:", len(text), "chars")
print("="*80)

service = HumanizerService()
result, stats = service.humanize_text(
    text,
    use_paraphrasing=False,
    use_enhanced_rewriting=True,
    add_variations=True,
    variation_intensity=0.85
)

print("\nHUMANIZED TEXT:")
print(result)
print("\nLength:", len(result), "chars")
print("="*80)
print("Processing steps:", " → ".join(stats.get("processing_steps", [])))
