"""add documents table for vectors

Revision ID: 1da51078015b
Revises: f04b5812a8f4
Create Date: 2025-11-29 20:52:45.497367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '1da51078015b'
down_revision: Union[str, Sequence[str], None] = 'f04b5812a8f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('source', sa.String(500), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for vector similarity search
    op.execute(
        "CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )
    
    # Create index on source for faster lookups
    op.create_index('ix_documents_source', 'documents', ['source'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_documents_source', table_name='documents')
    op.drop_table('documents')