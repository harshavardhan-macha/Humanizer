<script>
    import { onMount } from 'svelte';
    import { derived } from 'svelte/store';
    import '$lib/style.css';

    // Import minimal icons
    import { 
        Target, Sparkles, FileEdit,
        HelpCircle, Copy, CheckCircle, XCircle
    } from 'lucide-svelte';

    import {
        inputText, isProcessing, currentStep, error, results, statistics,
        availableModels, currentModel, selectedModel, useEnhanced, backendStatus,
        toastMessage, toastType, showToastFlag,
        combinedResults, showCombinedResults, showMultiResults,
        copyToClipboard, loadBackendInfo, humanizeWithSingleModel,
        humanizeAndCheck, showToast,
        getHumanizationModelInfo, getRecommendedHumanizationModel
    } from '$lib/script.js';

    import { writable } from 'svelte/store';
    const showHumanizationHelp = writable(false);

    const characterCount = derived(inputText, $inputText => $inputText.length);
    const wordCount = derived(inputText, $inputText =>
        $inputText.trim().split(/\s+/).filter(word => word.length > 0).length
    );

    const humanizationModelInfo = getHumanizationModelInfo();

    const handleHumanizeWithSingleModel = () => {
        humanizeWithSingleModel($inputText, $selectedModel, $useEnhanced);
    };

    const handleHumanizeAndCheck = () => {
        humanizeAndCheck($inputText, $useEnhanced, $selectedModel);
    };

    const setRecommendedHumanizationModels = (criteria) => {
        const recommended = getRecommendedHumanizationModel(criteria);
        selectedModel.set(recommended);
    };

    onMount(() => {
        selectedModel.set(getRecommendedHumanizationModel('performance'));
        loadBackendInfo().catch(err => console.error('Failed to load backend info:', err));
    });
</script>

<svelte:head>
    <title>VHumanize</title>
    <meta name="description" content="Transform AI-generated text into natural, human-like content and detect AI-generated text" />
</svelte:head>

<!-- Toast Notification -->
{#if $showToastFlag}
    <div class="toast toast--{$toastType}">
        <div class="toast__content">
            {$toastMessage}
        </div>
    </div>
{/if}

<div class="app">
    <!-- Action Navigation Bar with Brand -->
    <nav class="nav-bar">
        <div class="nav-container">
            <div class="nav-brand">
                <h1 class="brand-title">VHumanize</h1>
                {#if $backendStatus}
                    <div class="status-dot" class:status-dot--connected={$backendStatus.status === 'healthy'}></div>
                {/if}
            </div>
            <div class="nav-sections">
                <div class="nav-section">
                    <div class="nav-section__title">Humanization</div>
                    <div class="nav-buttons">
                        <button 
                            class="nav-btn nav-btn--combined" 
                            on:click={handleHumanizeAndCheck} 
                            disabled={$isProcessing || !$inputText.trim()}
                            title="Humanize text and verify improvement"
                        >
                            {#if $isProcessing && $currentStep === 'humanizing and checking'}
                                <div class="spinner"></div>
                                Processing...
                            {:else}
                                <Sparkles size={16} />
                                Humanize & Verify
                            {/if}
                        </button>
                        
                        <button 
                            class="nav-btn nav-btn--humanize" 
                            on:click={handleHumanizeWithSingleModel} 
                            disabled={$isProcessing || !$inputText.trim()}
                            title="Standard humanization"
                        >
                            {#if $isProcessing}
                                <div class="spinner"></div>
                                {$currentStep === 'paraphrasing' ? 'Paraphrasing...' : 
                                 $currentStep === 'rewriting' ? 'Rewriting...' : 'Processing...'}
                            {:else}
                                <Target size={16} />
                                Standard
                            {/if}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <main class="main">
        <div class="main-container">
            <!-- Configuration Sidebar (Only Config Options) -->
            <aside class="sidebar">
                <!-- Humanization Configuration -->
                <section class="sidebar-section">
                    <div class="section-header">
                        <h3 class="sidebar-title">
                            Humanization Settings
                            <button 
                                class="help-btn" 
                                on:click={() => showHumanizationHelp.update(v => !v)}
                                title="Show help"
                            >
                                <HelpCircle size={12} />
                            </button>
                        </h3>
                    </div>

                    {#if $showHumanizationHelp}
                        <div class="help-panel">
                            <h4><Lightbulb size={16} class="inline-icon" />How Humanization Works:</h4>
                            <ul class="help-list">
                                <li><strong>Step 1:</strong> Paraphrasing - Restructures sentences while keeping meaning</li>
                                <li><strong>Step 2:</strong> Rewriting - Applies human-like patterns and styles</li>
                                <li><strong>Enhanced:</strong> Uses advanced prompts for better quality (slower)</li>
                            </ul>
                        </div>
                    {/if}
                    
                    <div class="config-option">
                        <label class="option">
                            <input type="checkbox" bind:checked={$useEnhanced} />
                            <span class="option__text">
                                Enhanced Rewriting
                                <small class="option__description">
                                    Uses advanced prompts with better context understanding. 
                                    Slower but produces more natural, human-like text.
                                </small>
                            </span>
                        </label>
                    </div>

                    {#if $availableModels.length > 1}
                        <div class="config-option">
                            <label class="config-label">
                                Humanization Model:
                                <small class="config-description">
                                    Choose a specific model for humanization. Different models have varying writing styles and capabilities.
                                </small>
                            </label>
                            
                            <div class="model-selection">
                                <div class="quick-select">
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedHumanizationModels('performance')}
                                    >
                                        Best Performance
                                    </button>
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedHumanizationModels('speed')}
                                    >
                                        Fastest
                                    </button>
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedHumanizationModels('balanced')}
                                    >
                                        Balanced
                                    </button>
                                </div>

                                <div class="model-checkboxes">
                                    {#each $availableModels as model}
                                        <label class="model-checkbox">
                                            <input 
                                                type="radio" 
                                                name="humanization-model"
                                                value={model}
                                                bind:group={$selectedModel}
                                            />
                                            <div class="model-checkbox__content">
                                                <div class="model-checkbox__name">
                                                    {humanizationModelInfo[model]?.name || model}
                                                </div>
                                                <div class="model-checkbox__meta">
                                                    <span class="model-type">{humanizationModelInfo[model]?.type}</span>
                                                    <span class="model-speed">Speed: {humanizationModelInfo[model]?.speed}</span>
                                                    <span class="model-accuracy">Acc: {humanizationModelInfo[model]?.accuracy}</span>
                                                </div>
                                                <div class="model-checkbox__description">
                                                    {humanizationModelInfo[model]?.description}
                                                </div>
                                            </div>
                                        </label>
                                    {/each}
                                </div>
                                
                                <div class="selection-summary">
                                    Selected: {humanizationModelInfo[$selectedModel]?.name || $selectedModel || 'None'}
                                </div>
                            </div>
                        </div>
                    {/if}
                </section>



            </aside>

            <!-- Right Content Area -->
            <div class="content">
                <!-- Input Section -->
                <section class="input-section">
                    <div class="input-header">
                        <label class="input-label">
                            <FileEdit size={18} class="inline-icon" />
                            Enter AI-generated text to humanize
                        </label>
                        <div class="stats">
                            {$characterCount} / 50,000 chars • {$wordCount} words
                        </div>
                    </div>
                    
                    <textarea
                        bind:value={$inputText}
                        placeholder="Paste your AI-generated text here..."
                        class="textarea"
                        rows="15"
                        maxlength="50000"
                    ></textarea>
                </section>

                <!-- Error Display -->
                {#if $error}
                    <div class="error">
                        <AlertTriangle size={16} class="error__icon" />
                        {$error}
                    </div>
                {/if}



                <!-- Combined Results -->
                {#if $showCombinedResults && $combinedResults}
                    <section class="results">
                        <h2 class="results__title">Humanization & Detection Results</h2>
                        
                        <div class="combined-summary">
                            <div class="improvement-badge" class:improved={$combinedResults.improvement.detection_improved} class:not-improved={!$combinedResults.improvement.detection_improved}>
                                {#if $combinedResults.improvement.detection_improved}
                                    <CheckCircle size={16} />
                                    Detection Improved!
                                {:else}
                                    <XCircle size={16} />
                                    No Improvement
                                {/if}
                            </div>
                            
                            <div class="improvement-stats">
                                <span>
                                    Reduction: {($combinedResults.improvement.ai_probability_reduction * 100).toFixed(1)}%
                                </span>
                                <span>
                                    Improvement: {$combinedResults.improvement.percentage_improvement.toFixed(1)}%
                                </span>
                            </div>
                        </div>

                        <div class="before-after">
                            <div class="detection-comparison">
                                <div class="before-detection">
                                    <h4>Before Humanization</h4>
                                    <div class="detection-result">
                                        <div class="prediction-small" class:ai-detected={$combinedResults.original_detection.is_ai_generated}>
                                            {$combinedResults.original_detection.prediction}
                                        </div>
                                        <div class="probability">AI: {($combinedResults.original_detection.ai_probability * 100).toFixed(1)}%</div>
                                    </div>
                                </div>

                                <div class="after-detection">
                                    <h4>After Humanization</h4>
                                    <div class="detection-result">
                                        <div class="prediction-small" class:ai-detected={$combinedResults.humanized_detection.is_ai_generated} class:human-detected={!$combinedResults.humanized_detection.is_ai_generated}>
                                            {$combinedResults.humanized_detection.prediction}
                                        </div>
                                        <div class="probability">AI: {($combinedResults.humanized_detection.ai_probability * 100).toFixed(1)}%</div>
                                    </div>
                                </div>
                            </div>

                            <div class="text-comparison">
                                <div class="text-before">
                                    <div class="text-header">
                                        <h4>Original Text</h4>
                                        <button class="copy-btn" on:click={() => copyToClipboard($combinedResults.original_text)}>
                                            <Copy size={14} />
                                            Copy
                                        </button>
                                    </div>
                                    <div class="text-content">
                                        {$combinedResults.original_text}
                                    </div>
                                </div>

                                <div class="text-after">
                                    <div class="text-header">
                                        <h4>Humanized Text</h4>
                                        <button class="copy-btn copy-btn--primary" on:click={() => copyToClipboard($combinedResults.humanized_text)}>
                                            <Copy size={14} />
                                            Copy
                                        </button>
                                    </div>
                                    <div class="text-content">
                                        {$combinedResults.humanized_text}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                {/if}

                <!-- Single Pipeline Result -->
                {#if $results.final && !$showMultiResults}
                    <section class="results">
                        <h2 class="results__title">Humanized Text</h2>
                        
                        <!-- Show both steps -->
                        <div class="pipeline-results">
                            {#if $results.paraphrased}
                                <div class="step-result">
                                    <div class="step-result__header">
                                        <h3>Step 1: Paraphrased</h3>
                                        <button class="copy-btn" on:click={() => copyToClipboard($results.paraphrased)}>
                                            <Copy size={14} />
                                            Copy
                                        </button>
                                    </div>
                                    <div class="step-result__text">
                                        {$results.paraphrased}
                                    </div>
                                </div>
                            {/if}

                            <div class="step-result step-result--final">
                                <div class="step-result__header">
                                    <h3>Step 2: Final Humanized Text</h3>
                                    <button class="copy-btn copy-btn--primary" on:click={() => copyToClipboard($results.final)}>
                                        <Copy size={14} />
                                        Copy Final
                                    </button>
                                </div>
                                <div class="step-result__text">
                                    {$results.final}
                                </div>
                                
                                {#if $statistics && Object.keys($statistics).length > 0}
                                    <div class="quick-stats">
                                        <span>
                                            {$statistics.original_length || 0} → {$statistics.paraphrased_length || 0} → {$statistics.final_length || $statistics.rewritten_length || 0} chars
                                        </span>
                                        {#if $statistics.model_used}
                                            <span>• Model: {$statistics.model_used}</span>
                                        {/if}
                                        {#if $statistics.enhanced_rewriting_used}
                                            <span>• Enhanced rewriting</span>
                                        {/if}
                                    </div>
                                {/if}
                            </div>
                        </div>
                    </section>
                {/if}
            </div>
        </div>
    </main>
</div>

<style>
    .inline-icon {
        display: inline-block;
        vertical-align: middle;
        margin-right: 0.25rem;
    }
    
    /* Enhanced model selection styles */
    .model-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        margin-left: 8px;
    }
    
    .model-badge--t5 {
        background: #e3f2fd;
        color: #1565c0;
    }
    
    .model-badge--transformer {
        background: #f3e5f5;
        color: #7b1fa2;
    }
    
    .model-ratings {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin: 8px 0;
    }
    
    .model-rating {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
    }
    
    .rating-label {
        font-weight: 500;
        color: var(--text-secondary);
    }
    
    .rating-stars {
        font-family: monospace;
        color: #ffc107;
        font-size: 11px;
        letter-spacing: 1px;
    }
    
    .model-type-badge {
        background: var(--surface-2);
        color: var(--text-secondary);
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: 500;
        text-transform: capitalize;
    }
    
    .model-status {
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 10px;
    }
    
    .model-status--loaded {
        background: #e8f5e8;
        color: #2e7d32;
    }
    
    .model-status--available {
        background: #fff3e0;
        color: #ef6c00;
    }
    
    .model-recommendation {
        margin-top: 6px;
        font-size: 11px;
        font-weight: 600;
        color: var(--accent);
        text-align: center;
        padding: 4px;
        background: var(--accent-bg);
        border-radius: 4px;
    }
    
    .selection-summary {
        margin-top: 16px;
        padding: 12px;
        background: var(--surface-1);
        border-radius: 8px;
        border: 1px solid var(--border);
    }
    
    .selected-model {
        margin-bottom: 8px;
        font-size: 14px;
    }
    
    .selected-model-details {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 12px;
        color: var(--text-secondary);
    }
    
    .detail-item {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    .quick-select {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 8px;
        margin-bottom: 16px;
    }
    
    .quick-select .btn {
        font-size: 12px;
        padding: 6px 8px;
        white-space: nowrap;
    }
</style>

