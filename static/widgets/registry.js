/**
 * Widget Registry - Central registration and lifecycle management for widgets
 *
 * This module provides the core infrastructure for the widget system:
 * - Widget registration
 * - Widget creation and destruction
 * - Lifecycle management (cleanup timers, event listeners)
 */

// Registered widgets by type
const widgets = {};

// Active widget instances for cleanup tracking
const activeInstances = new WeakMap();

/**
 * Register a widget type
 * @param {string} name - Widget type name (e.g., 'clock', 'countdown')
 * @param {Object} widget - Widget implementation with lifecycle methods
 */
export function registerWidget(name, widget) {
    if (widgets[name]) {
        console.warn(`Widget '${name}' is already registered. Overwriting.`);
    }
    widgets[name] = widget;
    console.log(`Widget registered: ${name} v${widget.version || '1.0.0'}`);
}

/**
 * Get a registered widget by type
 * @param {string} type - Widget type name
 * @returns {Object|null} Widget implementation or null if not found
 */
export function getWidget(type) {
    return widgets[type] || null;
}

/**
 * Create a widget instance
 * @param {string} type - Widget type name
 * @param {Object} config - Widget configuration
 * @param {HTMLElement} container - Container element for the widget
 * @returns {HTMLElement|null} Created widget element or null if type not found
 */
export function createWidget(type, config, container) {
    const widget = widgets[type];
    if (!widget) {
        console.error(`Unknown widget type: ${type}`);
        return createFallbackWidget(type);
    }

    try {
        // Apply default config values from schema
        const mergedConfig = applyDefaults(config, widget.configSchema);

        // Create the widget element
        const element = widget.create(container, mergedConfig);

        // Track the instance for cleanup
        if (element) {
            activeInstances.set(element, { type, widget, config: mergedConfig });
        }

        return element;
    } catch (error) {
        console.error(`Error creating widget '${type}':`, error);
        return createFallbackWidget(type, error.message);
    }
}

/**
 * Destroy a widget instance and clean up resources
 * @param {HTMLElement} element - Widget element to destroy
 */
export function destroyWidget(element) {
    if (!element) return;

    const instance = activeInstances.get(element);
    if (instance && instance.widget.destroy) {
        try {
            instance.widget.destroy(element);
        } catch (error) {
            console.error(`Error destroying widget '${instance.type}':`, error);
        }
    }

    activeInstances.delete(element);
}

/**
 * Destroy all active widget instances
 * Called when page changes to prevent memory leaks
 */
export function destroyAllWidgets() {
    // Note: WeakMap doesn't support iteration, so we track elements separately
    // This is handled by screen.js which tracks panel elements
}

/**
 * Apply default values from config schema
 * @param {Object} config - User-provided config
 * @param {Object} schema - Widget config schema with defaults
 * @returns {Object} Merged config with defaults
 */
function applyDefaults(config, schema) {
    if (!schema) return config || {};

    const result = { ...config };
    for (const [key, def] of Object.entries(schema)) {
        if (result[key] === undefined && def.default !== undefined) {
            result[key] = def.default;
        }
    }
    return result;
}

/**
 * Create a fallback widget when type is unknown or creation fails
 * @param {string} type - Widget type that failed
 * @param {string} error - Optional error message
 * @returns {HTMLElement} Fallback element
 */
function createFallbackWidget(type, error = null) {
    const el = document.createElement('div');
    el.className = 'widget-error';
    el.innerHTML = `
        <div style="text-align: center; padding: 1rem; color: #ff6b6b;">
            <div style="font-size: 2rem;">&#x26A0;</div>
            <div style="margin-top: 0.5rem;">Unknown widget: ${type}</div>
            ${error ? `<div style="font-size: 0.8em; opacity: 0.7; margin-top: 0.25rem;">${error}</div>` : ''}
        </div>
    `;
    return el;
}

/**
 * Get list of registered widget types
 * @returns {string[]} Array of widget type names
 */
export function getRegisteredWidgets() {
    return Object.keys(widgets);
}

/**
 * Get widget metadata
 * @param {string} type - Widget type name
 * @returns {Object|null} Widget metadata (name, version, configSchema)
 */
export function getWidgetMetadata(type) {
    const widget = widgets[type];
    if (!widget) return null;

    return {
        name: widget.name || type,
        version: widget.version || '1.0.0',
        author: widget.author || 'unknown',
        configSchema: widget.configSchema || {}
    };
}

/**
 * Calculate scale factor based on container size.
 * Use this in widgets to scale fonts/sizes proportionally to panel size.
 * Base sizes should be designed for a ~300px container.
 *
 * @param {HTMLElement} container - Container element (should be in DOM already)
 * @param {number} baseSize - Reference size for scale calculation (default: 300)
 * @returns {number} Scale factor (clamped between 0.5 and 4)
 */
export function calculateScaleFactor(container, baseSize = 300) {
    if (!container) return 1;

    // Find the panel-content element (container might be it, or be inside it)
    let panel = container.closest('.panel-content');
    if (!panel && container.classList && container.classList.contains('panel-content')) {
        panel = container;
    }
    if (!panel) return 1;

    const width = panel.clientWidth;
    const height = panel.clientHeight;
    const minDimension = Math.min(width, height);

    // Scale based on container size relative to base size
    const scaleFactor = minDimension / baseSize;

    // Clamp scale factor to reasonable bounds
    return Math.max(0.5, Math.min(scaleFactor, 4));
}
