"""smv : moteur déterministe et causal de la stratégie Smart Money Vision (voir docs/)."""
from .config import Config
from .engine import Engine
from .types import BEAR, BULL, NONE, Bar, Event, Kind

__all__ = ["Config", "Engine", "Bar", "Event", "Kind", "BULL", "BEAR", "NONE"]
__version__ = "0.1.0"
