Single-database configuration for Flask.

# Scripts

```bash
flask db migrate -m "Description of schema changes"
```

Apply migration to database
```bash
flask db upgrade
```

Downgrade to the previous migration (use with caution)
```bash
flask db downgrade
```

Show migration history
```bash
flask db history
```

Show current migration status
```bash
flask db current
```

# Note

- Please ensure FLASK_APP is correctly set to manage.py
- It is recommended to add the migrations/ directory to version control
