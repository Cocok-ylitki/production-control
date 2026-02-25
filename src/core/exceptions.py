class NotFoundError(Exception):
    """Ресурс не найден."""

    def __init__(self, message: str = "Not found"):
        self.message = message
        super().__init__(message)
