# Contributing to Data Analyst Workbench

Thank you for your interest in contributing to the **Data Analyst Workbench**!

## Development Setup

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd data-analyst-workbench
   ```

2. Install in editable mode:
   ```bash
   pip install -e .
   ```

3. Verify installation:
   ```bash
   analyst doctor
   ```

## Adding Templates

To add a new project template (e.g. for e-commerce, healthcare, or financial analytics):
1. Add sample data and default SQL queries in `workbench/templates.py`.
2. Register the template name in `scaffold_project()`.
3. Submit a pull request!

## Code Style

- Keep dependencies minimal and open-source.
- Ensure terminal formatting works across Windows, macOS, and Linux without character encoding errors.
