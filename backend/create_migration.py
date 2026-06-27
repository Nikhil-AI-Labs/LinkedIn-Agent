"""Script to create initial Alembic migration."""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command

# Create Alembic config
alembic_cfg = Config("alembic.ini")

# Generate migration
print("Generating migration...")
command.revision(alembic_cfg, message="initial_phase_2_schema", autogenerate=True)
print("Migration generated successfully!")
