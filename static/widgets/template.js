/**
 * Widget Template - Scaffolding for creating new widgets
 *
 * This file serves as a comprehensive template for building new Big Beautiful Screens widgets.
 * Copy this file, rename it to your-widget.js, and modify as needed.
 *
 * IMPORTANT: After creating your widget, you must import it in screen.js:
 *   import './widgets/your-widget.js';
 *
 * =====================================================================================
 * WIDGET ARCHITECTURE OVERVIEW
 * =====================================================================================
 *
 * Widgets are self-contained display components that:
 * - Render inside a .panel-content container (their parent element)
 * - Scale automatically based on container size
 * - Can update themselves on timers (clocks, countdowns, etc.)
 * - Clean up their resources when destroyed (no memory leaks)
 *
 * Key concepts:
 *
 * 1. SCALE FACTOR
 *    Widgets scale relative to container size. Use calculateScaleFactor() to get a
 *    multiplier based on the panel's minimum dimension (width or height).
 *
 *    Base sizes are designed for ~300px container. If container is 600px, scale = 2.
 *    Scale factor is clamped between 0.5 and 4.
 *
 *    Example: For a 1706x855 panel, minDimension = 855, scaleFactor = 855/300 = 2.85
 *
 * 2. DEFERRED RENDERING
 *    Use requestAnimationFrame() to defer rendering until the wrapper is in the DOM.
 *    This is required because calculateScaleFactor() needs the element to be rendered
 *    to measure its parent container.
 *
 * 3. CLEANUP
 *    The destroy() method MUST clean up:
 *    - setInterval/setTimeout timers
 *    - Event listeners (resize, etc.)
 *    - Any other resources
 *
 * =====================================================================================
 * CONFIGURATION OPTIONS
 * =====================================================================================
 *
 * List your widget's configuration options here. Example:
 *
 * Configuration options:
 * - title: string (optional) - Display title
 * - value: number (required) - The value to display
 * - show_label: boolean (default: true) - Show value label
 * - color: string (default: '#3498db') - Accent color
 * - refresh_interval: number (default: 0) - Auto-refresh in ms (0 = no refresh)
 */

import { registerWidget, calculateScaleFactor } from './registry.js';

const TemplateWidget = {
    // ==================== WIDGET METADATA ====================
    name: 'template',
    version: '1.0.0',
    author: 'your-name',

    // ==================== CONFIGURATION SCHEMA ====================
    // Define all config options with defaults. The registry applies these
    // automatically before calling create().
    configSchema: {
        // Required fields have no default - config will contain undefined if not provided
        title: { default: 'Template Widget' },

        // Optional with defaults
        show_label: { default: true },
        color: { default: '#3498db' },
        refresh_interval: { default: 0 },

        // Enum fields restrict values to a set
        style: { enum: ['simple', 'detailed'], default: 'simple' },

        // Nested objects work too (just need to handle them in your code)
        // data: { default: [] }
    },

    // ==================== CREATE METHOD ====================
    // Called when the widget is instantiated. Must return an HTMLElement.
    //
    // Parameters:
    //   container - The parent .panel-content element (may not be in DOM yet)
    //   config - Merged config with defaults applied
    //
    // Returns: HTMLElement - The widget's root element
    create(container, config) {
        // Create wrapper element - this is the widget's root
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-template';

        // Standard wrapper styles - most widgets use these
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

        // ==================== DEFERRED RENDERING ====================
        // IMPORTANT: Use requestAnimationFrame to defer rendering.
        // This ensures the wrapper is in the DOM before we calculate scale factors.
        //
        // Without this, calculateScaleFactor() returns 1 because the element
        // hasn't been attached to the DOM yet and has no parent dimensions.
        requestAnimationFrame(() => {
            const scaleFactor = calculateScaleFactor(wrapper);

            // Choose render method based on config
            if (config.style === 'detailed') {
                this._renderDetailed(wrapper, config, scaleFactor);
            } else {
                this._renderSimple(wrapper, config, scaleFactor);
            }

            // ==================== RESIZE HANDLING ====================
            // Re-render on window resize to maintain proper scaling
            // Store handler reference for cleanup in destroy()
            wrapper._resizeHandler = () => {
                const newScaleFactor = calculateScaleFactor(wrapper);
                wrapper.innerHTML = ''; // Clear and re-render
                if (config.style === 'detailed') {
                    this._renderDetailed(wrapper, config, newScaleFactor);
                } else {
                    this._renderSimple(wrapper, config, newScaleFactor);
                }
            };
            window.addEventListener('resize', wrapper._resizeHandler);
        });

        // ==================== OPTIONAL: AUTO-REFRESH ====================
        // For widgets that need periodic updates (data refresh, etc.)
        if (config.refresh_interval > 0) {
            wrapper._refreshIntervalId = setInterval(() => {
                // Your refresh logic here
                // Could fetch new data, update display, etc.
                console.log('Widget refresh triggered');
            }, config.refresh_interval);
        }

        return wrapper;
    },

    // ==================== RENDER METHODS ====================
    // Break out rendering into separate methods for clarity and maintainability.
    // Each method receives the wrapper, config, and calculated scale factor.

    _renderSimple(wrapper, config, scaleFactor) {
        // ==================== SIZING CALCULATIONS ====================
        // Define base sizes for a ~300px container, then scale them.
        //
        // Guidelines for base sizes:
        //   - Main/hero text: 80-120px
        //   - Section titles: 40-50px
        //   - Body text: 20-30px
        //   - Small labels: 14-18px
        //   - Gaps: 0-20px depending on density
        //
        // Use Math.round() to avoid subpixel rendering issues.
        const titleSize = Math.round(40 * scaleFactor);
        const valueSize = Math.round(100 * scaleFactor);
        const labelSize = Math.round(20 * scaleFactor);
        const gapSize = Math.round(10 * scaleFactor);

        // Create container with gap
        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: ${gapSize}px;
        `;

        // Title
        if (config.title) {
            const titleEl = document.createElement('div');
            titleEl.style.cssText = `
                font-size: ${titleSize}px;
                font-weight: 600;
                opacity: 0.9;
            `;
            titleEl.textContent = config.title;
            container.appendChild(titleEl);
        }

        // Main value display
        const valueEl = document.createElement('div');
        valueEl.style.cssText = `
            font-size: ${valueSize}px;
            font-weight: 300;
            line-height: 1;
            color: ${config.color};
            font-variant-numeric: tabular-nums;
        `;
        valueEl.textContent = '42';
        container.appendChild(valueEl);

        // Optional label
        if (config.show_label) {
            const labelEl = document.createElement('div');
            labelEl.style.cssText = `
                font-size: ${labelSize}px;
                opacity: 0.6;
            `;
            labelEl.textContent = 'items';
            container.appendChild(labelEl);
        }

        wrapper.appendChild(container);
    },

    _renderDetailed(wrapper, config, scaleFactor) {
        // Detailed view with more information
        const headerSize = Math.round(30 * scaleFactor);
        const valueSize = Math.round(60 * scaleFactor);
        const detailSize = Math.round(18 * scaleFactor);
        const gapSize = Math.round(15 * scaleFactor);

        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: ${gapSize}px;
            width: 100%;
        `;

        // Header row
        const headerEl = document.createElement('div');
        headerEl.style.cssText = `
            font-size: ${headerSize}px;
            font-weight: 600;
        `;
        headerEl.textContent = config.title || 'Detailed View';
        container.appendChild(headerEl);

        // Value with accent color
        const valueEl = document.createElement('div');
        valueEl.style.cssText = `
            font-size: ${valueSize}px;
            font-weight: 300;
            color: ${config.color};
        `;
        valueEl.textContent = '42';
        container.appendChild(valueEl);

        // Details row
        const detailsEl = document.createElement('div');
        detailsEl.style.cssText = `
            display: flex;
            gap: ${gapSize * 2}px;
            font-size: ${detailSize}px;
            opacity: 0.7;
        `;
        detailsEl.innerHTML = `
            <span>Min: 10</span>
            <span>Max: 100</span>
            <span>Avg: 55</span>
        `;
        container.appendChild(detailsEl);

        wrapper.appendChild(container);
    },

    // ==================== HELPER METHODS ====================
    // Add any helper methods your widget needs.

    /**
     * Format a number with locale-appropriate separators
     * @param {number} num - The number to format
     * @param {number} decimals - Decimal places (default: 0)
     * @returns {string} Formatted number string
     */
    _formatNumber(num, decimals = 0) {
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    },

    /**
     * Get a color based on value (for conditional coloring)
     * @param {number} value - The value to evaluate
     * @param {Object} config - Widget config with color options
     * @returns {string} Color hex code
     */
    _getValueColor(value, config) {
        if (value > 0) return config.positive_color || '#22c55e';
        if (value < 0) return config.negative_color || '#ef4444';
        return config.neutral_color || '#9ca3af';
    },

    // ==================== UPDATE METHOD ====================
    // Called when widget config changes and widget needs to re-render.
    // For most widgets, destroy and recreate is simplest.
    update(element, config) {
        this.destroy(element);
        const parent = element.parentNode;
        const newElement = this.create(parent, config);
        parent.replaceChild(newElement, element);
        return newElement;
    },

    // ==================== DESTROY METHOD ====================
    // CRITICAL: Clean up all resources to prevent memory leaks.
    // Called when page changes, widget is removed, or update() is invoked.
    destroy(element) {
        // Clear any intervals
        if (element && element._refreshIntervalId) {
            clearInterval(element._refreshIntervalId);
            element._refreshIntervalId = null;
        }

        // Remove event listeners
        if (element && element._resizeHandler) {
            window.removeEventListener('resize', element._resizeHandler);
            element._resizeHandler = null;
        }

        // Clear any timeouts
        if (element && element._timeoutId) {
            clearTimeout(element._timeoutId);
            element._timeoutId = null;
        }

        // Clean up any other resources (WebSocket connections, etc.)
    }
};

// ==================== REGISTER THE WIDGET ====================
// This makes the widget available for use in pages.
// The first argument is the widget_type used in API calls.
registerWidget('template', TemplateWidget);

// Export for module system (optional but recommended)
export default TemplateWidget;

/* =====================================================================================
 * USAGE EXAMPLE
 * =====================================================================================
 *
 * After creating your widget, use it in a page like this:
 *
 * curl -X POST http://localhost:8000/api/v1/screens/YOUR_SCREEN_ID/pages/my-widget-page \
 *   -H "Content-Type: application/json" \
 *   -H "X-API-Key: YOUR_API_KEY" \
 *   -d '{
 *     "content": [
 *       {
 *         "type": "widget",
 *         "widget_type": "template",
 *         "widget_config": {
 *           "title": "My Widget",
 *           "style": "detailed",
 *           "color": "#e74c3c"
 *         }
 *       }
 *     ]
 *   }'
 *
 * =====================================================================================
 * CHECKLIST FOR NEW WIDGETS
 * =====================================================================================
 *
 * [ ] Copy this template and rename to your-widget.js
 * [ ] Update widget metadata (name, version, author)
 * [ ] Define configSchema with all options and defaults
 * [ ] Implement create() method with requestAnimationFrame for deferred rendering
 * [ ] Use calculateScaleFactor() for all sizes
 * [ ] Add resize handler if widget needs to respond to container size changes
 * [ ] Implement destroy() to clean up timers, listeners, and other resources
 * [ ] Import widget in screen.js: import './widgets/your-widget.js';
 * [ ] Test at different panel sizes to verify scaling works correctly
 * [ ] Document configuration options in the file header
 *
 * =====================================================================================
 */
