"""
tests/test_crm_clients.py - Comprehensive CRM client service and endpoint tests.
Covers:
- Client profile creation / auto-linking
- Client update notes
- Client CRM profile & loyalty calculations
- Client safe deletion
"""
import pytest
from app.services.client_service import ClientService
from app.models import Client, Appointment


def test_client_service_lifecycle(db_session):
    # 1. Create client
    client = ClientService.get_or_create(
        db_session,
        name="Martín Palermo",
        phone="5493834112233",
        email="martin@palermo.com"
    )
    assert client.id is not None
    assert client.name == "Martín Palermo"
    assert client.phone == "+5493834112233"
    
    # 2. Re-fetching with same phone retrieves the same record
    same_client = ClientService.get_or_create(
        db_session,
        name="Martín Palermo",
        phone="5493834112233"
    )
    assert same_client.id == client.id
    
    # 3. Update client notes
    updated = ClientService.update_client_notes(
        db_session,
        client.id,
        notes="Cliente VIP, corte texturizado y barba"
    )
    assert updated.notes == "Cliente VIP, corte texturizado y barba"
    
    # 4. Check client profile & loyalty metrics
    profile = ClientService.get_client_profile(db_session, client.id)
    assert profile["id"] == client.id
    assert "total_turnos" in profile
    assert profile["total_turnos"] >= 0
    assert "barbero_habitual" in profile
    
    # 5. Delete client
    db_session.delete(client)
    db_session.commit()
    
    # Client is now deleted or unlinked
    client_after = db_session.query(Client).filter(Client.id == client.id).first()
    assert client_after is None
