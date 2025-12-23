// Import widget system
import { createWidget, destroyWidget } from './widgets/registry.js';
import './widgets/clock.js';  // Register clock widget

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

// Debug state
let debugEnabled = false;

// Active widget elements for cleanup
let activeWidgets = [];

// Initialize
connect();

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
                    panelShadow: data.panel_shadow
                });
                break;

            case 'reload':
                // Force reload, bypassing cache
                location.reload(true);
                break;

            case 'debug':
                // Toggle debug mode
                debugEnabled = data.enabled;
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

function updateDebugDisplay() {
    const debugEl = document.getElementById('debug-info');
    if (debugEnabled) {
        // Debug will be populated on next render
        renderCurrentPage();
    } else if (debugEl) {
        // Remove debug element when disabled
        debugEl.remove();
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
        updateHeadHtml(rotation.head_html || null);
    }

    // Render current page
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

    renderContent(page.content, {
        backgroundColor: page.background_color,
        panelColor: page.panel_color,
        fontFamily: page.font_family,
        fontColor: page.font_color,
        gap: page.gap,  // Page-level gap override (null uses screen default)
        borderRadius: page.border_radius,  // Page-level border radius override
        panelShadow: page.panel_shadow  // Page-level panel shadow override
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

    // Move to next page
    currentPageIndex = (currentPageIndex + 1) % activePages.length;

    // Render the new page
    renderCurrentPage();

    // Schedule next rotation
    startRotation();
}

function renderContent(content, styles = {}) {
    const { backgroundColor, panelColor, fontFamily, fontColor, gap, borderRadius, panelShadow } = styles;

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

    // Update grid class based on panel count
    screenEl.className = `screen panels-${Math.min(content.length, 6)}`;

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
    if (typeof marked !== 'undefined') {
        el.innerHTML = marked.parse(markdown);
    } else {
        // Fallback: simple markdown parsing
        el.innerHTML = simpleMarkdown(markdown);
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

        // DEBUG: Show dimensions on screen if debug mode is enabled
        let debugEl = document.getElementById('debug-info');
        if (debugEnabled) {
            if (!debugEl) {
                debugEl = document.createElement('div');
                debugEl.id = 'debug-info';
                debugEl.style.cssText = 'position:fixed;top:10px;left:10px;background:rgba(0,0,0,0.8);color:#0f0;padding:15px;z-index:9999;font-size:14px;font-family:monospace;border-radius:8px;max-width:400px;';
                document.body.appendChild(debugEl);
            }
            const textContent = el.textContent.substring(0, 30);
            debugEl.innerHTML = `<strong>Debug Info</strong><br>parentW: ${parent.clientWidth}, parentH: ${parent.clientHeight}<br>maxW: ${maxWidth}, maxH: ${maxHeight}<br>panelCount: ${document.querySelectorAll('.panel').length}<br>text: "${textContent}"<br>scrollW: ${el.scrollWidth}, scrollH: ${el.scrollHeight}<br>wrap: ${el.dataset.wrap}`;
        }

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
        let debugLog = [];

        while (maxSize - minSize > 2) {
            const midSize = Math.floor((minSize + maxSize) / 2);
            el.style.fontSize = `${midSize}px`;

            // For wrapped text, check scrollHeight fits maxHeight
            // For non-wrapped, check both dimensions
            // Add 1px tolerance for browser rounding differences
            const fits = shouldWrap
                ? el.scrollHeight <= maxHeight + 1 && el.scrollWidth <= maxWidth + 1
                : el.scrollWidth <= maxWidth + 1 && el.scrollHeight <= maxHeight + 1;

            // DEBUG: Log first few iterations
            if (debugEnabled && debugLog.length < 3) {
                debugLog.push(`${midSize}px: ${el.scrollWidth}x${el.scrollHeight} fits=${fits}`);
            }

            if (fits) {
                optimalSize = midSize;
                minSize = midSize;
            } else {
                maxSize = midSize;
            }
        }

        // DEBUG: Show binary search progress and final font size
        if (debugEnabled && debugEl) {
            debugEl.innerHTML += `<br>search: ${debugLog.join(' | ')}`;
            debugEl.innerHTML += `<br>fontSize: ${optimalSize}px`;
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
