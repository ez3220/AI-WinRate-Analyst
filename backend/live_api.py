from fastapi import APIRouter
from runtime_config import validate_runtime

router = APIRouter(prefix='/live', tags=['live'])

@router.get('/status')
def live_status():
    return validate_runtime()
