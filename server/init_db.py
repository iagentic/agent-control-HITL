#!/usr/bin/env python
"""Initialize the database with tables."""

import asyncio

from sqlalchemy import create_engine

from src.agent_protect_server.config import db_config
from src.agent_protect_server.models import Base


async def init_db():
    """Create all database tables."""
    db_url = db_config.get_url()
    
    # For SQLite with aiosqlite, we need to use sync engine for table creation
    if db_url.startswith("sqlite+aiosqlite"):
        sync_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    else:
        sync_url = db_url
    
    engine = create_engine(sync_url, echo=True)
    
    print(f"Creating tables in database: {db_url}")
    Base.metadata.create_all(engine)
    print("✓ Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())

