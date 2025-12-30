from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    ForeignKey, Float, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class Interest(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    ALL = "all"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ComplaintReason(str, enum.Enum):
    ADULT_CONTENT = "adult_content"
    SELLING = "selling"
    DISLIKE = "dislike"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Profile
    name = Column(String(255), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(SQLEnum(Gender), nullable=True)
    interest = Column(SQLEnum(Interest), nullable=True)
    city = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    photos = Column(JSON, default=list)  # List of file_ids
    videos = Column(JSON, default=list)  # List of file_ids
    
    # Social networks
    instagram = Column(String(255), nullable=True)
    vk = Column(String(255), nullable=True)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_photo = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    
    # Subscription
    subscription_status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.EXPIRED)
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Limits
    daily_likes_used = Column(Integer, default=0)
    daily_dislikes_used = Column(Integer, default=0)
    last_limit_reset = Column(DateTime, default=func.now())
    total_likes = Column(Integer, default=0)
    total_dislikes = Column(Integer, default=0)
    
    # Referral
    referral_code = Column(String(50), unique=True, nullable=True)
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    referral_bonus_likes = Column(Integer, default=0)
    
    # Language
    language = Column(String(10), default="ru")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    likes_given = relationship("Like", foreign_keys="Like.from_user_id", back_populates="from_user")
    likes_received = relationship("Like", foreign_keys="Like.to_user_id", back_populates="to_user")
    events_created = relationship("Event", back_populates="creator")
    event_participants = relationship("EventParticipant", back_populates="user")
    complaints_received = relationship("Complaint", foreign_keys="Complaint.reported_user_id", back_populates="reported_user")
    complaints_made = relationship("Complaint", foreign_keys="Complaint.reporter_id", back_populates="reporter")


class Like(Base):
    __tablename__ = "likes"
    
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_super_like = Column(Boolean, default=False)
    message = Column(Text, nullable=True)
    video = Column(String(255), nullable=True)
    is_mutual = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="likes_given")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="likes_received")


class Dislike(Base):
    __tablename__ = "dislikes"
    
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    city = Column(String(255), nullable=False)
    event_date = Column(DateTime, nullable=False)
    photo = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="events_created")
    participants = relationship("EventParticipant", back_populates="event")


class EventParticipant(Base):
    __tablename__ = "event_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="participants")
    user = relationship("User", back_populates="event_participants")


class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(SQLEnum(ComplaintReason), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    is_resolved = Column(Boolean, default=False)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="complaints_made")
    reported_user = relationship("User", foreign_keys=[reported_user_id], back_populates="complaints_received")


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_type = Column(String(50), nullable=False)  # subscription, super_like, boost
    amount = Column(Integer, nullable=False)
    yumoney_payment_id = Column(String(255), nullable=True)
    
    # Crypto payment fields
    crypto_network = Column(String(20), nullable=True)  # BEP20, ERC20, TRC20, POLYGON
    crypto_address = Column(String(255), nullable=True)  # Wallet address for payment
    crypto_amount = Column(String(50), nullable=True)  # Amount in crypto (e.g., "5.5")
    crypto_currency = Column(String(10), nullable=True)  # USDT, USDC, BUSD, etc.
    transaction_hash = Column(String(255), nullable=True)  # Transaction hash when paid
    expires_at = Column(DateTime, nullable=True)  # Payment expiration time
    
    status = Column(String(50), default="pending")  # pending, completed, failed, expired
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)


class Boost(Base):
    __tablename__ = "boosts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())


class AdminMessage(Base):
    __tablename__ = "admin_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False)
    message_text = Column(Text, nullable=True)
    photo = Column(String(255), nullable=True)
    video = Column(String(255), nullable=True)
    buttons = Column(JSON, nullable=True)  # List of button configs
    sent_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    sent_at = Column(DateTime, nullable=True)


class SupportChat(Base):
    __tablename__ = "support_chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SupportMessage(Base):
    __tablename__ = "support_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("support_chats.id"), nullable=False)
    from_user_id = Column(Integer, nullable=False)
    is_from_admin = Column(Boolean, default=False)
    message_text = Column(Text, nullable=True)
    photo = Column(String(255), nullable=True)
    video = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())

