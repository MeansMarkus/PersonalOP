from pydantic import BaseModel, Field


class ConsentGrant(BaseModel):
    action_type: str = Field(min_length=3, max_length=64)
    granted_by: str = Field(min_length=2, max_length=64)
    expires_at: str


class ConsentRecord(BaseModel):
    action_type: str
    granted_by: str
    granted_at: str
    expires_at: str
    is_active: bool


class ConsentRevoke(BaseModel):
    revoked_by: str = Field(min_length=2, max_length=64)
    note: str = ""
