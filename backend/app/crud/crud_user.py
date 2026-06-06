from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser:
    def get(self, db: Session, id: Any) -> Optional[User]:
        return db.query(User).filter(User.id == id).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_by_mobile(self, db: Session, *, mobile_number: str) -> Optional[User]:
        return db.query(User).filter(User.mobile_number == mobile_number).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            mobile_number=obj_in.mobile_number,
            full_name=obj_in.full_name,
            hashed_password=get_password_hash(obj_in.password),
            role=obj_in.role or "citizen",
            is_active=True,
            is_superuser=False,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            db_obj.hashed_password = hashed_password
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(
        self, db: Session, *, mobile_number: str, password: str
    ) -> Optional[User]:
        user = self.get_by_mobile(db, mobile_number=mobile_number)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser


crud_user = CRUDUser()
