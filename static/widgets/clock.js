/**
 * Clock Widget - Digital and Analog clock display
 *
 * Configuration options:
 * - style: 'digital' | 'analog' (default: 'digital')
 * - timezone: IANA timezone string or 'local' (default: 'local')
 * - format: '12h' | '24h' (default: '12h')
 * - show_seconds: boolean (default: true)
 * - show_date: boolean (default: false)
 * - show_numbers: boolean - for analog (default: true)
 */

import { registerWidget } from './registry.js';

const ClockWidget = {
    name: 'clock',
    version: '1.0.0',
    author: 'built-in',

    configSchema: {
        style: { enum: ['digital', 'analog'], default: 'digital' },
        timezone: { default: 'local' },
        format: { enum: ['12h', '24h'], default: '12h' },
        show_seconds: { default: true },
        show_date: { default: false },
        show_numbers: { default: true }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-clock';
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

        if (config.style === 'analog') {
            return this._createAnalog(wrapper, config);
        } else {
            return this._createDigital(wrapper, config);
        }
    },

    _createDigital(wrapper, config) {
        const timeEl = document.createElement('div');
        timeEl.className = 'clock-time';
        timeEl.style.cssText = `
            font-weight: 300;
            letter-spacing: 0.05em;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        `;

        const dateEl = document.createElement('div');
        dateEl.className = 'clock-date';
        dateEl.style.cssText = `
            opacity: 0.7;
            margin-top: 0.5em;
            white-space: nowrap;
        `;
        if (!config.show_date) {
            dateEl.style.display = 'none';
        }

        wrapper.appendChild(timeEl);
        wrapper.appendChild(dateEl);

        // Auto-scale function
        const autoScale = () => {
            const parent = wrapper.closest('.panel-content');
            if (!parent) return;

            const maxWidth = parent.clientWidth * 0.9;
            const maxHeight = parent.clientHeight * (config.show_date ? 0.7 : 0.85);

            // Binary search for optimal font size
            let minSize = 16;
            let maxSize = 500;
            let optimalSize = minSize;

            while (maxSize - minSize > 2) {
                const midSize = Math.floor((minSize + maxSize) / 2);
                timeEl.style.fontSize = `${midSize}px`;
                dateEl.style.fontSize = `${midSize * 0.3}px`;

                if (timeEl.scrollWidth <= maxWidth && timeEl.scrollHeight <= maxHeight) {
                    optimalSize = midSize;
                    minSize = midSize;
                } else {
                    maxSize = midSize;
                }
            }

            timeEl.style.fontSize = `${optimalSize}px`;
            dateEl.style.fontSize = `${optimalSize * 0.3}px`;
        };

        // Update function
        const update = () => {
            const now = this._getTimeInZone(config.timezone);
            timeEl.textContent = this._formatTime(now, config);
            if (config.show_date) {
                dateEl.textContent = this._formatDate(now, config.timezone);
            }
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

        // Set up interval
        const intervalId = setInterval(update, 1000);

        // Store interval ID for cleanup
        wrapper._clockIntervalId = intervalId;

        return wrapper;
    },

    _createAnalog(wrapper, config) {
        const size = 200;
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
        svg.style.cssText = `
            width: 90%;
            height: 90%;
            max-width: 90vh;
            max-height: 90vh;
            aspect-ratio: 1;
            object-fit: contain;
        `;

        const center = size / 2;
        const radius = size / 2 - 10;

        // Clock face
        const face = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        face.setAttribute('cx', center);
        face.setAttribute('cy', center);
        face.setAttribute('r', radius);
        face.setAttribute('fill', 'none');
        face.setAttribute('stroke', 'currentColor');
        face.setAttribute('stroke-width', '2');
        face.setAttribute('opacity', '0.3');
        svg.appendChild(face);

        // Hour markers
        if (config.show_numbers) {
            for (let i = 1; i <= 12; i++) {
                const angle = (i * 30 - 90) * Math.PI / 180;
                const x = center + (radius - 20) * Math.cos(angle);
                const y = center + (radius - 20) * Math.sin(angle);

                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', x);
                text.setAttribute('y', y);
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('dominant-baseline', 'central');
                text.setAttribute('fill', 'currentColor');
                text.setAttribute('font-size', '14');
                text.setAttribute('opacity', '0.7');
                text.textContent = i;
                svg.appendChild(text);
            }
        } else {
            // Simple tick marks
            for (let i = 0; i < 12; i++) {
                const angle = (i * 30) * Math.PI / 180;
                const x1 = center + (radius - 5) * Math.cos(angle);
                const y1 = center + (radius - 5) * Math.sin(angle);
                const x2 = center + (radius - 15) * Math.cos(angle);
                const y2 = center + (radius - 15) * Math.sin(angle);

                const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                tick.setAttribute('x1', x1);
                tick.setAttribute('y1', y1);
                tick.setAttribute('x2', x2);
                tick.setAttribute('y2', y2);
                tick.setAttribute('stroke', 'currentColor');
                tick.setAttribute('stroke-width', '2');
                tick.setAttribute('opacity', '0.5');
                svg.appendChild(tick);
            }
        }

        // Hour hand
        const hourHand = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        hourHand.setAttribute('x1', center);
        hourHand.setAttribute('y1', center);
        hourHand.setAttribute('stroke', 'currentColor');
        hourHand.setAttribute('stroke-width', '4');
        hourHand.setAttribute('stroke-linecap', 'round');
        svg.appendChild(hourHand);

        // Minute hand
        const minuteHand = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        minuteHand.setAttribute('x1', center);
        minuteHand.setAttribute('y1', center);
        minuteHand.setAttribute('stroke', 'currentColor');
        minuteHand.setAttribute('stroke-width', '3');
        minuteHand.setAttribute('stroke-linecap', 'round');
        svg.appendChild(minuteHand);

        // Second hand
        const secondHand = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        secondHand.setAttribute('x1', center);
        secondHand.setAttribute('y1', center);
        secondHand.setAttribute('stroke', '#ff6b6b');
        secondHand.setAttribute('stroke-width', '1.5');
        secondHand.setAttribute('stroke-linecap', 'round');
        if (!config.show_seconds) {
            secondHand.style.display = 'none';
        }
        svg.appendChild(secondHand);

        // Center dot
        const centerDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        centerDot.setAttribute('cx', center);
        centerDot.setAttribute('cy', center);
        centerDot.setAttribute('r', '4');
        centerDot.setAttribute('fill', 'currentColor');
        svg.appendChild(centerDot);

        wrapper.appendChild(svg);

        // Update function
        const update = () => {
            const now = this._getTimeInZone(config.timezone);
            const hours = now.getHours() % 12;
            const minutes = now.getMinutes();
            const seconds = now.getSeconds();

            // Calculate angles
            const hourAngle = (hours + minutes / 60) * 30 - 90;
            const minuteAngle = (minutes + seconds / 60) * 6 - 90;
            const secondAngle = seconds * 6 - 90;

            // Update hands
            const hourLength = radius * 0.5;
            const minuteLength = radius * 0.7;
            const secondLength = radius * 0.8;

            const setHand = (hand, angle, length) => {
                const rad = angle * Math.PI / 180;
                hand.setAttribute('x2', center + length * Math.cos(rad));
                hand.setAttribute('y2', center + length * Math.sin(rad));
            };

            setHand(hourHand, hourAngle, hourLength);
            setHand(minuteHand, minuteAngle, minuteLength);
            if (config.show_seconds) {
                setHand(secondHand, secondAngle, secondLength);
            }
        };

        // Initial update
        update();

        // Set up interval
        const intervalId = setInterval(update, 1000);

        // Store interval ID for cleanup
        wrapper._clockIntervalId = intervalId;

        return wrapper;
    },

    _getTimeInZone(timezone) {
        const now = new Date();
        if (timezone === 'local' || !timezone) {
            return now;
        }

        try {
            // Create a date string in the target timezone and parse it
            const options = {
                timeZone: timezone,
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            };
            const formatter = new Intl.DateTimeFormat('en-US', options);
            const parts = formatter.formatToParts(now);

            const getPart = (type) => parts.find(p => p.type === type)?.value || '0';

            return new Date(
                parseInt(getPart('year')),
                parseInt(getPart('month')) - 1,
                parseInt(getPart('day')),
                parseInt(getPart('hour')),
                parseInt(getPart('minute')),
                parseInt(getPart('second'))
            );
        } catch (e) {
            console.warn(`Invalid timezone: ${timezone}, falling back to local`);
            return now;
        }
    },

    _formatTime(date, config) {
        let hours = date.getHours();
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');

        let suffix = '';
        if (config.format === '12h') {
            suffix = hours >= 12 ? ' PM' : ' AM';
            hours = hours % 12 || 12;
        }

        const hoursStr = hours.toString().padStart(2, '0');

        if (config.show_seconds) {
            return `${hoursStr}:${minutes}:${seconds}${suffix}`;
        } else {
            return `${hoursStr}:${minutes}${suffix}`;
        }
    },

    _formatDate(date, timezone) {
        const options = {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };

        if (timezone && timezone !== 'local') {
            options.timeZone = timezone;
        }

        try {
            return date.toLocaleDateString('en-US', options);
        } catch (e) {
            return date.toLocaleDateString('en-US');
        }
    },

    update(element, config) {
        // For clock, just destroy and recreate
        this.destroy(element);
        const parent = element.parentNode;
        const newElement = this.create(parent, config);
        parent.replaceChild(newElement, element);
        return newElement;
    },

    destroy(element) {
        if (element && element._clockIntervalId) {
            clearInterval(element._clockIntervalId);
            element._clockIntervalId = null;
        }
        if (element && element._resizeHandler) {
            window.removeEventListener('resize', element._resizeHandler);
            element._resizeHandler = null;
        }
    }
};

// Register the widget
registerWidget('clock', ClockWidget);

export default ClockWidget;
