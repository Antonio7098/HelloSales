"""Admin API router."""

from fastapi import APIRouter, Depends

from app.api.admin.dependencies import require_admin

from . import assessments as assessments_module
from . import benchmarks as benchmarks_module
from . import feedback as feedback_module
from . import stats as stats_module

router = APIRouter(dependencies=[Depends(require_admin)])

router.include_router(stats_module.router)
router.include_router(assessments_module.router)
router.include_router(benchmarks_module.router)
router.include_router(feedback_module.router)
