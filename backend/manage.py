#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import pymysql

pymysql.install_as_MySQLdb()

# Monkey patch the version to satisfy Django's requirements
try:
    import MySQLdb
    setattr(MySQLdb, 'version_info', (2, 2, 1, 'final', 0))
    setattr(MySQLdb, 'install_as_MySQLdb', lambda: None)
except ImportError:
    pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc 
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
