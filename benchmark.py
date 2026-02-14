#!/usr/bin/env python3
"""
Performance benchmark for the Humanizer application.
Run this script to measure humanification speed.
"""

import time
import json
import requests
from typing import Dict, Tuple

# Test texts of varying lengths
TEST_TEXTS = {
    "short": "This is an AI-generated paragraph that needs to be humanized. It contains typical patterns found in machine learning outputs.",
    
    "medium": """Artificial intelligence has become increasingly prevalent in modern society, with applications ranging from natural language processing to computer vision. 
    The development of deep learning models has revolutionized the field, enabling machines to perform complex tasks with remarkable accuracy. 
    However, the generated text often exhibits patterns that distinguish it from human writing, necessitating the use of specialized tools for humanization.""",
    
    "long": """The rapid advancement of artificial intelligence technologies has fundamentally transformed the landscape of modern computing and digital communication. 
    Machine learning algorithms, particularly those based on deep neural networks, have demonstrated remarkable capabilities in processing and generating natural language. 
    These systems are extensively utilized across various domains, including customer service automation, content generation, and information retrieval. 
    However, the output produced by these models frequently exhibits distinctive linguistic patterns and stylistic characteristics that differentiate it from authentic human writing. 
    This distinction arises from the underlying computational mechanisms and training methodologies employed in developing these systems. 
    Consequently, texts generated purely through artificial means may be readily identifiable by discerning readers or specialized detection algorithms. 
    The development of humanization techniques has become increasingly important for ensuring that automatically generated content maintains an authentic and natural appearance. 
    Various approaches have been proposed to address this challenge, ranging from simple rule-based transformations to sophisticated neural network-based methods."""
}

class HumanizerBenchmark:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results = []
    
    def check_server(self) -> bool:
        """Check if the server is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False
    
    def benchmark_humanization(self, text: str, text_name: str, enhanced: bool = False) -> Tuple[float, Dict]:
        """Benchmark humanization for a given text"""
        payload = {
            "text": text,
            "paraphrasing": True,
            "enhanced": enhanced
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/humanize",
                json=payload,
                timeout=60
            )
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return elapsed_time, data.get("statistics", {})
            else:
                print(f"  ❌ Error: {response.status_code}")
                return elapsed_time, {}
        
        except requests.Timeout:
            print(f"  ❌ Request timed out after 60 seconds")
            return 60.0, {}
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return 0.0, {}
    
    def run_benchmark(self):
        """Run the complete benchmark"""
        print("=" * 70)
        print("🚀 Humanizer Performance Benchmark")
        print("=" * 70)
        
        # Check server
        print("\n📡 Checking server status...")
        if not self.check_server():
            print("❌ Server is not running!")
            print("   Start it with: python main.py")
            return
        print("✅ Server is running\n")
        
        # Benchmark each text size
        for text_size in ["short", "medium", "long"]:
            text = TEST_TEXTS[text_size]
            text_length = len(text)
            
            print(f"\n{'=' * 70}")
            print(f"📝 Testing {text_size.upper()} text ({text_length} characters)")
            print(f"{'=' * 70}")
            
            # Test with enhanced=False (default, fast)
            print(f"\n⚡ Mode: FAST (enhanced=False)")
            time_fast, stats_fast = self.benchmark_humanization(text, text_size, enhanced=False)
            print(f"  ⏱️  Time: {time_fast:.2f}s")
            if stats_fast:
                print(f"  📊 Original: {stats_fast.get('original_length', 0)} chars")
                print(f"  📊 Humanized: {stats_fast.get('final_length', 0)} chars")
            
            # Test with enhanced=True (slower but more variation)
            print(f"\n🎨 Mode: ENHANCED (enhanced=True)")
            time_enhanced, stats_enhanced = self.benchmark_humanization(text, text_size, enhanced=True)
            print(f"  ⏱️  Time: {time_enhanced:.2f}s")
            if stats_enhanced:
                print(f"  📊 Original: {stats_enhanced.get('original_length', 0)} chars")
                print(f"  📊 Humanized: {stats_enhanced.get('final_length', 0)} chars")
            
            # Calculate speedup
            if time_enhanced > 0:
                speedup = time_enhanced / time_fast if time_fast > 0 else 1
                print(f"\n⚡ Speed difference: {speedup:.1f}x faster in FAST mode")
            
            # Store results
            self.results.append({
                "size": text_size,
                "length": text_length,
                "fast_mode": time_fast,
                "enhanced_mode": time_enhanced
            })
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print benchmark summary"""
        print(f"\n\n{'=' * 70}")
        print("📊 BENCHMARK SUMMARY")
        print(f"{'=' * 70}\n")
        
        print(f"{'Text Size':<15} {'Length':<12} {'Fast Mode':<15} {'Enhanced':<15} {'Speedup':<10}")
        print("-" * 70)
        
        for result in self.results:
            fast = result["fast_mode"]
            enhanced = result["enhanced_mode"]
            speedup = enhanced / fast if fast > 0 else 1
            
            print(f"{result['size']:<15} {result['length']:<12} {fast:<14.2f}s {enhanced:<14.2f}s {speedup:>6.1f}x")
        
        # Overall statistics
        total_fast = sum(r["fast_mode"] for r in self.results)
        total_enhanced = sum(r["enhanced_mode"] for r in self.results)
        avg_speedup = total_enhanced / total_fast if total_fast > 0 else 1
        
        print("-" * 70)
        print(f"{'TOTAL':<15} {'':<12} {total_fast:<14.2f}s {total_enhanced:<14.2f}s {avg_speedup:>6.1f}x")
        
        print(f"\n💡 Recommendation:")
        print(f"   Use FAST mode (enhanced=False) for ~{avg_speedup:.1f}x improvement")
        print(f"   Only use ENHANCED mode when maximum text variation is needed")
        
        print(f"\n✅ Benchmark complete!")

def main():
    """Main entry point"""
    import sys
    
    benchmark = HumanizerBenchmark()
    
    # Allow custom server URL
    if len(sys.argv) > 1:
        benchmark.base_url = sys.argv[1]
        print(f"Using server: {benchmark.base_url}")
    
    benchmark.run_benchmark()

if __name__ == "__main__":
    main()
