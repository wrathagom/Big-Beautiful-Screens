/**
 * Countdown Widget
 * Displays a countdown timer to a target date/time.
 */

import { registerWidget } from './registry.js';

const CountdownWidget = {
    name: 'countdown',
    version: '1.0.0',
    author: 'built-in',

    configSchema: {
        target: { required: true },              // ISO 8601 datetime string
        expired_text: { default: 'Expired' },    // Text shown when countdown ends
        show_days: { default: true },
        show_hours: { default: true },
        show_minutes: { default: true },
        show_seconds: { default: true },
        style: { enum: ['simple', 'labeled'], default: 'labeled' }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-countdown';
        wrapper.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            font-family: inherit;
            color: inherit;
        `;

        const countdownEl = document.createElement('div');
        countdownEl.className = 'countdown-display';
        countdownEl.style.cssText = `
            font-weight: bold;
            font-variant-numeric: tabular-nums;
            text-align: center;
            line-height: 1.2;
            white-space: nowrap;
        `;

        wrapper.appendChild(countdownEl);

        // Parse target date
        const targetDate = new Date(config.target);

        // Auto-scale function
        const autoScale = () => {
            const parent = wrapper.closest('.panel-content');
            if (!parent) return;

            const maxWidth = parent.clientWidth * 0.9;
            const maxHeight = parent.clientHeight * 0.85;

            // Binary search for optimal font size
            let minSize = 16;
            let maxSize = 500;
            let optimalSize = minSize;

            while (maxSize - minSize > 2) {
                const midSize = Math.floor((minSize + maxSize) / 2);
                countdownEl.style.fontSize = `${midSize}px`;

                if (countdownEl.scrollWidth <= maxWidth && countdownEl.scrollHeight <= maxHeight) {
                    optimalSize = midSize;
                    minSize = midSize;
                } else {
                    maxSize = midSize;
                }
            }

            countdownEl.style.fontSize = `${optimalSize}px`;
        };

        const update = () => {
            const now = new Date();
            const diff = targetDate - now;

            if (diff <= 0) {
                countdownEl.textContent = config.expired_text;
                // Clear interval when expired
                if (wrapper._countdownIntervalId) {
                    clearInterval(wrapper._countdownIntervalId);
                    wrapper._countdownIntervalId = null;
                }
                // Re-scale for expired text
                requestAnimationFrame(autoScale);
                return;
            }

            const parts = this._calculateParts(diff, config);
            countdownEl.innerHTML = this._formatDisplay(parts, config);
        };

        // Initial update
        update();

        // Auto-scale after render
        requestAnimationFrame(() => {
            autoScale();
            // Re-scale on window resize
            wrapper._resizeHandler = () => autoScale();
            window.addEventListener('resize', wrapper._resizeHandler);
        });

        // Update every second
        const intervalId = setInterval(update, 1000);
        wrapper._countdownIntervalId = intervalId;

        return wrapper;
    },

    _calculateParts(diff, config) {
        let remaining = Math.floor(diff / 1000); // Total seconds

        const days = Math.floor(remaining / 86400);
        remaining %= 86400;

        const hours = Math.floor(remaining / 3600);
        remaining %= 3600;

        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;

        return { days, hours, minutes, seconds };
    },

    _formatDisplay(parts, config) {
        const { days, hours, minutes, seconds } = parts;
        const { show_days, show_hours, show_minutes, show_seconds, style } = config;

        if (style === 'simple') {
            return this._formatSimple(parts, config);
        }

        return this._formatLabeled(parts, config);
    },

    _formatSimple(parts, config) {
        const { days, hours, minutes, seconds } = parts;
        const { show_days, show_hours, show_minutes, show_seconds } = config;

        const segments = [];

        if (show_days && days > 0) {
            segments.push(days.toString());
        }

        if (show_hours) {
            const h = show_days && days > 0 ? hours.toString().padStart(2, '0') : hours.toString();
            segments.push(h);
        }

        if (show_minutes) {
            segments.push(minutes.toString().padStart(2, '0'));
        }

        if (show_seconds) {
            segments.push(seconds.toString().padStart(2, '0'));
        }

        return segments.join(':');
    },

    _formatLabeled(parts, config) {
        const { days, hours, minutes, seconds } = parts;
        const { show_days, show_hours, show_minutes, show_seconds } = config;

        const segments = [];

        if (show_days && days > 0) {
            const label = days === 1 ? 'day' : 'days';
            segments.push(`${days}<span style="font-size:0.35em;opacity:0.7;margin:0 0.3em 0 0.1em">${label}</span>`);
        }

        if (show_hours) {
            segments.push(`${hours.toString().padStart(2, '0')}<span style="font-size:0.35em;opacity:0.7;margin:0 0.3em 0 0.1em">h</span>`);
        }

        if (show_minutes) {
            segments.push(`${minutes.toString().padStart(2, '0')}<span style="font-size:0.35em;opacity:0.7;margin:0 0.3em 0 0.1em">m</span>`);
        }

        if (show_seconds) {
            segments.push(`${seconds.toString().padStart(2, '0')}<span style="font-size:0.35em;opacity:0.7;margin:0 0 0 0.1em">s</span>`);
        }

        return segments.join('');
    },

    destroy(element) {
        if (element && element._countdownIntervalId) {
            clearInterval(element._countdownIntervalId);
            element._countdownIntervalId = null;
        }
        if (element && element._resizeHandler) {
            window.removeEventListener('resize', element._resizeHandler);
            element._resizeHandler = null;
        }
    }
};

registerWidget('countdown', CountdownWidget);
