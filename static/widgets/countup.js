/**
 * Count-Up Widget
 * Displays a count-up timer from a start date/time.
 */

import { registerWidget } from './registry.js';

const CountupWidget = {
    name: 'countup',
    version: '1.0.0',
    author: 'built-in',

    configSchema: {
        start: { required: true },
        label: { default: null },
        label_position: { enum: ['above', 'below', 'inline'], default: 'below' },
        show_days: { default: true },
        show_hours: { default: true },
        show_minutes: { default: true },
        show_seconds: { default: true },
        style: { enum: ['simple', 'labeled'], default: 'labeled' }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-countup';
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

        const isInline = config.label && config.label_position === 'inline';

        const innerWrapper = document.createElement('div');
        innerWrapper.style.cssText = isInline
            ? 'display: flex; align-items: baseline; gap: 0.3em; justify-content: center;'
            : 'display: flex; flex-direction: column; align-items: center; justify-content: center;';

        const labelEl = config.label ? document.createElement('div') : null;
        if (labelEl) {
            labelEl.className = 'countup-label';
            labelEl.textContent = config.label;
            labelEl.style.cssText = `
                opacity: 0.7;
                text-align: center;
                line-height: 1.2;
                white-space: nowrap;
            `;
        }

        const countupEl = document.createElement('div');
        countupEl.className = 'countup-display';
        countupEl.style.cssText = `
            font-weight: bold;
            font-variant-numeric: tabular-nums;
            text-align: center;
            line-height: 1.2;
            white-space: nowrap;
        `;

        if (labelEl && (config.label_position === 'above' || config.label_position === 'inline')) {
            innerWrapper.appendChild(labelEl);
        }
        innerWrapper.appendChild(countupEl);
        if (labelEl && config.label_position === 'below') {
            innerWrapper.appendChild(labelEl);
        }

        wrapper.appendChild(innerWrapper);

        const startDate = new Date(config.start);

        const autoScale = () => {
            const parent = wrapper.closest('.panel-content');
            if (!parent) return;

            const maxWidth = parent.clientWidth * 0.9;
            const maxHeight = parent.clientHeight * 0.85;

            let minSize = 16;
            let maxSize = 500;
            let optimalSize = minSize;

            while (maxSize - minSize > 2) {
                const midSize = Math.floor((minSize + maxSize) / 2);
                countupEl.style.fontSize = `${midSize}px`;
                if (labelEl) {
                    labelEl.style.fontSize = `${midSize * 0.35}px`;
                }

                const testWidth = innerWrapper.scrollWidth;
                const testHeight = innerWrapper.scrollHeight;

                if (testWidth <= maxWidth && testHeight <= maxHeight) {
                    optimalSize = midSize;
                    minSize = midSize;
                } else {
                    maxSize = midSize;
                }
            }

            countupEl.style.fontSize = `${optimalSize}px`;
            if (labelEl) {
                labelEl.style.fontSize = `${optimalSize * 0.35}px`;
            }
        };

        const update = () => {
            const now = new Date();
            const diff = now - startDate;

            if (diff < 0) {
                countupEl.textContent = '0:00:00:00';
                requestAnimationFrame(autoScale);
                return;
            }

            const parts = this._calculateParts(diff, config);
            countupEl.innerHTML = this._formatDisplay(parts, config);
        };

        update();

        requestAnimationFrame(() => {
            autoScale();
            wrapper._resizeHandler = () => autoScale();
            window.addEventListener('resize', wrapper._resizeHandler);
        });

        const intervalId = setInterval(update, 1000);
        wrapper._countupIntervalId = intervalId;

        return wrapper;
    },

    _calculateParts(diff, config) {
        let remaining = Math.floor(diff / 1000);

        const days = Math.floor(remaining / 86400);
        remaining %= 86400;

        const hours = Math.floor(remaining / 3600);
        remaining %= 3600;

        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;

        return { days, hours, minutes, seconds };
    },

    _formatDisplay(parts, config) {
        const { style } = config;

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
        if (element && element._countupIntervalId) {
            clearInterval(element._countupIntervalId);
            element._countupIntervalId = null;
        }
        if (element && element._resizeHandler) {
            window.removeEventListener('resize', element._resizeHandler);
            element._resizeHandler = null;
        }
    }
};

registerWidget('countup', CountupWidget);
