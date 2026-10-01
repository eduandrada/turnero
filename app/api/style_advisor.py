"""
app/api/style_advisor.py - Endpoints de Asesoría de Estilo y Visagismo (IA)
HiddenSYNC AI 2026
"""
from fastapi import APIRouter
from app.schemas import StyleAdviceRequest, StyleAdviceResponse
from app.services.style_advisor import style_advisor_service

router = APIRouter(tags=["AI Style Advisor"])

@router.post("/api/ai-advisor", response_model=StyleAdviceResponse)
@router.post("/api/ai-style-advisor", response_model=StyleAdviceResponse, deprecated=True)
def get_ai_style_advice(req: StyleAdviceRequest):
    """
    Asesoría morfológica y visagismo para recomendación de corte y estilo.
    /api/ai-advisor es el endpoint canónico; /api/ai-style-advisor se conserva por compatibilidad.
    """
    return style_advisor_service.get_advice(req)
