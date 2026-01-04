# Widget Development Guide

This guide explains how to create custom widgets for Big Beautiful Screens.

## Quick Start

1. Copy the template file: `static/widgets/template.js`
2. Rename it to `your-widget.js`
3. Modify the widget code
4. Import it in `static/screen.js`: `import './widgets/your-widget.js';`
5. Use it in your pages with `widget_type: "your-widget"`

---

## AI Prompt for Creating Widgets

Copy and paste this prompt when asking an AI assistant to help you create a new widget:

```
I want help implementing a new Big Beautiful Screens widget.

There's a template file at: static/widgets/template.js
And documentation at: docs/development/widgets.md

These files explain the widget architecture, scaling system, and best practices.

Here's what I want my widget to do:

[Describe your widget here - what data it displays, how it should look,
any configuration options you want, etc.]
```

---

## Widget Architecture

### File Structure

```
static/widgets/
├── registry.js      # Widget registration and utilities
├── template.js      # Template for new widgets (copy this)
├── clock.js         # Clock widget
├── countdown.js     # Countdown timer widget
├── chart.js         # Chart.js-based charts
├── weather.js       # Weather display widget
└── stock.js         # Stock ticker widget
```

### Widget Object Structure

Every widget is an object with this structure:

```javascript
const MyWidget = {
    // Metadata
    name: 'my-widget',
    version: '1.0.0',
    author: 'your-name',

    // Configuration schema with defaults
    configSchema: {
        option_name: { default: 'value' },
        required_option: { required: true },
        enum_option: { enum: ['a', 'b', 'c'], default: 'a' }
    },

    // Lifecycle methods
    create(container, config) { /* returns HTMLElement */ },
    update(element, config) { /* returns new HTMLElement */ },
    destroy(element) { /* cleanup */ }
};

// Register the widget
registerWidget('my-widget', MyWidget);
```

---

## The Scaling System

Widgets must scale to fit any panel size. Big Beautiful Screens uses a **scale factor** system.

### How It Works

1. Base sizes are designed for a **~300px container**
2. `calculateScaleFactor(wrapper)` returns a multiplier based on actual container size
3. Multiply base sizes by the scale factor
4. Scale factor is clamped between 0.5 and 4

### Example Calculation

For a panel that is 1706×855 pixels:
- Minimum dimension = 855px
- Scale factor = 855 ÷ 300 = **2.85**
- A base font size of 40px becomes: 40 × 2.85 = **114px**

### Base Size Guidelines

| Element Type | Base Size Range |
|-------------|----------------|
| Hero/main text | 80-120px |
| Section titles | 40-50px |
| Body text | 20-30px |
| Small labels | 14-18px |
| Gaps/spacing | 0-20px |

### Code Example

```javascript
import { calculateScaleFactor } from './registry.js';

create(container, config) {
    const wrapper = document.createElement('div');
    wrapper.className = 'widget-example';

    // IMPORTANT: Defer rendering until element is in DOM
    requestAnimationFrame(() => {
        const scaleFactor = calculateScaleFactor(wrapper);

        // Define base sizes (for ~300px container)
        const titleSize = Math.round(40 * scaleFactor);
        const valueSize = Math.round(100 * scaleFactor);
        const gapSize = Math.round(10 * scaleFactor);

        // Use scaled sizes in your elements
        const titleEl = document.createElement('div');
        titleEl.style.fontSize = `${titleSize}px`;
        // ...
    });

    return wrapper;
}
```

### Why requestAnimationFrame?

The `calculateScaleFactor()` function needs to measure the parent container. If you call it immediately in `create()`, the wrapper element hasn't been added to the DOM yet, so it has no parent and no dimensions.

Using `requestAnimationFrame()` defers the rendering until after the browser has attached the element to the DOM.

---

## Widget Lifecycle

### create(container, config)

Called when the widget is instantiated.

- **container**: The parent `.panel-content` element
- **config**: User config merged with schema defaults
- **Returns**: The widget's root HTMLElement

```javascript
create(container, config) {
    const wrapper = document.createElement('div');
    wrapper.className = 'widget-my-widget';
    wrapper.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        font-family: inherit;
        color: inherit;
    `;

    // Deferred rendering
    requestAnimationFrame(() => {
        this._render(wrapper, config);
    });

    return wrapper;
}
```

### update(element, config)

Called when widget config changes. Most widgets destroy and recreate:

```javascript
update(element, config) {
    this.destroy(element);
    const parent = element.parentNode;
    const newElement = this.create(parent, config);
    parent.replaceChild(newElement, element);
    return newElement;
}
```

### destroy(element)

**Critical**: Clean up all resources to prevent memory leaks.

```javascript
destroy(element) {
    // Clear intervals
    if (element._intervalId) {
        clearInterval(element._intervalId);
        element._intervalId = null;
    }

    // Remove event listeners
    if (element._resizeHandler) {
        window.removeEventListener('resize', element._resizeHandler);
        element._resizeHandler = null;
    }

    // Clear timeouts
    if (element._timeoutId) {
        clearTimeout(element._timeoutId);
        element._timeoutId = null;
    }
}
```

---

## Common Patterns

### Resize Handling

Re-render when the window resizes:

```javascript
requestAnimationFrame(() => {
    this._render(wrapper, config);

    // Store handler reference for cleanup
    wrapper._resizeHandler = () => {
        wrapper.innerHTML = '';
        this._render(wrapper, config);
    };
    window.addEventListener('resize', wrapper._resizeHandler);
});
```

### Periodic Updates (Timers)

For widgets that update on a schedule:

```javascript
create(container, config) {
    const wrapper = document.createElement('div');

    const update = () => {
        // Update logic here
    };

    update(); // Initial update

    // Store interval ID for cleanup
    wrapper._intervalId = setInterval(update, 1000);

    return wrapper;
},

destroy(element) {
    if (element._intervalId) {
        clearInterval(element._intervalId);
    }
}
```

### Different Display Modes

Use config to switch between render methods:

```javascript
requestAnimationFrame(() => {
    const scaleFactor = calculateScaleFactor(wrapper);

    switch (config.display) {
        case 'compact':
            this._renderCompact(wrapper, config, scaleFactor);
            break;
        case 'detailed':
            this._renderDetailed(wrapper, config, scaleFactor);
            break;
        default:
            this._renderDefault(wrapper, config, scaleFactor);
    }
});
```

### Adaptive Layouts

Change layout based on data count:

```javascript
const items = config.items || [];

if (items.length === 1) {
    this._renderSingle(wrapper, config, scaleFactor);
} else if (items.length <= 4) {
    this._renderGrid(wrapper, config, scaleFactor);
} else {
    this._renderList(wrapper, config, scaleFactor);
}
```

### Async Data Fetching

For widgets that fetch external data:

```javascript
async create(container, config) {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = '<div>Loading...</div>';

    try {
        const data = await this._fetchData(config);
        wrapper.innerHTML = '';

        requestAnimationFrame(() => {
            const scaleFactor = calculateScaleFactor(wrapper);
            this._render(wrapper, data, config, scaleFactor);
        });
    } catch (error) {
        wrapper.innerHTML = `<div style="color: #e74c3c;">Error: ${error.message}</div>`;
    }

    return wrapper;
}
```

---

## Styling Best Practices

### Inherit Theme Colors

Use `inherit` to pick up page/panel colors:

```javascript
wrapper.style.cssText = `
    font-family: inherit;
    color: inherit;
`;
```

### Use tabular-nums for Numbers

Prevents layout shifts when numbers change:

```javascript
element.style.fontVariantNumeric = 'tabular-nums';
```

### Prevent Text Wrapping Where Needed

```javascript
element.style.whiteSpace = 'nowrap';
```

### Flexible Layouts with CSS Grid/Flexbox

```javascript
// Grid for fixed layouts
container.style.cssText = `
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: ${gapSize}px;
`;

// Flexbox for dynamic content
container.style.cssText = `
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: ${gapSize}px;
`;
```

### Handle Overflow

```javascript
wrapper.style.overflow = 'hidden';
element.style.textOverflow = 'ellipsis';
```

---

## Configuration Schema

Define all config options in `configSchema`:

```javascript
configSchema: {
    // Simple default
    title: { default: 'My Widget' },

    // Required field (no default)
    data: { required: true },

    // Enum with allowed values
    style: { enum: ['simple', 'detailed'], default: 'simple' },

    // Boolean
    show_label: { default: true },

    // Number
    refresh_interval: { default: 0 },

    // Color
    accent_color: { default: '#3498db' }
}
```

The registry automatically merges user config with defaults before calling `create()`.

---

## Testing Your Widget

### 1. Import in screen.js

```javascript
// In static/screen.js, add:
import './widgets/your-widget.js';
```

### 2. Create a Test Page

```bash
curl -X POST http://localhost:8000/api/v1/screens/YOUR_SCREEN_ID/pages/test-widget \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "content": [
      {
        "type": "widget",
        "widget_type": "your-widget",
        "widget_config": {
          "title": "Test"
        }
      }
    ]
  }'
```

### 3. Test at Different Sizes

- Resize your browser window
- Test in different grid layouts (1 panel vs 4 panels)
- Check that scaling looks good at all sizes

### 4. Check for Memory Leaks

- Navigate between pages
- Verify timers are cleared
- Check browser dev tools for detached elements

---

## Example Widgets

### Simple Static Widget

```javascript
import { registerWidget, calculateScaleFactor } from './registry.js';

const SimpleWidget = {
    name: 'simple',
    version: '1.0.0',
    author: 'example',

    configSchema: {
        text: { default: 'Hello World' },
        color: { default: '#3498db' }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-simple';
        wrapper.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            font-family: inherit;
            color: inherit;
        `;

        requestAnimationFrame(() => {
            const scaleFactor = calculateScaleFactor(wrapper);
            const fontSize = Math.round(60 * scaleFactor);

            const textEl = document.createElement('div');
            textEl.style.cssText = `
                font-size: ${fontSize}px;
                color: ${config.color};
            `;
            textEl.textContent = config.text;
            wrapper.appendChild(textEl);
        });

        return wrapper;
    },

    destroy(element) {
        // No cleanup needed for static widget
    }
};

registerWidget('simple', SimpleWidget);
export default SimpleWidget;
```

### Timer-Based Widget

```javascript
import { registerWidget, calculateScaleFactor } from './registry.js';

const TimerWidget = {
    name: 'timer',
    version: '1.0.0',
    author: 'example',

    configSchema: {
        update_interval: { default: 1000 }
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-timer';
        wrapper.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            font-family: inherit;
            color: inherit;
        `;

        const display = document.createElement('div');
        display.className = 'timer-display';
        wrapper.appendChild(display);

        requestAnimationFrame(() => {
            const scaleFactor = calculateScaleFactor(wrapper);
            display.style.fontSize = `${Math.round(80 * scaleFactor)}px`;
        });

        const update = () => {
            display.textContent = new Date().toLocaleTimeString();
        };

        update();
        wrapper._intervalId = setInterval(update, config.update_interval);

        wrapper._resizeHandler = () => {
            const scaleFactor = calculateScaleFactor(wrapper);
            display.style.fontSize = `${Math.round(80 * scaleFactor)}px`;
        };
        window.addEventListener('resize', wrapper._resizeHandler);

        return wrapper;
    },

    destroy(element) {
        if (element._intervalId) {
            clearInterval(element._intervalId);
        }
        if (element._resizeHandler) {
            window.removeEventListener('resize', element._resizeHandler);
        }
    }
};

registerWidget('timer', TimerWidget);
export default TimerWidget;
```

---

## Checklist for New Widgets

- [ ] Copy `static/widgets/template.js` and rename
- [ ] Update widget metadata (name, version, author)
- [ ] Define `configSchema` with all options and defaults
- [ ] Implement `create()` with `requestAnimationFrame` for deferred rendering
- [ ] Use `calculateScaleFactor()` for all font sizes and spacing
- [ ] Add resize handler if needed
- [ ] Implement `destroy()` to clean up timers, listeners, and resources
- [ ] Import widget in `static/screen.js`
- [ ] Test at different panel sizes
- [ ] Document configuration options in file header

---

## Troubleshooting

### Widget Shows Wrong Size on First Render

**Problem**: Scale factor returns 1 on initial render.

**Solution**: Wrap rendering in `requestAnimationFrame()`:

```javascript
requestAnimationFrame(() => {
    const scaleFactor = calculateScaleFactor(wrapper);
    // render here
});
```

### Widget Doesn't Appear

**Problem**: Widget type not recognized.

**Solutions**:
1. Check widget is imported in `screen.js`
2. Verify `registerWidget()` is called with correct name
3. Check browser console for errors

### Timer Keeps Running After Page Change

**Problem**: Memory leak from uncleared interval.

**Solution**: Clean up in `destroy()`:

```javascript
destroy(element) {
    if (element._intervalId) {
        clearInterval(element._intervalId);
    }
}
```

### Fonts Don't Match Theme

**Problem**: Widget uses hardcoded fonts.

**Solution**: Use `inherit`:

```javascript
wrapper.style.fontFamily = 'inherit';
wrapper.style.color = 'inherit';
```
