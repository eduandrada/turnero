"""
app/services/style_advisor.py - AI & Visagism Style Advisory Service.
Recommends haircuts, beard styling, and products based on facial anatomy and hair density.
Can be disabled via configuration without impacting core booking, shop or management features.
"""
from typing import Dict, Any, Tuple
from app.schemas import StyleAdviceRequest, StyleAdviceResponse

RECS: Dict[str, Tuple[str, str, str, str]] = {
    "ovalada": (
        "Low Skin Fade con Texturizado French Crop",
        "Corte Signature Fade",
        "Low Skin Fade",
        "Tu rostro es simétrico. Mantené textura arriba."
    ),
    "cuadrada": (
        "Mid Fade Clásico con Pompadour",
        "Combo HiddenSYNC Total (Corte + Barba)",
        "Mid Fade Rasurado",
        "Resalta tu mandíbula manteniendo laterales limpios."
    ),
    "redonda": (
        "High Drop Fade con Quiff voluminoso",
        "Corte Signature Fade",
        "High Drop Fade",
        "Concentra altura en la coronilla para elongación vertical."
    ),
    "diamante": (
        "Taper Fade Medio con barba esculpida",
        "Combo HiddenSYNC Total (Corte + Barba)",
        "Taper Fade",
        "Suaviza pómulos manteniendo caída natural."
    ),
    "triangular": (
        "Mid Skin Fade con Crop despuntado",
        "Corte Signature Fade",
        "Mid Fade Gradual",
        "Añade textura en la zona superior."
    ),
    "corazón": (
        "Low Taper con barba perfilada",
        "Barba Ritual + Toalla Caliente",
        "Low Taper Fade",
        "Barba tupida pero delimitada para equilibrar mentón."
    )
}

class StyleAdvisorService:
    @staticmethod
    def get_advice(req: StyleAdviceRequest) -> StyleAdviceResponse:
        face = req.face_shape.strip().lower()
        density = (req.hair_density or "media").lower()

        cut, srv, fade, tip = RECS.get(
            face,
            ("Taper Fade Moderno", "Corte Signature Fade", "Taper Fade 2026", "Aplica pomada con arcilla mate.")
        )
        if "baja" in density:
            tip += " Recomendamos corte en bloque con menor entresacado."
        elif "alta" in density:
            tip += " Aligeraremos peso en zonas clave para mayor soltura."

        return StyleAdviceResponse(
            face_shape=req.face_shape,
            recommendation=cut,
            styling_tips=tip,
            recommended_service=srv,
            fade_type=fade,
            confidence_score=0.95
        )

style_advisor_service = StyleAdvisorService()
