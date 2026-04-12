#!/usr/bin/env python3
"""
Database Migration: Add pages table

This script adds the 'pages' table to store extracted page content.
This allows generation to work across server restarts and multiple workers.

Usage:
    python migrate_add_pages_table.py
"""

from app.models.database import Base, engine, Page
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Create the pages table"""
    try:
        logger.info("Creating pages table...")

        # Create only the Page table (other tables already exist)
        Page.__table__.create(engine, checkfirst=True)

        logger.info("✅ Pages table created successfully!")
        logger.info("Migration complete!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate()
