/**
 * Chart Widget - Line and Bar charts using Chart.js
 *
 * Configuration options:
 * - chart_type: 'line' | 'bar' (default: 'bar')
 * - labels: array of x-axis labels
 * - values: single series data array (simple format)
 * - datasets: multi-series data array (advanced format)
 * - label: single series label (default: 'Data')
 * - color: single series color (auto-generated if null)
 * - x_axis_label: x-axis title
 * - y_axis_label: y-axis title
 * - show_legend: boolean (default: true)
 * - legend_position: 'top' | 'bottom' | 'left' | 'right' (default: 'top')
 * - show_grid: boolean (default: true)
 * - fill: boolean - fill area under line (default: false)
 * - tension: number - line curve, 0 = straight (default: 0.1)
 * - y_min: number - y-axis minimum
 * - y_max: number - y-axis maximum
 */

import { registerWidget, calculateScaleFactor } from './registry.js';

const ChartWidget = {
    name: 'chart',
    version: '1.0.0',
    author: 'built-in',

    // Default color palette for auto-assignment
    _colorPalette: [
        '#3498db', '#e74c3c', '#2ecc71', '#f39c12',
        '#9b59b6', '#1abc9c', '#e67e22', '#34495e'
    ],

    configSchema: {
        chart_type: { enum: ['line', 'bar'], default: 'bar' },
        labels: { default: [] },
        datasets: { default: [] },
        values: { default: null },
        label: { default: 'Data' },
        color: { default: null },
        x_axis_label: { default: null },
        y_axis_label: { default: null },
        show_legend: { default: true },
        legend_position: { enum: ['top', 'bottom', 'left', 'right'], default: 'top' },
        show_grid: { default: true },
        fill: { default: false },
        tension: { default: 0.1 },
        point_radius: { default: 3 },
        index_axis: { enum: ['x', 'y'], default: 'x' },  // 'y' for horizontal bars
        x_min: { default: null },
        x_max: { default: null },
        y_min: { default: null },
        y_max: { default: null }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-chart';
        wrapper.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            padding: 0.5rem;
            box-sizing: border-box;
        `;

        // Create canvas for Chart.js
        const canvas = document.createElement('canvas');
        wrapper.appendChild(canvas);

        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            wrapper.innerHTML = '<div style="color: #e74c3c; text-align: center;">Chart.js not available</div>';
            return wrapper;
        }

        // Normalize data to Chart.js format
        const datasets = this._normalizeData(config);

        // Build Chart.js configuration
        const chartConfig = this._buildChartConfig(config, datasets);

        // Create the chart instance
        const chart = new Chart(canvas, chartConfig);

        // Store instance and config for cleanup and resize
        wrapper._chartInstance = chart;
        wrapper._chartConfig = config;

        // Apply dynamic styling (colors and font sizes) after render
        requestAnimationFrame(() => {
            this._applyDynamicStyling(wrapper, chart, config);
        });

        // Handle resize - recalculate font sizes
        const resizeHandler = () => {
            if (wrapper._chartInstance) {
                this._applyDynamicStyling(wrapper, wrapper._chartInstance, wrapper._chartConfig);
                wrapper._chartInstance.resize();
            }
        };
        wrapper._resizeHandler = resizeHandler;
        window.addEventListener('resize', resizeHandler);

        return wrapper;
    },

    destroy(element) {
        // Destroy Chart.js instance
        if (element && element._chartInstance) {
            element._chartInstance.destroy();
            element._chartInstance = null;
        }
        // Remove resize listener
        if (element && element._resizeHandler) {
            window.removeEventListener('resize', element._resizeHandler);
            element._resizeHandler = null;
        }
    },

    _normalizeData(config) {
        const isLine = config.chart_type === 'line';

        // Simple format: values array
        if (config.values && Array.isArray(config.values)) {
            const color = config.color || this._colorPalette[0];
            return [{
                label: config.label || 'Data',
                data: config.values,
                backgroundColor: isLine ? this._hexToRgba(color, 0.2) : color,
                borderColor: color,
                borderWidth: isLine ? 2 : 1,
                fill: config.fill,
                tension: config.tension,
                pointRadius: config.point_radius
            }];
        }

        // Advanced format: datasets array
        if (config.datasets && Array.isArray(config.datasets) && config.datasets.length > 0) {
            return config.datasets.map((ds, index) => {
                const color = ds.color || this._colorPalette[index % this._colorPalette.length];
                // Support per-bar colors via backgroundColor array
                const bgColor = ds.backgroundColor || (isLine ? this._hexToRgba(color, 0.2) : color);
                const borderColor = ds.borderColor || color;
                return {
                    label: ds.label || `Series ${index + 1}`,
                    data: ds.values || ds.data || [],
                    backgroundColor: bgColor,
                    borderColor: borderColor,
                    borderWidth: isLine ? 2 : 1,
                    fill: config.fill,
                    tension: config.tension,
                    pointRadius: config.point_radius
                };
            });
        }

        // Fallback: empty dataset
        return [{
            label: 'No Data',
            data: [],
            backgroundColor: this._colorPalette[0],
            borderColor: this._colorPalette[0]
        }];
    },

    _buildChartConfig(config, datasets) {
        const chartConfig = {
            type: config.chart_type,
            data: {
                labels: config.labels || [],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: config.index_axis || 'x',  // 'y' for horizontal bars
                animation: {
                    duration: 500
                },
                plugins: {
                    legend: {
                        display: config.show_legend,
                        position: config.legend_position
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: !!config.x_axis_label,
                            text: config.x_axis_label || ''
                        },
                        grid: {
                            display: config.show_grid
                        },
                        min: config.index_axis === 'y' ? config.x_min : undefined,
                        max: config.index_axis === 'y' ? config.x_max : undefined
                    },
                    y: {
                        display: true,
                        title: {
                            display: !!config.y_axis_label,
                            text: config.y_axis_label || ''
                        },
                        grid: {
                            display: config.show_grid
                        },
                        min: config.y_min,
                        max: config.y_max
                    }
                }
            }
        };
        return chartConfig;
    },

    _applyDynamicStyling(wrapper, chart, config) {
        const computedStyle = getComputedStyle(wrapper);
        const textColor = computedStyle.color || '#666';
        const gridColor = this._hexToRgba(textColor, 0.1);

        // Calculate font sizes based on container dimensions
        const fontSizes = this._calculateFontSizes(wrapper);

        // Update chart options with inherited colors and dynamic font sizes
        chart.options.plugins.legend.labels = {
            color: textColor,
            font: { size: fontSizes.legend }
        };

        chart.options.scales.x.ticks = {
            color: textColor,
            font: { size: fontSizes.ticks }
        };
        chart.options.scales.y.ticks = {
            color: textColor,
            font: { size: fontSizes.ticks }
        };

        chart.options.scales.x.title.color = textColor;
        chart.options.scales.x.title.font = { size: fontSizes.axisTitle };
        chart.options.scales.y.title.color = textColor;
        chart.options.scales.y.title.font = { size: fontSizes.axisTitle };

        chart.options.scales.x.grid.color = gridColor;
        chart.options.scales.y.grid.color = gridColor;

        // Scale point radius for line charts
        if (config.chart_type === 'line') {
            chart.data.datasets.forEach(dataset => {
                dataset.pointRadius = fontSizes.pointRadius;
                dataset.borderWidth = Math.max(2, fontSizes.lineWidth);
            });
        }

        chart.update('none'); // Update without animation
    },

    _calculateFontSizes(wrapper) {
        const scaleFactor = calculateScaleFactor(wrapper);

        return {
            legend: Math.round(12 * scaleFactor),
            ticks: Math.round(11 * scaleFactor),
            axisTitle: Math.round(14 * scaleFactor),
            pointRadius: Math.round(3 * scaleFactor),
            lineWidth: Math.round(2 * scaleFactor)
        };
    },

    _hexToRgba(hex, alpha) {
        // Handle rgb/rgba passthrough
        if (hex.startsWith('rgb')) {
            return hex;
        }

        // Parse hex color
        let r, g, b;
        if (hex.length === 4) {
            r = parseInt(hex[1] + hex[1], 16);
            g = parseInt(hex[2] + hex[2], 16);
            b = parseInt(hex[3] + hex[3], 16);
        } else {
            r = parseInt(hex.slice(1, 3), 16);
            g = parseInt(hex.slice(3, 5), 16);
            b = parseInt(hex.slice(5, 7), 16);
        }

        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
};

registerWidget('chart', ChartWidget);

export default ChartWidget;
