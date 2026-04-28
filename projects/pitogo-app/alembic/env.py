from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ensure project path is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config_obj = context.config

# Interpret the config file for Python logging.
if config_obj.config_file_name:
    try:
        fileConfig(config_obj.config_file_name)
    except Exception:
        # missing logging sections in minimal alembic.ini; continue without fileConfig
        pass

# set DB url programmatically (use config.SECURE_DIR pitogo.db)
db_path = str(config.SECURE_DIR / "pitogo.db")
config_obj.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config_obj.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config_obj.get_section(config_obj.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
