"""Load every production table into :class:`ProductionBase` metadata."""

from app.db.production_models import access
from app.db.production_models import repository
from app.db.production_models import indexing
from app.db.production_models import intelligence
from app.db.production_models import assistant
from app.db.production_models import evaluation

__all__ = ["access", "assistant", "evaluation", "indexing", "intelligence", "repository"]
