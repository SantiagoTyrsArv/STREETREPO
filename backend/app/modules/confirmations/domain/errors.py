"""Errores del dominio de confirmaciones (HU-16)."""


class ReportNotFoundError(Exception):
    """El reporte a confirmar no existe."""


class ReportNotActiveError(Exception):
    """El reporte ya está reparado: no necesita más confirmaciones."""


class OwnReportConfirmationError(Exception):
    """El autor intenta confirmar su propio reporte (propuesta 48)."""


class ConfirmationTooFarError(Exception):
    """Quien confirma está a más de ``CONFIRMATION_RADIUS_M`` del daño (propuesta 112)."""


class AlreadyConfirmedError(Exception):
    """El usuario ya confirmó ese reporte: una confirmación por usuario y reporte."""
