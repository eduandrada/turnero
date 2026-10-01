"""
app/api/loyalty.py - Programa de Fidelización & Puntos (Barber Club)
HiddenSYNC AI 2026
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, get_argentina_now
from app.models import Client, LoyaltyTransaction, LoyaltyReward, Voucher, AdminUser, AuditLog
from app.settings_helper import get_setting
from app.core.dependencies import require_admin_role, require_encargado_or_admin

logger = logging.getLogger("hiddensync.api.loyalty")

router = APIRouter(prefix="/api/loyalty", tags=["Barber Club & Loyalty"])


class RewardCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    points_required: int
    reward_type: str = "DISCOUNT_FIXED" # DISCOUNT_FIXED, DISCOUNT_PERCENT, FREE_SERVICE, FREE_PRODUCT
    reward_value: float = 0.0
    is_active: bool = True


class RedeemRequest(BaseModel):
    client_phone: str
    reward_id: int


def credit_client_loyalty_points(
    db: Session,
    client_phone: str,
    amount: float,
    reason: str,
    reference_id: Optional[str] = None
) -> Optional[int]:
    """Calcula y acredita automáticamente los puntos acumulados por cada corte o compra."""
    is_enabled = get_setting(db, "enable_barber_club", "1") in ["1", "true", "True"]
    if not is_enabled or not client_phone or amount <= 0:
        return 0

    points_per_amount = float(get_setting(db, "points_per_amount", "100") or 100.0)
    if points_per_amount <= 0:
        points_per_amount = 100.0

    earned_points = int(amount / points_per_amount)
    if earned_points <= 0:
        return 0

    client = db.query(Client).filter(Client.phone == client_phone).first()
    if not client:
        return 0

    client.points = (client.points or 0) + earned_points
    client.total_spent = (client.total_spent or 0.0) + amount

    # Tier status calculation
    if client.total_spent >= 100000:
        client.tier = "BLACK"
    elif client.total_spent >= 50000:
        client.tier = "ORO"
    elif client.total_spent >= 20000:
        client.tier = "PLATA"
    else:
        client.tier = "BRONCE"

    trans = LoyaltyTransaction(
        client_id=client.id,
        points=earned_points,
        reason=reason,
        reference_id=str(reference_id) if reference_id else None
    )
    db.add(trans)
    db.commit()

    return earned_points


@router.get("/config")
def get_loyalty_config(db: Session = Depends(get_db)):
    """Retorna la configuración activa del Barber Club."""
    is_enabled = get_setting(db, "enable_barber_club", "1") in ["1", "true", "True"]
    points_rate = int(get_setting(db, "points_per_amount", "100") or 100)
    return {
        "enabled": is_enabled,
        "points_per_amount": points_rate,
        "description": f"Gana 1 punto por cada ${points_rate} en cortes de pelo o productos del shop."
    }


@router.get("/client/{phone}")
def get_client_loyalty_profile(phone: str, db: Session = Depends(get_db)):
    """Consulta el balance de puntos y nivel de un cliente por su número de teléfono."""
    clean_phone = phone.strip()
    client = db.query(Client).filter(Client.phone == clean_phone).first()
    if not client:
        return {
            "found": False,
            "message": "Cliente no registrado.",
            "points": 0,
            "tier": "BRONCE",
            "total_spent": 0.0,
            "history": []
        }

    transactions = (
        db.query(LoyaltyTransaction)
        .filter(LoyaltyTransaction.client_id == client.id)
        .order_by(LoyaltyTransaction.created_at.desc())
        .limit(20)
        .all()
    )

    history = [
        {
            "id": t.id,
            "points": t.points,
            "reason": t.reason,
            "reference_id": t.reference_id,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for t in transactions
    ]

    return {
        "found": True,
        "client_id": client.id,
        "name": client.name,
        "phone": client.phone,
        "points": client.points or 0,
        "tier": client.tier or "BRONCE",
        "total_spent": client.total_spent or 0.0,
        "history": history
    }


@router.get("/rewards")
def list_rewards(db: Session = Depends(get_db)):
    """Retorna la lista de premios y beneficios canjeables activos."""
    rewards = db.query(LoyaltyReward).filter(LoyaltyReward.is_active == True).all()
    if not rewards:
        # Seed default rewards if none exist
        default_rewards = [
            LoyaltyReward(
                name="Cera o Gel de Peinado Gratis",
                description="Canjeá 200 puntos por un producto de modelado a elección en el Shop.",
                points_required=200,
                reward_type="FREE_PRODUCT",
                reward_value=1.0,
                is_active=True
            ),
            LoyaltyReward(
                name="50% OFF en tu próximo Corte",
                description="Canjeá 300 puntos por la mitad de precio en cualquier servicio de autor.",
                points_required=300,
                reward_type="DISCOUNT_PERCENT",
                reward_value=50.0,
                is_active=True
            ),
            LoyaltyReward(
                name="Corte + Ritual de Barba GRATIS",
                description="Canjeá 500 puntos por un servicio VIP completo sin cargo.",
                points_required=500,
                reward_type="FREE_SERVICE",
                reward_value=100.0,
                is_active=True
            )
        ]
        db.add_all(default_rewards)
        db.commit()
        rewards = db.query(LoyaltyReward).filter(LoyaltyReward.is_active == True).all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "points_required": r.points_required,
            "reward_type": r.reward_type,
            "reward_value": r.reward_value,
            "is_active": r.is_active
        }
        for r in rewards
    ]


@router.post("/rewards")
def create_reward(
    data: RewardCreateUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Crea un nuevo premio en el programa Barber Club."""
    reward = LoyaltyReward(**data.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return {"message": "Premio creado con éxito.", "reward_id": reward.id}


@router.put("/rewards/{reward_id}")
def update_reward(
    reward_id: int,
    data: RewardCreateUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Actualiza los parámetros de un premio de fidelización."""
    reward = db.query(LoyaltyReward).filter(LoyaltyReward.id == reward_id).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Premio no encontrado.")

    for field, val in data.model_dump().items():
        setattr(reward, field, val)

    db.commit()
    return {"message": "Premio actualizado correctamente."}


@router.delete("/rewards/{reward_id}")
def delete_reward(
    reward_id: int,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Desactiva/elimina un premio."""
    reward = db.query(LoyaltyReward).filter(LoyaltyReward.id == reward_id).first()
    if reward:
        reward.is_active = False
        db.commit()
    return {"message": "Premio eliminado."}


@router.post("/redeem")
def redeem_points(
    req: RedeemRequest,
    admin: Optional[AdminUser] = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Canjea puntos de un cliente por un premio o cupón."""
    client = db.query(Client).filter(Client.phone == req.client_phone.strip()).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    reward = db.query(LoyaltyReward).filter(LoyaltyReward.id == req.reward_id, LoyaltyReward.is_active == True).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Premio no encontrado o inactivo.")

    if (client.points or 0) < reward.points_required:
        raise HTTPException(
            status_code=400,
            detail=f"Puntos insuficientes. El cliente posee {client.points or 0} pts y requiere {reward.points_required} pts."
        )

    # Deduct points
    client.points -= reward.points_required
    trans = LoyaltyTransaction(
        client_id=client.id,
        points=-reward.points_required,
        reason=f"Canje: {reward.name}",
        reference_id=f"REWARD_{reward.id}"
    )
    db.add(trans)

    # Generate unique coupon code for redemption
    coupon_code = f"CLUB-{get_argentina_now().strftime('%m%d')}-{reward.id}{client.id}"
    voucher = Voucher(
        code=coupon_code,
        description=f"Premio Barber Club: {reward.name}",
        discount_type="PERCENTAGE" if reward.reward_type == "DISCOUNT_PERCENT" else "FIXED_AMOUNT",
        discount_value=reward.reward_value if reward.reward_type != "FREE_SERVICE" else 100.0,
        max_total_uses=1,
        is_active=True
    )
    db.add(voucher)
    db.commit()

    return {
        "message": f"¡Premio '{reward.name}' canjeado con éxito!",
        "coupon_code": coupon_code,
        "remaining_points": client.points,
        "reward_name": reward.name
    }
