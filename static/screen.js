// Import widget system
import { createWidget, destroyWidget } from './widgets/registry.js';
import './widgets/clock.js';      // Register clock widget
import './widgets/countdown.js';  // Register countdown widget
import './widgets/chart.js';      // Register chart widget
import './widgets/weather.js';    // Register weather widget
import './widgets/stock.js';      // Register stock widget

// ============== Layout Presets ==============
const LAYOUT_PRESETS = {
    // Auto (backward compatible)
    "auto": {},

    // Vertical stacking (single column)
    "vertical": { columns: 1 },
    "vertical-6": { columns: 1, rows: 6 },
    "vertical-8": { columns: 1, rows: 8 },
    "vertical-10": { columns: 1, rows: 10 },
    "vertical-12": { columns: 1, rows: 12 },

    // Horizontal (single row)
    "horizontal": { rows: 1 },
    "horizontal-4": { columns: 4, rows: 1 },
    "horizontal-6": { columns: 6, rows: 1 },

    // Standard grids
    "grid-2x2": { columns: 2, rows: 2 },
    "grid-3x2": { columns: 3, rows: 2 },
    "grid-2x3": { columns: 2, rows: 3 },
    "grid-3x3": { columns: 3, rows: 3 },
    "grid-4x3": { columns: 4, rows: 3 },
    "grid-4x4": { columns: 4, rows: 4 },

    // Dashboard layouts (header/footer span full width)
    "dashboard-header": { columns: 3, rows: "auto 1fr 1fr", header_rows: 1 },
    "dashboard-footer": { columns: 3, rows: "1fr 1fr auto", footer_rows: 1 },
    "dashboard-both": { columns: 3, rows: "auto 1fr 1fr auto", header_rows: 1, footer_rows: 1 },

    // Menu/schedule layouts
    "menu-board": { columns: 2, rows: "auto 1fr 1fr 1fr 1fr 1fr 1fr", header_rows: 1 },
    "menu-3col": { columns: 3, rows: "auto 1fr 1fr 1fr 1fr", header_rows: 1 },
    "schedule": { columns: 1, rows: "auto 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr", header_rows: 1 },

    // Featured/sidebar layouts
    "featured-top": { columns: 3, rows: "2fr 1fr", header_rows: 1 },
    "sidebar-left": { columns: "1fr 3fr" },
    "sidebar-right": { columns: "3fr 1fr" }
};

// Extract screen ID from URL
const pathParts = window.location.pathname.split('/');
const screenId = pathParts[pathParts.length - 1];

// WebSocket connection
let ws = null;
const reconnectDelay = 1000;  // Retry every second, forever

// DOM elements
const screenEl = document.getElementById('screen');
const statusEl = document.getElementById('connection-status');

// Page state
let pages = [];              // Array of page objects
let currentPageIndex = 0;
let rotationEnabled = false;
let rotationInterval = 30;   // seconds
let rotationTimer = null;
let screenGap = '1rem';      // Screen-level gap default
let screenBorderRadius = '1rem';  // Screen-level border radius default
let screenPanelShadow = null;    // Screen-level panel shadow (null = no shadow)
let screenBackgroundColor = null;  // Screen-level background color
let screenPanelColor = null;       // Screen-level panel color
let screenFontFamily = null;       // Screen-level font family
let screenFontColor = null;        // Screen-level font color
let screenHeadHtml = null;         // Custom HTML for <head> (e.g., Google Fonts)
let screenDefaultLayout = null;    // Screen-level default layout
let screenTransition = 'none';     // Screen-level transition type
let screenTransitionDuration = 500; // Screen-level transition duration (ms)

// Transition state
let isTransitioning = false;       // Prevent overlapping transitions

// Debug state (persisted in localStorage)
let debugEnabled = localStorage.getItem('debugEnabled') === 'true';

// Active widget elements for cleanup
let activeWidgets = [];

// Initialize
connect();

// Show debug panel on load if it was previously enabled
if (debugEnabled) {
    // Wait for DOM to be ready, then show debug panel
    requestAnimationFrame(() => updateDebugDisplay());
}

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${screenId}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('Connected to screen');
        showStatus('connected', 'Connected');
        setTimeout(() => hideStatus(), 2000);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'pages_sync':
                // Full state replacement
                handlePagesSync(data.pages, data.rotation);
                break;

            case 'page_update':
                // Upsert single page
                handlePageUpdate(data.page);
                break;

            case 'page_delete':
                // Remove page
                handlePageDelete(data.page_name);
                break;

            case 'rotation_update':
                // Update rotation settings
                handleRotationUpdate(data.rotation);
                break;

            case 'message':
                // Legacy format - still supported for backward compatibility
                renderContent(data.content, {
                    backgroundColor: data.background_color,
                    panelColor: data.panel_color,
                    fontFamily: data.font_family,
                    fontColor: data.font_color,
                    gap: data.gap,
                    borderRadius: data.border_radius,
                    panelShadow: data.panel_shadow,
                    layout: data.layout
                });
                break;

            case 'reload':
                // Force reload, bypassing cache
                location.reload(true);
                break;

            case 'debug':
                // Toggle debug mode (persist in localStorage)
                debugEnabled = data.enabled;
                localStorage.setItem('debugEnabled', debugEnabled ? 'true' : 'false');
                updateDebugDisplay();
                break;
        }
    };

    ws.onclose = (event) => {
        console.log('Disconnected:', event.code, event.reason);
        showStatus('disconnected', 'Disconnected');

        if (event.code !== 4004) { // Don't reconnect if screen not found
            scheduleReconnect();
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function scheduleReconnect() {
    showStatus('reconnecting', 'Reconnecting...');
    setTimeout(connect, reconnectDelay);
}

function showStatus(type, message) {
    statusEl.className = `connection-status visible ${type}`;
    statusEl.textContent = message;
}

function hideStatus() {
    statusEl.classList.remove('visible');
}

function updateHeadHtml(newHeadHtml) {
    // Skip if unchanged
    if (newHeadHtml === screenHeadHtml) return;

    // Remove any previously injected head elements
    const existingContainer = document.getElementById('custom-head-html');
    if (existingContainer) {
        existingContainer.remove();
    }

    screenHeadHtml = newHeadHtml;

    // Inject new head HTML if provided
    if (screenHeadHtml) {
        const container = document.createElement('div');
        container.id = 'custom-head-html';
        container.innerHTML = screenHeadHtml;

        // Move all child elements to head
        while (container.firstChild) {
            document.head.appendChild(container.firstChild);
        }
    }
}

// Debug pause state
let debugPaused = false;

function updateDebugDisplay() {
    let debugEl = document.getElementById('debug-info');

    if (debugEnabled) {
        // Create debug panel if it doesn't exist
        if (!debugEl) {
            debugEl = document.createElement('div');
            debugEl.id = 'debug-info';
            debugEl.style.cssText = 'position:fixed;top:10px;left:10px;background:rgba(0,0,0,0.9);color:#0f0;padding:15px;z-index:9999;font-size:14px;font-family:monospace;border-radius:8px;max-width:500px;line-height:1.6;';
            document.body.appendChild(debugEl);
        }

        // Gather debug info
        const activePages = getActivePages();
        const currentPage = activePages[currentPageIndex] || null;
        const panels = document.querySelectorAll('.panel');
        const panelContents = document.querySelectorAll('.panel-content');

        let html = '<strong style="color:#0ff;">Debug Panel</strong><br>';
        html += `<span style="color:#ff0;">Screen:</span> ${window.innerWidth}x${window.innerHeight}<br>`;
        html += `<span style="color:#ff0;">Pages:</span> ${activePages.length} active, index ${currentPageIndex}<br>`;
        html += `<span style="color:#ff0;">Current:</span> ${currentPage ? currentPage.name : 'none'}<br>`;
        html += `<span style="color:#ff0;">Panels:</span> ${panels.length}<br>`;
        html += `<span style="color:#ff0;">Rotation:</span> ${rotationEnabled ? `${rotationInterval}s` : 'off'}${debugPaused ? ' <span style="color:#f00;">(PAUSED)</span>' : ''}<br>`;
        html += `<span style="color:#ff0;">Layout:</span> ${screenDefaultLayout || 'auto'}<br>`;

        // Navigation controls
        html += '<br><div style="display:flex;gap:10px;align-items:center;margin:8px 0;">';
        html += `<button id="debug-prev" style="background:#333;color:#fff;border:1px solid #666;padding:8px 16px;cursor:pointer;border-radius:4px;font-size:16px;" title="Previous page">&larr;</button>`;
        html += `<button id="debug-pause" style="background:${debugPaused ? '#060' : '#333'};color:#fff;border:1px solid #666;padding:8px 16px;cursor:pointer;border-radius:4px;font-size:14px;" title="Pause/Resume rotation">${debugPaused ? '▶ Play' : '⏸ Pause'}</button>`;
        html += `<button id="debug-next" style="background:#333;color:#fff;border:1px solid #666;padding:8px 16px;cursor:pointer;border-radius:4px;font-size:16px;" title="Next page">&rarr;</button>`;
        html += '</div>';

        // Panel dimensions
        if (panelContents.length > 0) {
            html += '<br><strong style="color:#0ff;">Panel Sizes:</strong><br>';
            panelContents.forEach((pc, i) => {
                html += `[${i}] ${pc.clientWidth}x${pc.clientHeight}<br>`;
            });
        }

        debugEl.innerHTML = html;

        // Attach event listeners
        document.getElementById('debug-prev').addEventListener('click', debugPrevPage);
        document.getElementById('debug-next').addEventListener('click', debugNextPage);
        document.getElementById('debug-pause').addEventListener('click', debugTogglePause);
    } else if (debugEl) {
        // Remove debug element when disabled
        debugEl.remove();
        // Resume rotation if it was paused when debug was disabled
        if (debugPaused) {
            debugPaused = false;
            if (rotationEnabled && pages.length > 1) {
                startRotation();
            }
        }
    }
}

function debugPrevPage() {
    const activePages = getActivePages();
    if (activePages.length <= 1) return;

    // Stop current rotation timer
    stopRotation();

    // Go to previous page
    currentPageIndex = (currentPageIndex - 1 + activePages.length) % activePages.length;
    renderCurrentPage();

    // Restart rotation if not paused
    if (!debugPaused && rotationEnabled) {
        startRotation();
    }
}

function debugNextPage() {
    const activePages = getActivePages();
    if (activePages.length <= 1) return;

    // Stop current rotation timer
    stopRotation();

    // Go to next page
    currentPageIndex = (currentPageIndex + 1) % activePages.length;
    renderCurrentPage();

    // Restart rotation if not paused
    if (!debugPaused && rotationEnabled) {
        startRotation();
    }
}

function debugTogglePause() {
    debugPaused = !debugPaused;

    if (debugPaused) {
        // Stop rotation
        stopRotation();
    } else {
        // Resume rotation if enabled
        if (rotationEnabled && pages.length > 1) {
            startRotation();
        }
    }

    // Update display to show new pause state
    updateDebugDisplay();
}

// ============== Layout Resolution ==============

function resolveLayout(layout, contentCount) {
    // No layout = backward compatible auto-detection
    if (!layout) {
        return { type: 'auto', panelCount: Math.min(contentCount, 6) };
    }

    // String = preset name
    if (typeof layout === 'string') {
        const preset = LAYOUT_PRESETS[layout];
        if (preset && Object.keys(preset).length === 0) {
            // 'auto' preset
            return { type: 'auto', panelCount: Math.min(contentCount, 6) };
        }
        return preset ? { type: 'custom', ...preset } : { type: 'auto', panelCount: contentCount };
    }

    // Object = full config (could be LayoutConfig model serialized)
    if (typeof layout === 'object') {
        // Check if it's using a preset
        if (layout.preset) {
            const preset = LAYOUT_PRESETS[layout.preset];
            if (preset) {
                // Merge preset with overrides
                const config = { ...preset };
                Object.keys(layout).forEach(key => {
                    if (layout[key] !== null && layout[key] !== undefined && key !== 'preset') {
                        config[key] = layout[key];
                    }
                });
                return { type: 'custom', ...config };
            }
        }
        return { type: 'custom', ...layout };
    }

    // Fallback
    return { type: 'auto', panelCount: contentCount };
}

function applyScreenLayout(screenEl, layoutConfig, contentCount) {
    // Reset any previous inline styles
    screenEl.style.gridTemplateColumns = '';
    screenEl.style.gridTemplateRows = '';

    if (layoutConfig.type === 'auto') {
        // Backward compatible - use panels-N classes
        screenEl.className = `screen panels-${layoutConfig.panelCount}`;
        return;
    }

    // Custom layout
    screenEl.className = 'screen layout-custom';

    // Apply columns
    if (layoutConfig.columns) {
        const cols = typeof layoutConfig.columns === 'number'
            ? `repeat(${layoutConfig.columns}, 1fr)`
            : layoutConfig.columns;
        screenEl.style.gridTemplateColumns = cols;
    }

    // Apply rows
    if (layoutConfig.rows) {
        const rows = typeof layoutConfig.rows === 'number'
            ? `repeat(${layoutConfig.rows}, 1fr)`
            : layoutConfig.rows;
        screenEl.style.gridTemplateRows = rows;
    } else if (layoutConfig.columns && !layoutConfig.rows) {
        // Auto rows based on content count and column count
        const cols = typeof layoutConfig.columns === 'number'
            ? layoutConfig.columns
            : layoutConfig.columns.split(' ').length;
        const rowCount = Math.ceil(contentCount / cols);
        screenEl.style.gridTemplateRows = `repeat(${rowCount}, 1fr)`;
    }
}

// ============== Page Handling ==============

function handlePagesSync(newPages, rotation) {
    pages = newPages || [];
    currentPageIndex = 0;

    // Update rotation settings
    if (rotation) {
        rotationEnabled = rotation.enabled;
        rotationInterval = rotation.interval || 30;
        screenGap = rotation.gap || '1rem';
        screenBorderRadius = rotation.border_radius || '1rem';
        screenPanelShadow = rotation.panel_shadow || null;
        screenBackgroundColor = rotation.background_color || null;
        screenPanelColor = rotation.panel_color || null;
        screenFontFamily = rotation.font_family || null;
        screenFontColor = rotation.font_color || null;
        screenDefaultLayout = rotation.default_layout || null;
        screenTransition = rotation.transition || 'none';
        screenTransitionDuration = rotation.transition_duration || 500;
        updateHeadHtml(rotation.head_html || null);

        // Apply debug state from server (takes precedence over localStorage)
        if (rotation.debug_enabled !== undefined) {
            debugEnabled = rotation.debug_enabled;
            localStorage.setItem('debugEnabled', debugEnabled ? 'true' : 'false');
            if (debugEnabled) {
                updateDebugDisplay();
            } else {
                // Remove debug panel if disabled
                const debugEl = document.getElementById('debug-info');
                if (debugEl) debugEl.remove();
            }
        }
    }

    // Render current page (no transition on initial load)
    renderCurrentPage();

    // Start/stop rotation based on settings
    if (rotationEnabled && pages.length > 1) {
        startRotation();
    } else {
        stopRotation();
    }
}

function handlePageUpdate(page) {
    if (!page) return;

    // Find existing page by name
    const existingIndex = pages.findIndex(p => p.name === page.name);

    if (existingIndex >= 0) {
        // Update existing page
        pages[existingIndex] = page;
    } else {
        // Add new page at correct position based on display_order
        pages.push(page);
        pages.sort((a, b) => a.display_order - b.display_order);
    }

    // Re-render if viewing the updated page
    const activePages = getActivePages();
    if (activePages.length > 0 && currentPageIndex < activePages.length) {
        const currentPage = activePages[currentPageIndex];
        if (currentPage.name === page.name) {
            renderCurrentPage();
        }
    }

    // Start rotation if we now have multiple pages
    if (rotationEnabled && pages.length > 1) {
        startRotation();
    }
}

function handlePageDelete(pageName) {
    const deletedIndex = pages.findIndex(p => p.name === pageName);
    if (deletedIndex < 0) return;

    pages.splice(deletedIndex, 1);

    // Adjust current index if needed
    if (currentPageIndex >= pages.length) {
        currentPageIndex = Math.max(0, pages.length - 1);
    }

    // Re-render
    renderCurrentPage();

    // Stop rotation if only one page left
    if (pages.length <= 1) {
        stopRotation();
    }
}

function handleRotationUpdate(rotation) {
    if (!rotation) return;

    rotationEnabled = rotation.enabled;
    rotationInterval = rotation.interval || 30;
    screenGap = rotation.gap || '1rem';
    screenBorderRadius = rotation.border_radius || '1rem';
    screenPanelShadow = rotation.panel_shadow || null;
    screenBackgroundColor = rotation.background_color || null;
    screenPanelColor = rotation.panel_color || null;
    screenFontFamily = rotation.font_family || null;
    screenFontColor = rotation.font_color || null;
    screenDefaultLayout = rotation.default_layout || null;
    screenTransition = rotation.transition || 'none';
    screenTransitionDuration = rotation.transition_duration || 500;
    updateHeadHtml(rotation.head_html || null);

    // Re-render to apply new settings
    renderCurrentPage();

    if (rotationEnabled && pages.length > 1) {
        startRotation();
    } else {
        stopRotation();
    }
}

function getActivePages() {
    // Filter out expired pages
    const now = new Date().toISOString();
    return pages.filter(page => !page.expires_at || page.expires_at > now);
}

function renderCurrentPage() {
    const activePages = getActivePages();

    if (activePages.length === 0) {
        // No pages to show
        screenEl.innerHTML = '<div class="panel"><div class="panel-content"><div class="content-text">No content</div></div></div>';
        screenEl.className = 'screen panels-1';
        return;
    }

    // Ensure index is valid
    if (currentPageIndex >= activePages.length) {
        currentPageIndex = 0;
    }

    const page = activePages[currentPageIndex];

    // Determine layout: page override > screen default > auto
    const effectiveLayout = page.layout || screenDefaultLayout || null;

    renderContent(page.content, {
        backgroundColor: page.background_color,
        panelColor: page.panel_color,
        fontFamily: page.font_family,
        fontColor: page.font_color,
        gap: page.gap,  // Page-level gap override (null uses screen default)
        borderRadius: page.border_radius,  // Page-level border radius override
        panelShadow: page.panel_shadow,  // Page-level panel shadow override
        layout: effectiveLayout  // Layout configuration
    });
}

function startRotation() {
    stopRotation(); // Clear any existing timer

    if (!rotationEnabled || pages.length <= 1) return;

    const activePages = getActivePages();
    const currentPage = activePages[currentPageIndex];

    // Use per-page duration if set, otherwise use screen default
    const duration = (currentPage && currentPage.duration) || rotationInterval;

    rotationTimer = setTimeout(() => {
        advanceToNextPage();
    }, duration * 1000);
}

function stopRotation() {
    if (rotationTimer) {
        clearTimeout(rotationTimer);
        rotationTimer = null;
    }
}

function advanceToNextPage() {
    const activePages = getActivePages();

    if (activePages.length <= 1) {
        stopRotation();
        return;
    }

    // Prevent overlapping transitions
    if (isTransitioning) {
        startRotation();
        return;
    }

    // Calculate next page index
    const nextPageIndex = (currentPageIndex + 1) % activePages.length;
    const nextPage = activePages[nextPageIndex];

    // Determine effective transition (page override or screen default)
    const effectiveTransition = nextPage.transition || screenTransition || 'none';
    const effectiveDuration = nextPage.transition_duration || screenTransitionDuration || 500;

    if (effectiveTransition === 'none') {
        // No transition - instant swap
        currentPageIndex = nextPageIndex;
        renderCurrentPage();
        startRotation();
    } else {
        // Animate transition
        transitionToPage(nextPageIndex, effectiveTransition, effectiveDuration);
    }
}

function transitionToPage(nextPageIndex, transitionType, duration) {
    isTransitioning = true;
    const activePages = getActivePages();
    const nextPage = activePages[nextPageIndex];

    // Set CSS variable for duration
    screenEl.style.setProperty('--transition-duration', `${duration}ms`);

    // Capture current content as old content wrapper
    const currentPanels = Array.from(screenEl.children);
    const oldContentWrapper = document.createElement('div');
    oldContentWrapper.className = 'screen__old-content';

    // Copy current grid styles to old content wrapper (use getComputedStyle for CSS class-based layouts)
    const computedStyle = getComputedStyle(screenEl);
    oldContentWrapper.style.gridTemplateColumns = screenEl.style.gridTemplateColumns || computedStyle.gridTemplateColumns;
    oldContentWrapper.style.gridTemplateRows = screenEl.style.gridTemplateRows || computedStyle.gridTemplateRows;
    oldContentWrapper.style.gap = computedStyle.gap;

    // Move current panels to old wrapper
    currentPanels.forEach(panel => {
        oldContentWrapper.appendChild(panel);
    });

    // Add transitioning class to screen
    screenEl.classList.add('screen--transitioning');

    // Re-insert old content wrapper
    screenEl.appendChild(oldContentWrapper);

    // Update page index and render new content
    currentPageIndex = nextPageIndex;

    // Determine layout for new page
    const effectiveLayout = nextPage.layout || screenDefaultLayout || null;

    // Create new content elements (similar to renderContent but creating a wrapper)
    const newContentWrapper = document.createElement('div');
    newContentWrapper.className = 'screen__new-content';

    // Make it a grid to give panels proper dimensions
    newContentWrapper.style.display = 'grid';
    newContentWrapper.style.width = '100%';
    newContentWrapper.style.height = '100%';

    // Apply gap/padding
    const effectiveGap = nextPage.gap || screenGap;
    screenEl.style.gap = effectiveGap;
    screenEl.style.padding = effectiveGap;

    // Apply background
    const effectiveBackgroundColor = nextPage.background_color || screenBackgroundColor;
    if (effectiveBackgroundColor) {
        document.body.style.background = effectiveBackgroundColor;
        screenEl.style.background = effectiveBackgroundColor;
    }

    // Apply font styles to screen (page overrides screen defaults)
    const effectiveFontFamily = nextPage.font_family || screenFontFamily;
    const effectiveFontColor = nextPage.font_color || screenFontColor;
    if (effectiveFontFamily) {
        screenEl.style.fontFamily = effectiveFontFamily;
    } else {
        screenEl.style.fontFamily = '';
    }
    if (effectiveFontColor) {
        screenEl.style.color = effectiveFontColor;
    } else {
        screenEl.style.color = '';
    }

    // Resolve and apply layout
    const layoutConfig = resolveLayout(effectiveLayout, nextPage.content.length);
    applyScreenLayout(screenEl, layoutConfig, nextPage.content.length);

    // Copy grid template to new content wrapper
    newContentWrapper.style.gridTemplateColumns = screenEl.style.gridTemplateColumns || getComputedStyle(screenEl).gridTemplateColumns;
    newContentWrapper.style.gridTemplateRows = screenEl.style.gridTemplateRows || getComputedStyle(screenEl).gridTemplateRows;
    newContentWrapper.style.gap = effectiveGap;

    // Apply font styles to wrapper so panels inherit correctly
    if (effectiveFontFamily) {
        newContentWrapper.style.fontFamily = effectiveFontFamily;
    }
    if (effectiveFontColor) {
        newContentWrapper.style.color = effectiveFontColor;
    }

    // Build new panels inside wrapper
    buildPanelsInWrapper(newContentWrapper, nextPage, layoutConfig);

    // Insert new content wrapper - hidden with opacity 0 for pre-scaling
    // (opacity 0 maintains layout dimensions while being invisible)
    newContentWrapper.style.opacity = '0';
    screenEl.appendChild(newContentWrapper);

    // Use double requestAnimationFrame to ensure layout is calculated before scaling
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            // Auto-scale while content is hidden (opacity 0 maintains dimensions)
            autoScaleText();
            autoScaleMarkdown();

            // Apply animation classes - fade-in starts from opacity 0, so it takes over smoothly
            // For slide, we need to remove opacity first since slide doesn't animate opacity
            if (transitionType === 'fade') {
                // Remove inline opacity - animation will control it from 0 to 1
                newContentWrapper.style.opacity = '';
                oldContentWrapper.classList.add('transition-fade-out');
                newContentWrapper.classList.add('transition-fade-in');
            } else if (transitionType === 'slide-left') {
                // For slide, content should be visible, just positioned off-screen
                newContentWrapper.style.opacity = '1';
                oldContentWrapper.classList.add('transition-slide-out-left');
                newContentWrapper.classList.add('transition-slide-in-right');
            }

            // After animation completes, clean up
            // (setTimeout starts here so it counts from when animations actually begin)
            setTimeout(() => {
                // Remove old content wrapper
                oldContentWrapper.remove();

                // Move new panels out of wrapper to be direct children of screen
                const newPanels = Array.from(newContentWrapper.children);
                newPanels.forEach(panel => {
                    screenEl.appendChild(panel);
                });
                newContentWrapper.remove();

                // Remove transitioning class
                screenEl.classList.remove('screen--transitioning');

                isTransitioning = false;

                // Schedule next rotation
                startRotation();
            }, duration);
        });
    });
}

function buildPanelsInWrapper(wrapper, page, layoutConfig) {
    const content = page.content;
    const effectiveBorderRadius = page.border_radius || screenBorderRadius;
    const effectivePanelShadow = page.panel_shadow || screenPanelShadow;
    const effectivePanelColor = page.panel_color || screenPanelColor;
    const effectiveFontFamily = page.font_family || screenFontFamily;
    const effectiveFontColor = page.font_color || screenFontColor;

    const headerRows = layoutConfig.header_rows || 0;
    const footerRows = layoutConfig.footer_rows || 0;
    const totalItems = content.length;

    content.forEach((item, index) => {
        const panel = document.createElement('div');
        panel.className = 'panel';

        panel.style.borderRadius = effectiveBorderRadius;

        if (item.panel_shadow !== undefined && item.panel_shadow !== null) {
            panel.style.boxShadow = item.panel_shadow === 'none' ? 'none' : item.panel_shadow;
        } else if (effectivePanelShadow) {
            panel.style.boxShadow = effectivePanelShadow;
        }

        if (item.panel_color) {
            panel.style.background = item.panel_color;
        } else if (effectivePanelColor) {
            panel.style.background = effectivePanelColor;
        }

        if (item.font_family) {
            panel.style.fontFamily = item.font_family;
        }
        if (item.font_color) {
            panel.style.color = item.font_color;
        }

        if (item.grid_column) {
            panel.style.gridColumn = item.grid_column;
        } else if (layoutConfig.type === 'custom') {
            if (headerRows > 0 && index < headerRows) {
                panel.style.gridColumn = '1 / -1';
            } else if (footerRows > 0 && index >= totalItems - footerRows) {
                panel.style.gridColumn = '1 / -1';
            }
        }
        if (item.grid_row) {
            panel.style.gridRow = item.grid_row;
        }

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'panel-content';

        const isCoverMode = (item.type === 'image' || item.type === 'video') &&
                           (item.image_mode === 'cover');
        if (isCoverMode) {
            panel.classList.add('panel-cover');
        }

        switch (item.type) {
            case 'text':
                contentWrapper.appendChild(createTextElement(item.value, item.wrap));
                break;
            case 'image':
                contentWrapper.appendChild(createImageElement(item.url, item.image_mode));
                break;
            case 'video':
                contentWrapper.appendChild(createVideoElement(item.url, item));
                break;
            case 'markdown':
                contentWrapper.appendChild(createMarkdownElement(item.value, content.length));
                break;
            case 'widget':
                const widgetEl = createWidgetElement(item, contentWrapper);
                if (widgetEl) {
                    contentWrapper.appendChild(widgetEl);
                    activeWidgets.push(widgetEl);
                }
                break;
            default:
                contentWrapper.appendChild(createTextElement(item.value || item.url || '', content.length));
        }

        panel.appendChild(contentWrapper);
        wrapper.appendChild(panel);
    });
}

function renderContent(content, styles = {}) {
    const { backgroundColor, panelColor, fontFamily, fontColor, gap, borderRadius, panelShadow, layout } = styles;

    // Clean up any active widgets before clearing content
    activeWidgets.forEach(widget => {
        try {
            destroyWidget(widget);
        } catch (e) {
            console.error('Error destroying widget:', e);
        }
    });
    activeWidgets = [];

    // Clear existing content
    screenEl.innerHTML = '';

    // Apply gap (page-level override or screen-level default)
    const effectiveGap = gap || screenGap;
    screenEl.style.gap = effectiveGap;
    screenEl.style.padding = effectiveGap;  // Match padding to gap for tiling WM feel

    // Calculate effective border radius
    const effectiveBorderRadius = borderRadius || screenBorderRadius;

    // Calculate effective panel shadow
    const effectivePanelShadow = panelShadow || screenPanelShadow;

    // Calculate effective colors/fonts (page overrides screen defaults)
    const effectiveBackgroundColor = backgroundColor || screenBackgroundColor;
    const effectivePanelColor = panelColor || screenPanelColor;
    const effectiveFontFamily = fontFamily || screenFontFamily;
    const effectiveFontColor = fontColor || screenFontColor;

    // Apply background color (use 'background' to support gradients)
    if (effectiveBackgroundColor) {
        document.body.style.background = effectiveBackgroundColor;
        screenEl.style.background = effectiveBackgroundColor;
    } else {
        document.body.style.background = '';
        screenEl.style.background = '';
    }

    // Apply default font styles to screen
    if (effectiveFontFamily) {
        screenEl.style.fontFamily = effectiveFontFamily;
    } else {
        screenEl.style.fontFamily = '';
    }
    if (effectiveFontColor) {
        screenEl.style.color = effectiveFontColor;
    } else {
        screenEl.style.color = '';
    }

    // Resolve and apply layout
    const layoutConfig = resolveLayout(layout, content.length);
    applyScreenLayout(screenEl, layoutConfig, content.length);

    // Extract header/footer row counts for auto-spanning
    const headerRows = layoutConfig.header_rows || 0;
    const footerRows = layoutConfig.footer_rows || 0;
    const totalItems = content.length;

    // Create panels for each content item
    content.forEach((item, index) => {
        const panel = document.createElement('div');
        panel.className = 'panel';

        // Apply border radius
        panel.style.borderRadius = effectiveBorderRadius;

        // Apply panel shadow (per-item override takes precedence)
        // Use "none" to explicitly disable shadow on a panel
        if (item.panel_shadow !== undefined && item.panel_shadow !== null) {
            panel.style.boxShadow = item.panel_shadow === 'none' ? 'none' : item.panel_shadow;
        } else if (effectivePanelShadow) {
            panel.style.boxShadow = effectivePanelShadow;
        }

        // Apply panel color (per-item override takes precedence, then page, then screen default)
        // Use 'background' to support gradients
        if (item.panel_color) {
            panel.style.background = item.panel_color;
        } else if (effectivePanelColor) {
            panel.style.background = effectivePanelColor;
        }

        // Apply per-panel font overrides
        if (item.font_family) {
            panel.style.fontFamily = item.font_family;
        }
        if (item.font_color) {
            panel.style.color = item.font_color;
        }

        // Apply per-panel grid positioning
        if (item.grid_column) {
            panel.style.gridColumn = item.grid_column;
        } else if (layoutConfig.type === 'custom') {
            // Auto-span header and footer rows (only if custom layout)
            if (headerRows > 0 && index < headerRows) {
                panel.style.gridColumn = '1 / -1';  // Full width
            } else if (footerRows > 0 && index >= totalItems - footerRows) {
                panel.style.gridColumn = '1 / -1';  // Full width
            }
        }
        if (item.grid_row) {
            panel.style.gridRow = item.grid_row;
        }

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'panel-content';

        // Check if this is a cover mode media item
        const isCoverMode = (item.type === 'image' || item.type === 'video') &&
                           (item.image_mode === 'cover');
        if (isCoverMode) {
            panel.classList.add('panel-cover');
        }

        switch (item.type) {
            case 'text':
                contentWrapper.appendChild(createTextElement(item.value, item.wrap));
                break;
            case 'image':
                contentWrapper.appendChild(createImageElement(item.url, item.image_mode));
                break;
            case 'video':
                contentWrapper.appendChild(createVideoElement(item.url, item));
                break;
            case 'markdown':
                contentWrapper.appendChild(createMarkdownElement(item.value, content.length));
                break;
            case 'widget':
                const widgetEl = createWidgetElement(item, contentWrapper);
                if (widgetEl) {
                    contentWrapper.appendChild(widgetEl);
                    activeWidgets.push(widgetEl);
                }
                break;
            default:
                contentWrapper.appendChild(createTextElement(item.value || item.url || '', content.length));
        }

        panel.appendChild(contentWrapper);
        screenEl.appendChild(panel);
    });

    // Auto-scale text and markdown after render
    requestAnimationFrame(() => {
        autoScaleText();
        autoScaleMarkdown();
        // Update debug display if enabled
        if (debugEnabled) {
            updateDebugDisplay();
        }
    });
}

function createTextElement(text, wrap) {
    const el = document.createElement('div');
    el.className = 'content-text auto-scale';
    el.textContent = text;
    // Default wrap to true for text (allows larger text by using multiple lines)
    const shouldWrap = wrap !== false;
    el.dataset.wrap = shouldWrap ? 'true' : 'false';
    if (!shouldWrap) {
        el.style.whiteSpace = 'nowrap';
    }
    return el;
}

function createImageElement(url, imageMode) {
    const el = document.createElement('img');
    el.className = 'content-image';
    el.src = url;
    el.alt = 'Content image';

    // Apply image mode class
    const mode = imageMode || 'contain';
    el.classList.add(`mode-${mode}`);

    el.onerror = () => {
        el.style.display = 'none';
        const fallback = document.createElement('div');
        fallback.className = 'content-text';
        fallback.textContent = 'Failed to load image';
        fallback.style.color = '#e74c3c';
        el.parentNode.appendChild(fallback);
    };
    return el;
}

function createVideoElement(url, options = {}) {
    const el = document.createElement('video');
    el.className = 'content-video';
    el.src = url;

    // Apply video options (defaults: autoplay, loop, muted)
    if (options.autoplay !== false) {
        el.autoplay = true;
    }
    if (options.loop !== false) {
        el.loop = true;
    }
    if (options.muted !== false) {
        el.muted = true;
    }

    // Required for autoplay in most browsers
    el.playsInline = true;

    // Apply image mode for sizing (reuse same modes)
    const mode = options.image_mode || 'contain';
    el.classList.add(`mode-${mode}`);

    el.onerror = () => {
        el.style.display = 'none';
        const fallback = document.createElement('div');
        fallback.className = 'content-text';
        fallback.textContent = 'Failed to load video';
        fallback.style.color = '#e74c3c';
        el.parentNode.appendChild(fallback);
    };

    return el;
}

function createMarkdownElement(markdown, panelCount) {
    const el = document.createElement('div');
    el.className = 'content-markdown auto-scale-markdown';

    // Parse markdown using marked.js
    let html;
    if (typeof marked !== 'undefined') {
        html = marked.parse(markdown);
    } else {
        // Fallback: simple markdown parsing
        html = simpleMarkdown(markdown);
    }

    // Sanitize HTML to prevent XSS attacks
    if (typeof DOMPurify !== 'undefined') {
        el.innerHTML = DOMPurify.sanitize(html);
    } else {
        // Fallback: strip all tags if DOMPurify not loaded
        el.textContent = html.replace(/<[^>]*>/g, '');
    }

    return el;
}

function createWidgetElement(item, container) {
    const widgetType = item.widget_type;
    const widgetConfig = item.widget_config || {};

    if (!widgetType) {
        console.error('Widget item missing widget_type');
        const fallback = document.createElement('div');
        fallback.className = 'content-text';
        fallback.textContent = 'Widget: missing type';
        fallback.style.color = '#e74c3c';
        return fallback;
    }

    try {
        const widget = createWidget(widgetType, widgetConfig, container);
        if (!widget) {
            throw new Error(`Unknown widget type: ${widgetType}`);
        }
        return widget;
    } catch (error) {
        console.error(`Error creating widget '${widgetType}':`, error);
        const fallback = document.createElement('div');
        fallback.className = 'content-text';
        fallback.innerHTML = `<div style="text-align: center; color: #e74c3c;">
            <div style="font-size: 2rem;">⚠</div>
            <div>Widget error: ${widgetType}</div>
            <div style="font-size: 0.8em; opacity: 0.7;">${error.message}</div>
        </div>`;
        return fallback;
    }
}

function simpleMarkdown(text) {
    // Very basic markdown parsing as fallback
    return text
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

function autoScaleText() {
    const elements = document.querySelectorAll('.auto-scale');

    elements.forEach(el => {
        const parent = el.closest('.panel-content');
        if (!parent) return;

        const maxWidth = Math.floor(parent.clientWidth * 0.95);
        const maxHeight = Math.floor(parent.clientHeight * 0.95);

        const shouldWrap = el.dataset.wrap === 'true';

        // For wrapping text, constrain width so text can wrap at word boundaries
        if (shouldWrap) {
            el.style.width = `${maxWidth}px`;
            el.style.whiteSpace = 'normal';
            el.style.wordWrap = 'normal';
            el.style.overflowWrap = 'normal';
        } else {
            el.style.width = '';
            el.style.whiteSpace = 'nowrap';
        }

        // Binary search for optimal font size
        let minSize = 16;
        let maxSize = 500;
        let optimalSize = minSize;

        while (maxSize - minSize > 2) {
            const midSize = Math.floor((minSize + maxSize) / 2);
            el.style.fontSize = `${midSize}px`;

            // For wrapped text, check scrollHeight fits maxHeight
            // For non-wrapped, check both dimensions
            // Add 1px tolerance for browser rounding differences
            const fits = shouldWrap
                ? el.scrollHeight <= maxHeight + 1 && el.scrollWidth <= maxWidth + 1
                : el.scrollWidth <= maxWidth + 1 && el.scrollHeight <= maxHeight + 1;

            if (fits) {
                optimalSize = midSize;
                minSize = midSize;
            } else {
                maxSize = midSize;
            }
        }

        el.style.fontSize = `${optimalSize}px`;
    });
}

function autoScaleMarkdown() {
    const elements = document.querySelectorAll('.auto-scale-markdown');

    elements.forEach(el => {
        const parent = el.closest('.panel-content');
        if (!parent) return;

        // Reset any previous scaling
        el.style.transform = '';
        el.style.width = '';
        el.style.height = '';

        const maxWidth = parent.clientWidth * 0.9;
        const maxHeight = parent.clientHeight * 0.9;

        // Get natural size of markdown content
        const naturalWidth = el.scrollWidth;
        const naturalHeight = el.scrollHeight;

        // Calculate scale factor to fit both dimensions
        const scaleX = maxWidth / naturalWidth;
        const scaleY = maxHeight / naturalHeight;
        const scale = Math.min(scaleX, scaleY, 3); // Cap at 3x to avoid huge text

        if (scale !== 1) {
            el.style.transform = `scale(${scale})`;
        }
    });
}

// Re-scale on window resize
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        autoScaleText();
        autoScaleMarkdown();
    }, 100);
});

// Periodic check for expired pages (client-side fallback)
setInterval(() => {
    if (pages.length === 0) return;

    const activePages = getActivePages();
    const expiredCount = pages.length - activePages.length;

    if (expiredCount > 0) {
        // Remove expired pages from local state
        pages = activePages;

        // Adjust current index if needed
        if (currentPageIndex >= pages.length) {
            currentPageIndex = Math.max(0, pages.length - 1);
        }

        // Re-render current page
        renderCurrentPage();

        // Update rotation
        if (pages.length <= 1) {
            stopRotation();
        }
    }
}, 1000); // Check every second
