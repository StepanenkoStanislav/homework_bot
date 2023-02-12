class DontSendTelegramError(Exception):
    """Незначительные ошибки, которые не требуют отправки в Телеграм."""


class SendTelegramError(Exception):
    """Ошибки, которые будут отправляться в Телеграм."""
