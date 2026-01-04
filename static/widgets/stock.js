/**
 * Stock Widget - Static display widget for stock tickers
 *
 * This is a display/formatting widget - users provide stock data directly
 * in the configuration, and the widget handles the display with adaptive
 * layouts based on the number of stocks.
 *
 * Configuration options:
 * - stocks: Array of stock objects (required)
 *   Each stock: { symbol, price, change?, change_percent?, name? }
 * - show_change: boolean (default: true) - Show +/- change
 * - show_percent: boolean (default: true) - Show % change
 * - gain_color: string (default: '#22c55e') - Color for positive changes
 * - loss_color: string (default: '#ef4444') - Color for negative changes
 * - neutral_color: string (default: '#9ca3af') - Color for no change
 * - compact: boolean (default: false) - Force compact list mode
 */

import { registerWidget } from './registry.js';

const StockWidget = {
    name: 'stock',
    version: '1.0.0',
    author: 'built-in',

    configSchema: {
        stocks: { required: true },
        show_change: { default: true },
        show_percent: { default: true },
        gain_color: { default: '#22c55e' },
        loss_color: { default: '#ef4444' },
        neutral_color: { default: '#9ca3af' },
        compact: { default: false }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-stock';
        wrapper.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            font-family: inherit;
            color: inherit;
            padding: 1rem;
            box-sizing: border-box;
        `;

        if (!config.stocks || !Array.isArray(config.stocks) || config.stocks.length === 0) {
            wrapper.innerHTML = '<div style="opacity: 0.5;">No stock data provided</div>';
            return wrapper;
        }

        const stockCount = config.stocks.length;

        // Determine display mode based on count and config
        if (config.compact || stockCount > 4) {
            this._renderCompactList(wrapper, config);
        } else if (stockCount === 1) {
            this._renderSingleStock(wrapper, config);
        } else {
            this._renderGrid(wrapper, config);
        }

        return wrapper;
    },

    _renderSingleStock(wrapper, config) {
        const stock = config.stocks[0];
        const changeColor = this._getChangeColor(stock.change, config);

        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            width: 100%;
        `;

        // Symbol
        const symbolEl = document.createElement('div');
        symbolEl.style.cssText = `
            font-size: 2rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            opacity: 0.9;
        `;
        symbolEl.textContent = stock.symbol;
        container.appendChild(symbolEl);

        // Company name (if provided)
        if (stock.name) {
            const nameEl = document.createElement('div');
            nameEl.style.cssText = 'font-size: 0.9rem; opacity: 0.6;';
            nameEl.textContent = stock.name;
            container.appendChild(nameEl);
        }

        // Price
        const priceEl = document.createElement('div');
        priceEl.style.cssText = `
            font-size: 4rem;
            font-weight: 300;
            line-height: 1;
            font-variant-numeric: tabular-nums;
        `;
        priceEl.textContent = this._formatPrice(stock.price);
        container.appendChild(priceEl);

        // Change row
        if (config.show_change || config.show_percent) {
            const changeRow = document.createElement('div');
            changeRow.style.cssText = `
                display: flex;
                align-items: baseline;
                gap: 0.75rem;
                font-size: 1.5rem;
                color: ${changeColor};
            `;

            if (config.show_change && stock.change !== undefined) {
                const changeEl = document.createElement('span');
                changeEl.textContent = this._formatChange(stock.change);
                changeRow.appendChild(changeEl);
            }

            if (config.show_percent && stock.change_percent !== undefined) {
                const percentEl = document.createElement('span');
                percentEl.textContent = this._formatPercent(stock.change_percent);
                changeRow.appendChild(percentEl);
            }

            container.appendChild(changeRow);
        }

        wrapper.appendChild(container);
        this._autoScale(wrapper, 1);
    },

    _renderGrid(wrapper, config) {
        const stocks = config.stocks;
        const count = stocks.length;

        // Determine grid layout: 2x1 for 2, 2x2 for 3-4
        const cols = count <= 2 ? count : 2;
        const rows = Math.ceil(count / cols);

        const grid = document.createElement('div');
        grid.style.cssText = `
            display: grid;
            grid-template-columns: repeat(${cols}, 1fr);
            grid-template-rows: repeat(${rows}, 1fr);
            gap: 1.5rem;
            width: 100%;
            height: 100%;
            padding: 1rem;
        `;

        stocks.forEach(stock => {
            const changeColor = this._getChangeColor(stock.change, config);

            const cell = document.createElement('div');
            cell.style.cssText = `
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 0.25rem;
            `;

            // Symbol
            const symbolEl = document.createElement('div');
            symbolEl.style.cssText = 'font-size: 1.2rem; font-weight: 600; opacity: 0.8;';
            symbolEl.textContent = stock.symbol;
            cell.appendChild(symbolEl);

            // Price
            const priceEl = document.createElement('div');
            priceEl.style.cssText = `
                font-size: 2rem;
                font-weight: 300;
                font-variant-numeric: tabular-nums;
            `;
            priceEl.textContent = this._formatPrice(stock.price);
            cell.appendChild(priceEl);

            // Change
            if ((config.show_change && stock.change !== undefined) ||
                (config.show_percent && stock.change_percent !== undefined)) {
                const changeEl = document.createElement('div');
                changeEl.style.cssText = `
                    font-size: 1rem;
                    color: ${changeColor};
                `;

                const parts = [];
                if (config.show_change && stock.change !== undefined) {
                    parts.push(this._formatChange(stock.change));
                }
                if (config.show_percent && stock.change_percent !== undefined) {
                    parts.push(this._formatPercent(stock.change_percent));
                }
                changeEl.textContent = parts.join(' ');
                cell.appendChild(changeEl);
            }

            grid.appendChild(cell);
        });

        wrapper.appendChild(grid);
        this._autoScale(wrapper, count);
    },

    _renderCompactList(wrapper, config) {
        const stocks = config.stocks;

        const list = document.createElement('div');
        list.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
        `;

        stocks.forEach(stock => {
            const changeColor = this._getChangeColor(stock.change, config);

            const row = document.createElement('div');
            row.style.cssText = `
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 0.5rem 0;
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
            `;

            // Symbol
            const symbolEl = document.createElement('div');
            symbolEl.style.cssText = `
                font-weight: 600;
                min-width: 4rem;
                font-size: 1rem;
            `;
            symbolEl.textContent = stock.symbol;
            row.appendChild(symbolEl);

            // Name (if provided, truncated)
            if (stock.name) {
                const nameEl = document.createElement('div');
                nameEl.style.cssText = `
                    flex: 1;
                    font-size: 0.85rem;
                    opacity: 0.6;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                `;
                nameEl.textContent = stock.name;
                row.appendChild(nameEl);
            } else {
                const spacer = document.createElement('div');
                spacer.style.flex = '1';
                row.appendChild(spacer);
            }

            // Price
            const priceEl = document.createElement('div');
            priceEl.style.cssText = `
                font-size: 1rem;
                font-variant-numeric: tabular-nums;
                min-width: 5rem;
                text-align: right;
            `;
            priceEl.textContent = this._formatPrice(stock.price);
            row.appendChild(priceEl);

            // Change
            if ((config.show_change && stock.change !== undefined) ||
                (config.show_percent && stock.change_percent !== undefined)) {
                const changeEl = document.createElement('div');
                changeEl.style.cssText = `
                    font-size: 0.9rem;
                    color: ${changeColor};
                    min-width: 6rem;
                    text-align: right;
                `;

                const parts = [];
                if (config.show_change && stock.change !== undefined) {
                    parts.push(this._formatChange(stock.change));
                }
                if (config.show_percent && stock.change_percent !== undefined) {
                    parts.push(this._formatPercent(stock.change_percent));
                }
                changeEl.textContent = parts.join(' ');
                row.appendChild(changeEl);
            }

            list.appendChild(row);
        });

        wrapper.appendChild(list);
    },

    _getChangeColor(change, config) {
        if (change === undefined || change === 0) {
            return config.neutral_color;
        }
        return change > 0 ? config.gain_color : config.loss_color;
    },

    _formatPrice(price) {
        if (typeof price !== 'number') return price;
        // Format with commas and 2 decimal places
        return price.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },

    _formatChange(change) {
        if (typeof change !== 'number') return change;
        const sign = change > 0 ? '+' : '';
        return `${sign}${change.toFixed(2)}`;
    },

    _formatPercent(percent) {
        if (typeof percent !== 'number') return percent;
        const sign = percent > 0 ? '+' : '';
        return `(${sign}${percent.toFixed(2)}%)`;
    },

    _autoScale(wrapper, stockCount) {
        requestAnimationFrame(() => {
            const parent = wrapper.closest('.panel-content');
            if (!parent) return;

            // Scale based on panel size and stock count
            const baseScale = stockCount === 1 ? 300 : 400;
            const scale = Math.min(
                parent.clientWidth / baseScale,
                parent.clientHeight / (stockCount === 1 ? 200 : 300)
            );

            if (scale > 1) {
                wrapper.style.transform = `scale(${Math.min(scale, 2)})`;
            }
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
        // No cleanup needed for static widget
    }
};

// Register the widget
registerWidget('stock', StockWidget);

export default StockWidget;
