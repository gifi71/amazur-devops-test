from sqlalchemy import Column, DateTime, Integer, Numeric, String, func

from .db import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
