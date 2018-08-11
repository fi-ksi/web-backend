from sqlalchemy import (Column, Integer, SmallInteger, String, Text, Enum,
                        Boolean, ForeignKey, text, DECIMAL)

from . import Base
from .module import Module
from .user import User


class ModuleCustom(Base):
    __tablename__ = 'modules_custom'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4',
    }

    module = Column(
        Integer,
        ForeignKey(Module.id, ondelete='CASCADE', onupdate='NO ACTION'),
        primary_key=True,
        nullable=False,
    )
    user = Column(
        Integer,
        ForeignKey(User.id, ondelete='CASCADE', onupdate='NO ACTION'),
        primary_key=True,
        nullable=False,
    )
    description = Column(Text, nullable=True)
    description_replace = Column(Text, nullable=True)
    data = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
