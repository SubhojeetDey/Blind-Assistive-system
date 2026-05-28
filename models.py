from fastapi import HTTPException
from database import Base
from sqlalchemy import(
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    Column,
    event,
    JSON
)
from sqlalchemy.ext.mutable import MutableList
from typing_extensions import List,Dict,Any
from sqlalchemy.orm import Mapped,relationship,mapped_column
import uuid
from datetime import datetime,timezone

user_guardians = Table(
    "user_guardians",
    Base.metadata,

    Column(
        "user_id",
        String,
        ForeignKey("Users.user_id"),
        primary_key=True
    ),

    Column(
        "guardian_id",
        String,
        ForeignKey("Users.user_id"),
        primary_key=True
    )
)

class User(Base):
    __tablename__ = "Users"

    user_id:Mapped[str]  = mapped_column(String,unique=True,nullable=False,primary_key=True,default=lambda: str(uuid.uuid4()))
    username:Mapped[str] = mapped_column(String(50),unique=True,nullable=False)
    password:Mapped[str] = mapped_column(String,nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc))
    email:Mapped[str] = mapped_column(String(100),nullable=True,unique=True)
    firstname:Mapped[str] = mapped_column(String,nullable=True,unique=False)
    lastname:Mapped[str] = mapped_column(String,nullable=True,unique=False)
    address:Mapped[str] = mapped_column(String,nullable=True)
    # consignments:Mapped[List["Consignment"]] = relationship(
    #     secondary=user_consignment,
    #     back_populates="users"
    # )
    logs:Mapped[List["Log"]] = relationship(back_populates="user")
    device_id:Mapped[str] = mapped_column(String,nullable=True,unique=True)
    guardians: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_guardians,
        primaryjoin=user_id == user_guardians.c.user_id,
        secondaryjoin=user_id == user_guardians.c.guardian_id,
        back_populates="children"
    )

    # Children/users this user guards
    children: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_guardians,
        primaryjoin=user_id == user_guardians.c.guardian_id,
        secondaryjoin=user_id == user_guardians.c.user_id,
        back_populates="guardians"
    )


class Log(Base):
    __tablename__ = "Logs"

    id:Mapped[int] = mapped_column(Integer,unique=True,primary_key=True,index=True,nullable=False)
    status:Mapped[str] = mapped_column(String,unique=False,nullable=False,default="Logged in")
    user_agent:Mapped[str] = mapped_column(String,unique=False,nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc))
    user:Mapped["User"] = relationship(back_populates="logs")
    user_id:Mapped[str] = mapped_column(ForeignKey("Users.user_id"),nullable=False)


