from datetime import date
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class LoginRequest(BaseModel):
    email: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class MemberCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    temporary_password: str = Field(min_length=12, max_length=128)


class GroupCreate(BaseModel):
    name: str = Field(default="Trip 2027", min_length=2, max_length=100)
    group_code: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_-]+$")
    monthly_contribution: int = Field(default=2000, ge=1, le=1000000)
    duration_months: int = Field(default=12, ge=1, le=36)
    start_date: date
    custody_holder_name: str = Field(min_length=2, max_length=80)
    currency: str = "INR"
    trip_destination: str = Field(default="To be decided", max_length=160)
    trip_start_date: date | None = None
    trip_end_date: date | None = None
    planned_trip_budget: int = Field(default=0, ge=0, le=100000000)
    trip_notes: str = Field(default="", max_length=5000)


class GroupResponse(BaseModel):
    id: str
    name: str
    group_code: str
    monthly_contribution: int
    duration_months: int
    start_date: date
    custody_holder_name: str
    currency: str
    created_by: str


class MemberResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class ExpenseSplitInput(BaseModel):
    user_id: str
    share_amount: int | None = Field(default=None, ge=0)
    share_percentage: float | None = Field(default=None, ge=0, le=100)


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    category: str = Field(default="Other", max_length=40)
    amount: int = Field(gt=0, le=100000000)
    paid_by_user_id: str
    split_type: str = Field(default="equal", pattern=r"^(equal|custom|percentage)$")
    participant_user_ids: list[str] = Field(min_length=1, max_length=4)
    splits: list[ExpenseSplitInput] | None = None
    expense_date: date
    notes: str = Field(default="", max_length=1000)


class SettlementCreate(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: int = Field(gt=0, le=100000000)
    settlement_date: date
    note: str = Field(default="", max_length=500)


class TripStop(BaseModel):
    destination: str = Field(min_length=2, max_length=160)
    arrival_date: date | None = None
    departure_date: date | None = None
    notes: str = Field(default="", max_length=1000)
    transport: str = Field(default="", max_length=160)
    accommodation: str = Field(default="", max_length=160)


class TripPlanUpdate(BaseModel):
    trip_title: str = Field(min_length=2, max_length=120)
    trip_start_date: date | None = None
    trip_end_date: date | None = None
    planned_trip_budget: int = Field(default=0, ge=0, le=100000000)
    stops: list[TripStop] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=5000)


class ContributionSubmit(BaseModel):
    utr_reference: str = Field(min_length=6, max_length=24, description="12-digit Bank/UPI Reference number")
    payment_date: date
    proof_url: str | None = None
    notes: str = Field(default="", max_length=500)


class ContributionReject(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class KittyDisbursementCreate(BaseModel):
    amount: int = Field(gt=0, le=100000000, description="Amount in INR rupees")
    category: str = Field(default="stay", max_length=50)
    description: str = Field(min_length=2, max_length=200)
    recipient: str = Field(min_length=2, max_length=120)
    disbursement_date: date | None = None


class KittyReconcileRequest(BaseModel):
    actual_bank_balance: int = Field(ge=0, le=100000000, description="Actual funds confirmed in bank/cash")
    notes: str = Field(default="", max_length=500)
    apply_adjustment: bool = Field(default=False, description="Whether to auto-apply compensating adjustment")

