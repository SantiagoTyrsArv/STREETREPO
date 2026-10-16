from enum import StrEnum


class UserRole(StrEnum):
    """Rol del usuario. Los valores coinciden con el ENUM ``rol`` del diagrama ER."""

    CITIZEN = "ciudadano"
    ADMIN = "administrador"
