from rewriter import TextRewriteService

service = TextRewriteService()

# Test text with multiple paragraphs (using explicit newlines)
test_text = "Artificial intelligence is transforming the world. Machine learning is powerful.\n\nThe applications are vast. Healthcare and finance benefit greatly.\n\nHowever, concerns exist. Privacy and ethics are important.\n\nDespite challenges, AI advances. Regulations will evolve."

print(f"Original text:")
print(f"  Paragraphs: {test_text.count(chr(10)+chr(10)) + 1}")
print(f"  Length: {len(test_text)} chars")
print(f"  Content:\n{test_text[:200]}...\n")

result, error = service.rewrite_text_with_modifications(test_text)

if error:
    print(f'Error: {error}')
else:
    print(f"Result text:")
    print(f"  Paragraphs: {result.count(chr(10)+chr(10)) + 1}")
    print(f"  Length: {len(result)} chars")
    print(f"  Structure preserved: {result.count(chr(10)+chr(10)) == test_text.count(chr(10)+chr(10))}")
    print(f"\nResult preview:\n{result[:300]}...")
