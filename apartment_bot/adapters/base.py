from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    source: str
    url: str
    external_id: Optional[str] = None
    price: Optional[int] = None
    rooms: Optional[float] = None
    floor: Optional[int] = None
    sqm: Optional[int] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    posted_date: Optional[str] = None
    raw_text: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch_listings(self) -> list[Listing]:
        """Fetch current listings from this source, newest data available right now."""
        raise NotImplementedError
