"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.Enum('MALE', 'FEMALE', name='gender'), nullable=True),
        sa.Column('interest', sa.Enum('MALE', 'FEMALE', 'ALL', name='interest'), nullable=True),
        sa.Column('city', sa.String(length=255), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('photos', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('videos', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('instagram', sa.String(length=255), nullable=True),
        sa.Column('vk', sa.String(length=255), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verification_photo', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_banned', sa.Boolean(), nullable=True),
        sa.Column('is_hidden', sa.Boolean(), nullable=True),
        sa.Column('ban_reason', sa.Text(), nullable=True),
        sa.Column('subscription_status', sa.Enum('ACTIVE', 'EXPIRED', 'CANCELLED', name='subscriptionstatus'), nullable=True),
        sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
        sa.Column('daily_likes_used', sa.Integer(), nullable=True),
        sa.Column('daily_dislikes_used', sa.Integer(), nullable=True),
        sa.Column('last_limit_reset', sa.DateTime(), nullable=True),
        sa.Column('total_likes', sa.Integer(), nullable=True),
        sa.Column('total_dislikes', sa.Integer(), nullable=True),
        sa.Column('referral_code', sa.String(length=50), nullable=True),
        sa.Column('referred_by', sa.Integer(), nullable=True),
        sa.Column('referral_bonus_likes', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id'),
        sa.UniqueConstraint('referral_code')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=False)

    # Likes table
    op.create_table(
        'likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.Integer(), nullable=False),
        sa.Column('to_user_id', sa.Integer(), nullable=False),
        sa.Column('is_super_like', sa.Boolean(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('video', sa.String(length=255), nullable=True),
        sa.Column('is_mutual', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_likes_id'), 'likes', ['id'], unique=False)

    # Dislikes table
    op.create_table(
        'dislikes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.Integer(), nullable=False),
        sa.Column('to_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Events table
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=255), nullable=False),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('photo', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Event participants table
    op.create_table(
        'event_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Complaints table
    op.create_table(
        'complaints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('reported_user_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Enum('ADULT_CONTENT', 'SELLING', 'DISLIKE', 'OTHER', name='complaintreason'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reported_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('payment_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('yumoney_payment_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Boosts table
    op.create_table(
        'boosts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Admin messages table
    op.create_table(
        'admin_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=True),
        sa.Column('photo', sa.String(length=255), nullable=True),
        sa.Column('video', sa.String(length=255), nullable=True),
        sa.Column('buttons', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sent_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Support chats table
    op.create_table(
        'support_chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Support messages table
    op.create_table(
        'support_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.Integer(), nullable=False),
        sa.Column('is_from_admin', sa.Boolean(), nullable=True),
        sa.Column('message_text', sa.Text(), nullable=True),
        sa.Column('photo', sa.String(length=255), nullable=True),
        sa.Column('video', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['support_chats.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('support_messages')
    op.drop_table('support_chats')
    op.drop_table('admin_messages')
    op.drop_table('boosts')
    op.drop_table('payments')
    op.drop_table('complaints')
    op.drop_table('event_participants')
    op.drop_table('events')
    op.drop_table('dislikes')
    op.drop_index(op.f('ix_likes_id'), table_name='likes')
    op.drop_table('likes')
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    sa.Enum(name='subscriptionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='interest').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='gender').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='complaintreason').drop(op.get_bind(), checkfirst=True)

