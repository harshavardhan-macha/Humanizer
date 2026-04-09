#!/usr/bin/env python3
"""Quick test of enhanced humanization"""

from main import HumanizerService

def test():
    text = 'Artificial Intelligence is changing the world rapidly. AI technology is advancing very fast.'
    service = HumanizerService()
    
    result, stats = service.humanize_text(
        text,
        use_paraphrasing=True,
        use_enhanced_rewriting=True,
        add_variations=True,
        variation_intensity=0.85
    )
    
    print('='*80)
    print('ORIGINAL TEXT:')
    print(text)
    print('='*80)
    print('FINAL HUMANIZED TEXT:')
    print(result)
    print('='*80)
    print(f'Length: {len(text)} → {len(result)} chars')
    print(f'Processing: {" → ".join(stats.get("processing_steps", []))}')
    
if __name__ == "__main__":
    test()
