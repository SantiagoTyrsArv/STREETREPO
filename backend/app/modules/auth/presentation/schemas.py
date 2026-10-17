from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.modules.auth.domain.passwords import MAX_PASSWORD_LENGTH

# Longitudes de las columnas del diagrama ER.
NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 150
POLICY_VERSION_MAX_LENGTH = 20
# Un token de refresco tiene 43 caracteres; el tope solo evita cuerpos enormes.
REFRESH_TOKEN_MAX_LENGTH = 200

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH)
]
Email = Annotated[EmailStr, Field(max_length=EMAIL_MAX_LENGTH)]
# La política de longitud mínima la valida el dominio, con un mensaje propio.
Password = Annotated[str, Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RegisterRequest(_Request):
    name: Name
    email: Email
    password: Password
    accepted_policy: bool
    policy_version: Annotated[str, Field(min_length=1, max_length=POLICY_VERSION_MAX_LENGTH)]


class LoginRequest(_Request):
    email: Email
    password: Password


class RefreshRequest(_Request):
    refresh_token: Annotated[str, Field(min_length=1, max_length=REFRESH_TOKEN_MAX_LENGTH)]


class TokenResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str
    # Esquema OAuth 2, no un secreto.
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int
    refresh_token: str
