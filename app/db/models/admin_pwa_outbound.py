"""One private message body per job; bounded recipients claim before provider IO."""
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AdminPwaOutboundJob(Base):
    __tablename__='admin_pwa_outbound_jobs'
    __table_args__=(
        CheckConstraint("kind IN ('direct','broadcast','test')",name='ck_pwa_outbound_kind'),
        CheckConstraint("status IN ('ready','running','complete','closed')",name='ck_pwa_outbound_job_status'),
        CheckConstraint('audience_count BETWEEN 1 AND 1000',name='ck_pwa_outbound_audience'),
        Index('ix_pwa_outbound_actor_created','actor_user_id','created_at','id'),
        Index('ix_pwa_outbound_expires','expires_at'),
    )
    id: Mapped[str]=mapped_column(ForeignKey('admin_pwa_command_audit.id',ondelete='RESTRICT'),primary_key=True)
    actor_user_id: Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),nullable=False)
    session_id: Mapped[str]=mapped_column(ForeignKey('admin_pwa_sessions.id',ondelete='CASCADE'),nullable=False,index=True)
    target_user_id: Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),nullable=True,index=True)
    kind: Mapped[str]=mapped_column(String(16),nullable=False)
    status: Mapped[str]=mapped_column(String(16),nullable=False,default='ready')
    body_json: Mapped[str]=mapped_column(Text,nullable=False)
    audience_hash: Mapped[str]=mapped_column(String(64),nullable=False)
    audience_count: Mapped[int]=mapped_column(Integer,nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    started_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    run_token: Mapped[str|None]=mapped_column(String(36),nullable=True)


class AdminPwaOutboundRecipient(Base):
    __tablename__='admin_pwa_outbound_recipients'
    __table_args__=(
        CheckConstraint("status IN ('pending','attempting','attempted','uncertain','skipped')",name='ck_pwa_outbound_recipient_status'),
        Index('ix_pwa_outbound_pending','job_id','status','user_id'),
        Index('ix_pwa_outbound_target','user_id'),
    )
    job_id: Mapped[str]=mapped_column(ForeignKey('admin_pwa_outbound_jobs.id',ondelete='CASCADE'),primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    snapshot_hash: Mapped[str]=mapped_column(String(64),nullable=False)
    language: Mapped[str]=mapped_column(String(8),nullable=False)
    status: Mapped[str]=mapped_column(String(16),nullable=False,default='pending')
    attempted_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    finished_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)


class AdminPwaOutboundEvent(Base):
    """Content-free cancellation evidence survives private job expiry."""
    __tablename__='admin_pwa_outbound_events'
    __table_args__=(CheckConstraint("operation = 'stop'",name='ck_pwa_outbound_event_operation'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    job_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    actor_user_id: Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'),nullable=True,index=True)
    operation: Mapped[str]=mapped_column(String(16),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
