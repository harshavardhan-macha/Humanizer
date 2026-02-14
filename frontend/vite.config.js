import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	build: {
		// Enable code splitting for better caching
		rollupOptions: {
			output: {
				manualChunks: {
					// Create separate chunks for better lazy loading
					'lucide': ['lucide-svelte'],
					'svelte-core': ['svelte/store', 'svelte'],
				}
			}
		},
		// Optimize chunk size
		chunkSizeWarningLimit: 1000,
		// Use minification
		minify: 'terser',
		terserOptions: {
			compress: {
				drop_console: false, // Keep console for debugging in dev
				passes: 2
			},
			format: {
				comments: false
			}
		}
	},
	// Optimize performance
	optimizeDeps: {
		include: ['svelte/store', 'svelte', 'lucide-svelte'],
		exclude: []
	}
});
