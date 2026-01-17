# Screen Templates

Templates let you quickly create screens with pre-configured layouts, styles, and content. Instead of starting from scratch, choose a template that matches your use case and customize it.

## Using Templates

### Creating a Screen from a Template

1. Go to **Screens** in the admin panel
2. Click **+ Create New Screen**
3. Choose **Use a Template**
4. Browse templates by category or view all
5. Click a template to preview it
6. Click **Use This Template** to create your screen

The new screen inherits all settings, pages, and content from the template. You can then customize it as needed.

### Template Categories

Templates are organized by use case:

| Category | Best For |
|----------|----------|
| **Restaurant** | Menu boards, daily specials, dining room displays |
| **IT & Tech** | System dashboards, monitoring, build status |
| **Small Business** | Retail displays, office announcements, welcome screens |
| **Education** | Class schedules, campus info, event displays |
| **Healthcare** | Waiting room info, patient displays |
| **Custom** | Your own saved templates |

### Filtering Templates

Use the category dropdown to filter templates:

- **All Templates** - Show everything
- **System Templates** - Pre-built templates from Big Beautiful Screens
- **My Templates** - Your own saved templates (visible after you save one)

## Saving Templates

Save any screen as a template to reuse its configuration.

### How to Save a Template

1. Set up a screen with your desired layout, colors, and content
2. On the **Screens** page, find your screen card
3. Click **Screen Actions** dropdown
4. Select **Save as Template**
5. Enter a name and optional description
6. Choose a category
7. Click **Save Template**

### What Gets Saved

When you save a template, these elements are captured:

- **Screen settings** - Colors, fonts, transitions, rotation settings
- **Layout** - Panel arrangement and spacing
- **All pages** - Including their names and content
- **Content items** - Text, images, widgets, and their styling

!!! tip "Template Thumbnail"
    A preview thumbnail is automatically generated showing your template's layout and colors.

## Managing Templates

### My Templates Page

Access your saved templates at **Templates** in the navigation:

- View all your templates in a grid
- Filter by category
- See page count for each template

### Editing Templates

1. Go to **Templates**
2. Find your template
3. Click **Edit**
4. Update the name, description, or category
5. Click **Save Changes**

!!! note "Configuration Updates"
    To update a template's content or layout, create a new template from an updated screen. Template configurations cannot be edited directly.

### Deleting Templates

1. Go to **Templates**
2. Find your template
3. Click **Delete**
4. Confirm the deletion

!!! warning "Permanent Action"
    Deleted templates cannot be recovered. Screens created from a template are not affected when the template is deleted.

### Using Your Templates

Your saved templates appear in:

- **Templates page** - Click **Use** to create a screen
- **Create Screen modal** - Switch to **My Templates** tab

## System Templates

Big Beautiful Screens includes pre-built system templates for common use cases:

- **Simple Welcome** - Clean single-page welcome display
- **Dashboard Header** - Dashboard with title bar
- **Menu Board** - Restaurant-style menu layout
- **Status Grid** - Multi-panel status display
- And more...

System templates:

- Are available to all users
- Cannot be modified or deleted
- Serve as starting points you can customize

## API Access

Templates can be managed programmatically via the REST API:

```bash
# List templates
curl "http://localhost:8000/api/v1/templates"

# Create template from screen
curl -X POST http://localhost:8000/api/v1/templates \
  -H "Content-Type: application/json" \
  -d '{"screen_id": "abc123", "name": "My Layout", "category": "custom"}'

# Create screen from template
curl -X POST "http://localhost:8000/api/v1/screens?template_id=tmpl_abc123"
```

See the [Templates API Reference](../api/templates.md) for complete documentation.
