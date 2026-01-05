/**
 * RSS Widget - Display RSS feed items
 *
 * Fetches RSS feeds via server proxy and displays configurable number of items.
 *
 * Configuration options:
 * - url: string (required) - RSS feed URL
 * - max_items: number (default: 5) - Maximum items to display
 * - show_description: boolean (default: false) - Show item description/body
 * - show_date: boolean (default: true) - Show publication date
 * - show_image: boolean (default: false) - Show item images if available
 * - title_override: string (optional) - Override the feed title
 * - refresh_interval: number (default: 300000) - Refresh interval in ms (5 min default)
 * - date_format: 'relative' | 'short' | 'long' (default: 'relative')
 */

import { registerWidget, calculateScaleFactor } from './registry.js';

// Cache for RSS feed data to avoid refetching on every page rotation
// Key: feed URL, Value: { data: feedData, timestamp: Date.now() }
const feedCache = new Map();

const RssWidget = {
    name: 'rss',
    version: '1.0.0',
    author: 'built-in',

    configSchema: {
        url: { required: true },
        max_items: { default: 5 },
        show_description: { default: false },
        show_date: { default: true },
        show_image: { default: false },
        title_override: { default: null },
        refresh_interval: { default: 300000 },
        date_format: { enum: ['relative', 'short', 'long'], default: 'relative' }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-rss';
        wrapper.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            font-family: inherit;
            color: inherit;
            box-sizing: border-box;
            overflow: hidden;
        `;

        // Show loading state
        wrapper.innerHTML = '<div style="opacity: 0.5;">Loading feed...</div>';

        // Store feed data for resize handler
        wrapper._feedData = null;
        wrapper._config = config;

        // Fetch and render
        this._fetchAndRender(wrapper, config);

        // Set up auto-refresh (force refresh when interval fires)
        if (config.refresh_interval > 0) {
            wrapper._refreshIntervalId = setInterval(() => {
                this._fetchAndRender(wrapper, config, true);
            }, config.refresh_interval);
        }

        return wrapper;
    },

    async _fetchAndRender(wrapper, config, forceRefresh = false) {
        try {
            // Use 0 as refresh interval to force a fresh fetch
            const refreshInterval = forceRefresh ? 0 : config.refresh_interval;
            const feed = await this._fetchFeed(config.url, refreshInterval);
            wrapper._feedData = feed;
            wrapper.innerHTML = '';

            requestAnimationFrame(() => {
                const scaleFactor = calculateScaleFactor(wrapper);
                this._render(wrapper, feed, config, scaleFactor);

                // Set up resize handler (only once)
                if (!wrapper._resizeHandler) {
                    wrapper._resizeHandler = () => {
                        if (wrapper._feedData) {
                            wrapper.innerHTML = '';
                            const newScaleFactor = calculateScaleFactor(wrapper);
                            this._render(wrapper, wrapper._feedData, wrapper._config, newScaleFactor);
                        }
                    };
                    window.addEventListener('resize', wrapper._resizeHandler);
                }
            });
        } catch (error) {
            console.error('RSS fetch error:', error);
            wrapper.innerHTML = `<div style="color: #ef4444; text-align: center;">
                <div style="font-size: 1.5em;">⚠</div>
                <div>Failed to load feed</div>
                <div style="font-size: 0.8em; opacity: 0.7;">${error.message}</div>
            </div>`;
        }
    },

    async _fetchFeed(url, refreshInterval) {
        // Check cache first
        const cached = feedCache.get(url);
        if (cached) {
            const age = Date.now() - cached.timestamp;
            if (age < refreshInterval) {
                // Cache is still fresh, use it
                return cached.data;
            }
        }

        // Use server proxy to avoid CORS issues
        const proxyUrl = `/api/v1/proxy/rss?url=${encodeURIComponent(url)}`;
        const response = await fetch(proxyUrl);

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();

        // Store in cache
        feedCache.set(url, {
            data: data,
            timestamp: Date.now()
        });

        return data;
    },

    _render(wrapper, feed, config, scaleFactor) {
        if (config.max_items === 1) {
            this._renderSingle(wrapper, feed, config, scaleFactor);
        } else {
            this._renderList(wrapper, feed, config, scaleFactor);
        }
    },

    _renderSingle(wrapper, feed, config, scaleFactor) {
        const item = feed.items[0];
        if (!item) {
            wrapper.innerHTML = '<div style="opacity: 0.5;">No items in feed</div>';
            return;
        }

        // Base sizes for single item display
        const titleSize = Math.round(35 * scaleFactor);
        const headlineSize = Math.round(50 * scaleFactor);
        const descSize = Math.round(22 * scaleFactor);
        const dateSize = Math.round(18 * scaleFactor);
        const gapSize = Math.round(12 * scaleFactor);
        const imageSize = Math.round(150 * scaleFactor);

        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: ${gapSize}px;
            padding: ${gapSize}px;
            text-align: center;
            max-width: 95%;
        `;

        // Feed title
        const feedTitle = config.title_override || feed.title;
        if (feedTitle) {
            const titleEl = document.createElement('div');
            titleEl.style.cssText = `
                font-size: ${titleSize}px;
                font-weight: 600;
                opacity: 0.7;
            `;
            titleEl.textContent = feedTitle;
            container.appendChild(titleEl);
        }

        // Image (if enabled and available)
        if (config.show_image && item.image) {
            const imgEl = document.createElement('img');
            imgEl.src = item.image;
            imgEl.alt = item.title || 'Article image';
            imgEl.style.cssText = `
                max-width: ${imageSize}px;
                max-height: ${imageSize}px;
                object-fit: cover;
                border-radius: ${Math.round(8 * scaleFactor)}px;
            `;
            imgEl.onerror = () => { imgEl.style.display = 'none'; };
            container.appendChild(imgEl);
        }

        // Item title (headline)
        const headlineEl = document.createElement('div');
        headlineEl.style.cssText = `
            font-size: ${headlineSize}px;
            font-weight: 500;
            line-height: 1.2;
        `;
        headlineEl.textContent = item.title;
        container.appendChild(headlineEl);

        // Description
        if (config.show_description && item.description) {
            const descEl = document.createElement('div');
            descEl.style.cssText = `
                font-size: ${descSize}px;
                opacity: 0.8;
                line-height: 1.4;
                max-height: ${descSize * 4}px;
                overflow: hidden;
            `;
            descEl.textContent = this._stripHtml(item.description);
            container.appendChild(descEl);
        }

        // Date
        if (config.show_date && item.pubDate) {
            const dateEl = document.createElement('div');
            dateEl.style.cssText = `
                font-size: ${dateSize}px;
                opacity: 0.5;
            `;
            dateEl.textContent = this._formatDate(item.pubDate, config.date_format);
            container.appendChild(dateEl);
        }

        wrapper.appendChild(container);
    },

    _renderList(wrapper, feed, config, scaleFactor) {
        const items = feed.items.slice(0, config.max_items);
        if (items.length === 0) {
            wrapper.innerHTML = '<div style="opacity: 0.5;">No items in feed</div>';
            return;
        }

        // Base sizes for list view
        const titleSize = Math.round(28 * scaleFactor);
        const itemTitleSize = Math.round(18 * scaleFactor);
        const descSize = Math.round(14 * scaleFactor);
        const dateSize = Math.round(12 * scaleFactor);
        const gapSize = Math.round(8 * scaleFactor);
        const itemGap = Math.round(4 * scaleFactor);
        const thumbWidth = Math.round(80 * scaleFactor);
        const thumbHeight = Math.round(60 * scaleFactor);

        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            padding: ${gapSize}px;
            box-sizing: border-box;
            overflow: hidden;
        `;

        // Feed title
        const feedTitle = config.title_override || feed.title;
        if (feedTitle) {
            const titleEl = document.createElement('div');
            titleEl.style.cssText = `
                font-size: ${titleSize}px;
                font-weight: 600;
                margin-bottom: ${gapSize}px;
                flex-shrink: 0;
            `;
            titleEl.textContent = feedTitle;
            container.appendChild(titleEl);
        }

        // Items list
        const listEl = document.createElement('div');
        listEl.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: ${gapSize}px;
            overflow: hidden;
            flex: 1;
        `;

        items.forEach((item, index) => {
            const itemEl = document.createElement('div');
            itemEl.style.cssText = `
                display: flex;
                flex-direction: row;
                gap: ${gapSize}px;
                padding-bottom: ${gapSize}px;
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
                align-items: center;
            `;

            // Thumbnail (if enabled and available)
            if (config.show_image && item.image) {
                const imgEl = document.createElement('img');
                imgEl.src = item.image;
                imgEl.alt = '';
                imgEl.style.cssText = `
                    width: ${thumbWidth}px;
                    height: ${thumbHeight}px;
                    object-fit: cover;
                    border-radius: ${Math.round(4 * scaleFactor)}px;
                    flex-shrink: 0;
                `;
                imgEl.onerror = () => { imgEl.style.display = 'none'; };
                itemEl.appendChild(imgEl);
            }

            // Text content container
            const textContainer = document.createElement('div');
            textContainer.style.cssText = `
                display: flex;
                flex-direction: column;
                gap: ${itemGap}px;
                flex: 1;
                min-width: 0;
            `;

            // Item title
            const itemTitleEl = document.createElement('div');
            itemTitleEl.style.cssText = `
                font-size: ${itemTitleSize}px;
                font-weight: 500;
                line-height: 1.3;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            `;
            itemTitleEl.textContent = item.title;
            textContainer.appendChild(itemTitleEl);

            // Description (if enabled)
            if (config.show_description && item.description) {
                const descEl = document.createElement('div');
                descEl.style.cssText = `
                    font-size: ${descSize}px;
                    opacity: 0.7;
                    line-height: 1.3;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                `;
                descEl.textContent = this._stripHtml(item.description);
                textContainer.appendChild(descEl);
            }

            // Date
            if (config.show_date && item.pubDate) {
                const dateEl = document.createElement('div');
                dateEl.style.cssText = `
                    font-size: ${dateSize}px;
                    opacity: 0.5;
                `;
                dateEl.textContent = this._formatDate(item.pubDate, config.date_format);
                textContainer.appendChild(dateEl);
            }

            itemEl.appendChild(textContainer);
            listEl.appendChild(itemEl);
        });

        container.appendChild(listEl);
        wrapper.appendChild(container);
    },

    _stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    },

    _formatDate(dateStr, format) {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;

        if (format === 'relative') {
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);

            if (minutes < 1) return 'Just now';
            if (minutes < 60) return `${minutes}m ago`;
            if (hours < 24) return `${hours}h ago`;
            if (days < 7) return `${days}d ago`;
            return date.toLocaleDateString();
        }

        if (format === 'short') {
            return date.toLocaleDateString();
        }

        // long format
        return date.toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    update(element, config) {
        this.destroy(element);
        const parent = element.parentNode;
        const newElement = this.create(parent, config);
        parent.replaceChild(newElement, element);
        return newElement;
    },

    destroy(element) {
        if (element && element._refreshIntervalId) {
            clearInterval(element._refreshIntervalId);
            element._refreshIntervalId = null;
        }
        if (element && element._resizeHandler) {
            window.removeEventListener('resize', element._resizeHandler);
            element._resizeHandler = null;
        }
    }
};

registerWidget('rss', RssWidget);

export default RssWidget;
