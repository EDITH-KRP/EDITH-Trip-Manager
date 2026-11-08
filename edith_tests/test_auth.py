import pytest
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.security import hash_password
from app.schemas import LoginRequest, PasswordChange, MemberCreate
from app.routes.auth import login, change_password
from app.routes.admin import create_member, admin_list_members


@pytest.mark.anyio
async def test_admin_login_and_member_creation(setup_mock_db):
    db = setup_mock_db
    # Seed admin
    admin_id = ObjectId()
    admin_user = {
        "_id": admin_id,
        "name": "Trip Admin",
        "email": "admin@example.com",
        "password_hash": hash_password("AdminPass123!"),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(admin_user)

    # 1. Login success
    login_resp = await login(LoginRequest(email="admin@example.com", password="AdminPass123!"))
    assert "access_token" in login_resp
    assert login_resp["user"]["email"] == "admin@example.com"
    assert login_resp["user"]["role"] == "admin"

    # 2. Login invalid password
    with pytest.raises(HTTPException) as exc_info:
        await login(LoginRequest(email="admin@example.com", password="WrongPassword123!"))
    assert exc_info.value.status_code == 401

    # 3. Create member as admin
    member_payload = MemberCreate(
        name="Member Bob",
        email="bob@example.com",
        phone="+919876543210",
        temporary_password="TempPassword123!",
    )
    new_member = await create_member(member_payload, admin=admin_user)
    assert new_member["name"] == "Member Bob"
    assert new_member["email"] == "bob@example.com"

    # 4. Member login with temporary password
    member_login = await login(LoginRequest(email="bob@example.com", password="TempPassword123!"))
    assert member_login["user"]["role"] == "member"

    # 5. Member changes password
    bob_user = await db.users.find_one({"email": "bob@example.com"})
    await change_password(
        PasswordChange(current_password="TempPassword123!", new_password="NewSecurePassword123!"),
        user=bob_user,
    )

    # 6. Member logs in with new password
    new_login = await login(LoginRequest(email="bob@example.com", password="NewSecurePassword123!"))
    assert "access_token" in new_login
