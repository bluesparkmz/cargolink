"""
Rotas de estatísticas do dashboard.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.stats_controller import get_dashboard_stats
from database import get_db
from deps import get_current_user
from models.models import User
from schemas.schemas import DashboardStatsResponse

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Contagens para os cards do ecrã inicial (cargas e camiões)."""
    return get_dashboard_stats(db, current_user)
