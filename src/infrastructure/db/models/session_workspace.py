"""
Session-Workspace Association Table
"""
from sqlalchemy import String, Column, ForeignKey, Table
from src.infrastructure.db.session import Base

# Association table for session-workspace many-to-many relationship
session_workspace = Table(
    "session_workspace",
    Base.metadata,
    Column("session_id", String, ForeignKey("sessions.id"), primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), primary_key=True)
)