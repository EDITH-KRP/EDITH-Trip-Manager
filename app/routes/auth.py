from fastapi import APIRouter, HTTPException, status, Depends
from app.database import get_database
from app.schemas import LoginRequest, TokenResponse, PasswordChange
from app.security import verify_password, create_access_token, hash_password
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    db = get_database()
    identifier = payload.email.strip().lower()

    # Match by exact email, or auto-completed @edith.travel, or by member first name
    user = await db.users.find_one({"email": identifier})
    if not user and "@" not in identifier:
        user = await db.users.find_one({"email": f"{identifier}@edith.travel"})
        if not user:
            all_users = await db.users.find({}).to_list()
            for candidate in all_users:
                if candidate.get("name", "").strip().lower() == identifier:
                    user = candidate
                    break

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(str(user["_id"]), user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }



@router.post("/change-password")
async def change_password(payload: PasswordChange, user=Depends(get_current_user)):
    if not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from the current password",
        )

    db = get_database()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": hash_password(payload.new_password),
            "must_change_password": False,
        }},
    )
    return {"message": "Password updated successfully"}
