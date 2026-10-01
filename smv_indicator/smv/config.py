"""Paramètres du moteur et leur provenance (STRATEGY_SPEC.md §14, CALIBRATION.md).

Chaque paramètre indique sa provenance :
- DEPOT : repris du dépôt ;
- RECHERCHE : définition externe documentée dans RESEARCH.md ;
- MESURE : valeur choisie à partir des mesures sur données réelles (CALIBRATION.md) ;
- PROPOSITION : choix de formalisation sans appui suffisant, à revoir si de meilleures données existent.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PROVENANCE = {
    "pivot_left": ("RECHERCHE+MESURE", "R-ST-02", "fractal de Williams ; distribution des jambes identique de M15 à D1 (Q-16)"),
    "pivot_right": ("RECHERCHE+MESURE", "R-ST-02", "idem ; fixe le retard de confirmation"),
    "major_mode": ("DEPOT+RECHERCHE+MESURE", "R-ST-04", "lecture A retenue ; B dégénérée sur données réelles (Q-01)"),
    "bos_eps": ("DEPOT", "R-ST-05", "clôture strictement au-delà ; 0 = pas de marge"),
    "atr_len": ("RECHERCHE", "§0.4", "ATR de Wilder"),
    "bm_body_min": ("RECHERCHE+MESURE", "R-CA-01", "corps >= 70 % (≈ 20 % des bougies les plus pleines) (Q-02)"),
    "bm_range_atr": ("MESURE", "R-CA-01", "aucun effet mesuré de la BM sur la réaction ; désactivé (Q-15)"),
    "bm_search_back": ("DEPOT", "R-CA-03", "BM = BQA ou bougie précédente (diapositive M2)"),
    "doji_body_max": ("RECHERCHE", "R-CA-04", "Nison : ouverture ≈ clôture ; 10 % ≈ décile inférieur mesuré"),
    "doji_window": ("PROPOSITION", "R-CA-04", "bougies avant le BOS où un doji est « signature »"),
    "liqsig_wick_min": ("PROPOSITION", "R-CA-05", "« grande mèche » sans seuil dans le dépôt"),
    "zone_proximal": ("DEPOT", "R-OD-01", "diapositive M2 : corps de la BM ; écart avec la mèche < 0,1 ATR (Q-03)"),
    "zones_on": ("DEPOT+MESURE", "R-OD-01", "zones à l'origine des BOS ; texte du dépôt, aucun avantage mesuré (Q-04)"),
    "odf_min_len": ("PROPOSITION", "R-OD-04", "nombre de zones liées pour parler d'ODF"),
    "eq_tol_atr": ("RECHERCHE+MESURE", "R-LQ-03", "0,1 ATR : 8 % des paires de pivots consécutifs (Q-07)"),
    "eq_max_gap": ("PROPOSITION", "R-LQ-03", "écart maximal en bougies entre les deux sommets d'un EQH/EQL"),
    "range_accept_bars": ("RECHERCHE", "R-CE-01", "spring récupéré en 1 à 5 bougies, souvent 3 à 5 (praticiens, fiabilité C/D)"),
    "test_max_bars": ("PROPOSITION", "R-GS-03", "délai du test non chiffré dans les sources ; 2 x la fenêtre de récupération (Q-11)"),
    "sl_max_atr": ("DEPOT+MESURE", "R-SE-02", "16 pips « dans la stratégie », 20 non ; ≈ 2,5 ATR M15 EURUSD (Q-12)"),
    "setup_expiry_bars": ("PROPOSITION", "R-SE-01", "durée de vie d'un ordre limite non déclenché"),
    "rotation_legs": ("PROPOSITION+MESURE", "R-ST-09", "impulsions décroissantes ; effet mesuré faible (Q-08)"),
    "enable_imbalance": ("RECHERCHE", "§15", "FVG ICT à 3 bougies, optionnel"),
    "enable_sessions": ("DEPOT", "R-OU-01", "heures de tir"),
    "session_mode": ("MESURE", "R-OU-01", "'measured' : ancrages mesurés ; 'repo' : heures du dépôt (Q-10)"),
    "session_window_min": ("PROPOSITION", "R-OU-01", "durée de la fenêtre de marquage"),
    "timezone": ("DEPOT", "R-OU-01", "heure d'affichage : France"),
}

# Heures de tir mesurées (CALIBRATION.md §5) : ancrées dans le fuseau de la place concernée,
# donc justes en hiver, en été et pendant les semaines où les heures d'été sont désynchronisées.
SESSIONS_MEASURED = (
    ("ASIA", "Asia/Tokyo", 10, 0),            # 2 h Paris en hiver, 3 h en été ; fixing de Tokyo 9 h 55
    ("EUROPE", "Europe/London", 8, 0),        # 9 h Paris toute l'année
    ("US_DATA", "America/New_York", 8, 30),   # 14 h 30 Paris (13 h 30 pendant la désynchronisation)
    ("US_10H", "America/New_York", 10, 0),    # 16 h Paris : pic le plus haut sur EURUSD
)
# Heures du dépôt (M6/11), heure de France : (nom, heure d'hiver, heure d'été).
SESSIONS_REPO = (
    ("ASIA", 2, 1),
    ("ASIA_TOKYO", 4, 4),
    ("EUROPE", 9, 8),
    ("US", 14, 13),
    ("US_CHICAGO", 16, 15),
)


@dataclass(frozen=True)
class Config:
    pivot_left: int = 2
    pivot_right: int = 2
    major_mode: str = "A"
    bos_eps: float = 0.0
    atr_len: int = 14
    bm_body_min: float = 0.7
    bm_range_atr: float | None = None
    bm_search_back: int = 1
    doji_body_max: float = 0.1
    doji_window: int = 2
    liqsig_wick_min: float = 0.5
    zone_proximal: str = "body"
    zones_on: str = "bos_origin"
    odf_min_len: int = 2
    eq_tol_atr: float = 0.1
    eq_max_gap: int = 500
    range_accept_bars: int = 3
    test_max_bars: int = 10
    sl_max_atr: float = 2.5
    setup_expiry_bars: int = 100
    rotation_legs: int = 3
    enable_setups: bool = True
    enable_imbalance: bool = False
    enable_sessions: bool = False
    session_mode: str = "measured"
    session_window_min: int = 60
    timezone: str = "Europe/Paris"
    sessions: tuple = field(default=SESSIONS_REPO)

    def __post_init__(self) -> None:
        for name in ("pivot_left", "pivot_right", "range_accept_bars", "test_max_bars",
                     "setup_expiry_bars", "atr_len", "odf_min_len", "session_window_min"):
            v = getattr(self, name)
            if type(v) is not int or v < 1:
                raise ValueError(f"{name} doit être un entier >= 1")
        for name in ("bm_search_back", "doji_window", "eq_max_gap"):
            v = getattr(self, name)
            if type(v) is not int or v < 0:
                raise ValueError(f"{name} doit être un entier >= 0")
        if type(self.rotation_legs) is not int or self.rotation_legs < 2:
            raise ValueError("rotation_legs doit être un entier >= 2")
        for name in ("bos_eps", "eq_tol_atr", "sl_max_atr", "bm_body_min",
                     "doji_body_max", "liqsig_wick_min"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v):
                raise ValueError(f"{name} doit être un nombre fini")
        if self.bos_eps < 0 or self.eq_tol_atr < 0:
            raise ValueError("bos_eps et eq_tol_atr doivent être >= 0")
        if self.bm_range_atr is not None and (isinstance(self.bm_range_atr, bool) or
                not isinstance(self.bm_range_atr, (int, float)) or
                not isfinite(self.bm_range_atr) or self.bm_range_atr <= 0):
            raise ValueError("bm_range_atr doit être None ou un nombre fini > 0")
        if self.major_mode not in ("A", "B"):
            raise ValueError("major_mode doit valoir 'A' ou 'B'")
        if self.zone_proximal not in ("body", "wick"):
            raise ValueError("zone_proximal doit valoir 'body' ou 'wick'")
        if self.zones_on not in ("bos_origin", "all_pivots"):
            raise ValueError("zones_on doit valoir 'bos_origin' ou 'all_pivots'")
        if self.session_mode not in ("measured", "repo"):
            raise ValueError("session_mode doit valoir 'measured' ou 'repo'")
        for name in ("bm_body_min", "doji_body_max", "liqsig_wick_min"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} doit être dans [0, 1]")
        if self.sl_max_atr <= 0:
            raise ValueError("sl_max_atr doit être > 0")
        for name in ("enable_setups", "enable_imbalance", "enable_sessions"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} doit être booléen")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
            raise ValueError("timezone doit être un fuseau IANA valide") from exc
        for session in self.sessions:
            if (len(session) != 3 or not isinstance(session[0], str) or
                    any(type(h) is not int or not 0 <= h <= 23 for h in session[1:])):
                raise ValueError("sessions exige (nom, heure_hiver, heure_été), heures dans [0, 23]")

    def describe(self) -> list[tuple[str, object, str, str, str]]:
        """(nom, valeur, provenance, règle, note) pour chaque paramètre documenté."""
        out = []
        for f in fields(self):
            if f.name in PROVENANCE:
                prov, rule, note = PROVENANCE[f.name]
                out.append((f.name, getattr(self, f.name), prov, rule, note))
        return out
