# deep-history-py
Python version of the Mapki OSM Deep History viewer.

## Development

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

To get started:

```bash
# Install dependencies
uv sync --all-extras

# Run the application
uv run python -m deephistory.wsgi

# Or with gunicorn (production)
uv run gunicorn deephistory.wsgi:app
```
