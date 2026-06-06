from typing import Any
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically in lowercase
    @declared_attr
    def __tablename__(cls) -> str:
        # Convert CamelCase class name to snake_case table name
        name = cls.__name__
        res = [name[0].lower()]
        for char in name[1:]:
            if char.isupper():
                res.append("_")
                res.append(char.lower())
            else:
                res.append(char)
        return "".join(res)
