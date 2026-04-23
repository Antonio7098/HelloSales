"""In-memory mutation record storage."""

from __future__ import annotations

from hello_sales_backend.modules.entity_operations.use_cases.ports import MutationRecord


class InMemoryMutationRecordStore:
    """Keep recent mutation records in process memory."""

    def __init__(self) -> None:
        self._records: dict[str, MutationRecord] = {}

    async def save(self, record: MutationRecord) -> None:
        self._records[record.operation_id] = record

    async def get(self, operation_id: str) -> MutationRecord | None:
        return self._records.get(operation_id)
