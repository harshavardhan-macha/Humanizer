// Frontend Performance Monitoring
// Add this to src/lib/performance.js

/**
 * Performance monitoring and metrics collection
 * Usage: import and call initPerformanceMonitoring() in +page.svelte onMount
 */

export class PerformanceMonitor {
    constructor() {
        this.metrics = {};
        this.marks = {};
        this.startTime = performance.now();
    }

    /**
     * Mark a named checkpoint
     */
    mark(name) {
        if (typeof performance !== 'undefined') {
            performance.mark(name);
            this.marks[name] = performance.now();
        }
    }

    /**
     * Measure time between two marks
     */
    measure(name, startMark, endMark) {
        if (typeof performance !== 'undefined') {
            try {
                performance.measure(name, startMark, endMark);
                const measure = performance.getEntriesByName(name)[0];
                if (measure) {
                    this.metrics[name] = measure.duration;
                    return measure.duration;
                }
            } catch (e) {
                console.warn('Performance measure error:', e);
            }
        }
        return null;
    }

    /**
     * Get all Web Vitals
     */
    getWebVitals() {
        const vitals = {};

        // Get Navigation Timing
        if (typeof performance !== 'undefined' && performance.timing) {
            const timing = performance.timing;
            const navigationStart = timing.navigationStart;

            vitals.dns = timing.domainLookupEnd - timing.domainLookupStart;
            vitals.tcp = timing.connectEnd - timing.connectStart;
            vitals.ttfb = timing.responseStart - navigationStart; // Time to First Byte
            vitals.domContent = timing.domContentLoadedEventEnd - navigationStart;
            vitals.pageLoad = timing.loadEventEnd - navigationStart;
            vitals.domInteractive = timing.domInteractive - navigationStart;
            vitals.domComplete = timing.domComplete - navigationStart;
        }

        // Get Paint Timing
        if (typeof performance !== 'undefined' && performance.getEntriesByType) {
            const paintEntries = performance.getEntriesByType('paint');
            paintEntries.forEach(entry => {
                if (entry.name === 'first-paint') {
                    vitals.firstPaint = entry.startTime;
                } else if (entry.name === 'first-contentful-paint') {
                    vitals.fcp = entry.startTime;
                }
            });
        }

        return vitals;
    }

    /**
     * Get Largest Contentful Paint
     */
    observeLCP() {
        if (typeof PerformanceObserver !== 'undefined') {
            try {
                const observer = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    this.metrics.lcp = lastEntry.renderTime || lastEntry.loadTime;
                });
                observer.observe({ entryTypes: ['largest-contentful-paint'] });
                return observer;
            } catch (e) {
                console.warn('LCP observer not supported:', e);
            }
        }
        return null;
    }

    /**
     * Get Cumulative Layout Shift
     */
    observeCLS() {
        let clsValue = 0;
        if (typeof PerformanceObserver !== 'undefined') {
            try {
                const observer = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) {
                            clsValue += entry.value;
                            this.metrics.cls = clsValue;
                        }
                    }
                });
                observer.observe({ entryTypes: ['layout-shift'] });
                return observer;
            } catch (e) {
                console.warn('CLS observer not supported:', e);
            }
        }
        return null;
    }

    /**
     * Measure first interaction
     */
    observeFirstInput() {
        if (typeof PerformanceObserver !== 'undefined') {
            try {
                const observer = new PerformanceObserver((list) => {
                    const entry = list.getEntries()[0];
                    if (entry) {
                        this.metrics.fid = entry.processingDuration;
                        this.metrics.firstInputDelay = entry.processingDuration;
                    }
                });
                observer.observe({ entryTypes: ['first-input'] });
                return observer;
            } catch (e) {
                console.warn('FID observer not supported:', e);
            }
        }
        return null;
    }

    /**
     * Get current memory usage (Chrome only)
     */
    getMemoryUsage() {
        if (typeof performance !== 'undefined' && performance.memory) {
            return {
                usedMemory: (performance.memory.usedJSHeapSize / 1048576).toFixed(2) + ' MB',
                totalMemory: (performance.memory.totalJSHeapSize / 1048576).toFixed(2) + ' MB',
                memoryLimit: (performance.memory.jsHeapSizeLimit / 1048576).toFixed(2) + ' MB'
            };
        }
        return null;
    }

    /**
     * Print metrics to console in nice format
     */
    printMetrics() {
        console.group('📊 Performance Metrics');
        console.table(this.metrics);
        console.groupEnd();

        const vitals = this.getWebVitals();
        console.group('⏱️  Web Vitals');
        console.table(vitals);
        console.groupEnd();

        const memory = this.getMemoryUsage();
        if (memory) {
            console.group('💾 Memory Usage');
            console.table(memory);
            console.groupEnd();
        }
    }

    /**
     * Send metrics to analytics service
     */
    async sendMetrics(endpoint = '/api/metrics') {
        try {
            const payload = {
                timestamp: new Date().toISOString(),
                metrics: this.metrics,
                vitals: this.getWebVitals(),
                memory: this.getMemoryUsage(),
                userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown'
            };

            await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (e) {
            console.warn('Failed to send metrics:', e);
        }
    }
}

/**
 * Initialize performance monitoring
 */
export function initPerformanceMonitoring() {
    const monitor = new PerformanceMonitor();

    // Mark page start
    monitor.mark('page-start');

    // Observe Core Web Vitals
    monitor.observeLCP();
    monitor.observeCLS();
    monitor.observeFirstInput();

    // Log metrics when page loads
    window.addEventListener('load', () => {
        setTimeout(() => {
            monitor.printMetrics();
            // Optionally send to analytics:
            // monitor.sendMetrics();
        }, 0);
    });

    return monitor;
}

/**
 * API call performance tracker
 */
export class APIPerformanceTracker {
    constructor() {
        this.calls = [];
    }

    /**
     * Track API call
     */
    trackCall(endpoint, duration, status, size = 0) {
        this.calls.push({
            endpoint,
            duration: `${duration.toFixed(0)}ms`,
            status,
            size: size > 0 ? `${(size / 1024).toFixed(2)}KB` : 'unknown',
            timestamp: new Date().toISOString()
        });
    }

    /**
     * Get average response time
     */
    getAverageResponseTime() {
        if (this.calls.length === 0) return 0;
        const total = this.calls.reduce((sum, call) => {
            const duration = parseInt(call.duration);
            return sum + duration;
        }, 0);
        return (total / this.calls.length).toFixed(0);
    }

    /**
     * Print API metrics
     */
    printMetrics() {
        console.group('🌐 API Performance');
        console.table(this.calls);
        console.log(`Average response time: ${this.getAverageResponseTime()}ms`);
        console.groupEnd();
    }
}

/**
 * Use in script.js to track API calls:
 * 
 * export const apiTracker = new APIPerformanceTracker();
 * 
 * Then in API functions:
 * const startTime = performance.now();
 * const response = await fetch(url);
 * const duration = performance.now() - startTime;
 * apiTracker.trackCall(url, duration, response.status);
 */
