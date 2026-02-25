from pydantic import Field

LIMIT_MAX = 100


class PaginationParams:
    def __init__(
        self,
        offset: int = Field(0, ge=0, description="Смещение"),
        limit: int = Field(20, ge=1, le=LIMIT_MAX, description="Лимит"),
    ):
        self.offset = offset
        self.limit = limit
