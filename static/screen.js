// Extract screen ID from URL
const pathParts = window.location.pathname.split('/');
const screenId = pathParts[pathParts.length - 1];

// WebSocket connection
let ws = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;
const reconnectDelay = 1000;

// DOM elements
const screenEl = document.getElementById('screen');
const statusEl = document.getElementById('connection-status');

// Initialize
connect();

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${screenId}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('Connected to screen');
        reconnectAttempts = 0;
        showStatus('connected', 'Connected');
        setTimeout(() => hideStatus(), 2000);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
            renderContent(data.content, {
                backgroundColor: data.background_color,
                panelColor: data.panel_color,
                fontFamily: data.font_family,
                fontColor: data.font_color
            });
        } else if (data.type === 'reload') {
            // Force reload, bypassing cache
            location.reload(true);
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
    if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const delay = reconnectDelay * Math.min(reconnectAttempts, 5);
        showStatus('reconnecting', `Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`);
        setTimeout(connect, delay);
    } else {
        showStatus('disconnected', 'Connection lost. Refresh to retry.');
    }
}

function showStatus(type, message) {
    statusEl.className = `connection-status visible ${type}`;
    statusEl.textContent = message;
}

function hideStatus() {
    statusEl.classList.remove('visible');
}

function renderContent(content, styles = {}) {
    const { backgroundColor, panelColor, fontFamily, fontColor } = styles;

    // Clear existing content
    screenEl.innerHTML = '';

    // Apply background color
    if (backgroundColor) {
        document.body.style.backgroundColor = backgroundColor;
        screenEl.style.backgroundColor = backgroundColor;
    } else {
        document.body.style.backgroundColor = '';
        screenEl.style.backgroundColor = '';
    }

    // Apply default font styles to screen
    if (fontFamily) {
        screenEl.style.fontFamily = fontFamily;
    } else {
        screenEl.style.fontFamily = '';
    }
    if (fontColor) {
        screenEl.style.color = fontColor;
    } else {
        screenEl.style.color = '';
    }

    // Update grid class based on panel count
    screenEl.className = `screen panels-${Math.min(content.length, 6)}`;

    // Create panels for each content item
    content.forEach((item, index) => {
        const panel = document.createElement('div');
        panel.className = 'panel';

        // Apply panel color (per-item override takes precedence over default)
        if (item.color) {
            panel.style.backgroundColor = item.color;
        } else if (panelColor) {
            panel.style.backgroundColor = panelColor;
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

        const maxWidth = parent.clientWidth * 0.95;
        const maxHeight = parent.clientHeight * 0.95;
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
            const fits = shouldWrap
                ? el.scrollHeight <= maxHeight && el.scrollWidth <= maxWidth
                : el.scrollWidth <= maxWidth && el.scrollHeight <= maxHeight;

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
