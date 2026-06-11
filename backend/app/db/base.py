# Import all the models, so that Base has them before being
# imported by Alembic or used elsewhere
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.complaint import (  # noqa
    ComplaintCategory,
    ComplaintSubcategory,
    ComplaintQuestion,
    Complaint,
    ComplaintAnswer,
    EvidenceFile,
    ComplaintStatus,
)
from app.models.suspect import SuspectReport  # noqa
from app.models.notification import Notification  # noqa
from app.models.audit import AuditLog  # noqa

