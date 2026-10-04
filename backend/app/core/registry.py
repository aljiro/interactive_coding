from __future__ import annotations

from collections.abc import Iterator


class RegistryError(LookupError):
    pass


class Registry[T]:
    """Tiny id -> implementation registry with duplicate protection."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: dict[str, T] = {}

    def register(self, item: T, *, replace: bool = False) -> T:
        item_id = item.id
        if not isinstance(item_id, str) or not item_id:
            raise RegistryError(f"{self.kind} must define a non-empty string id")
        if item_id in self._items and not replace and self._items[item_id] is not item:
            raise RegistryError(f"{self.kind} '{item_id}' is already registered")
        self._items[item_id] = item
        return item

    def unregister(self, item_id: str) -> None:
        self._items.pop(item_id, None)

    def get(self, item_id: str) -> T:
        try:
            return self._items[item_id]
        except KeyError:
            raise RegistryError(f"unknown {self.kind}: '{item_id}'") from None

    def ids(self) -> list[str]:
        return sorted(self._items)

    def values(self) -> list[T]:
        return [self._items[k] for k in self.ids()]

    def __contains__(self, item_id: object) -> bool:
        return item_id in self._items

    def __iter__(self) -> Iterator[T]:
        return iter(self.values())

    def __len__(self) -> int:
        return len(self._items)
