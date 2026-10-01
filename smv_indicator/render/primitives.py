"""Conversion du journal d'événements en primitives graphiques indépendantes de la plateforme.

Aucune logique de stratégie ici : on ne fait que lire des événements déjà confirmés.
Chaque primitive porte `visible_from` (= confirm_index de l'événement qui la crée) pour
permettre une relecture bougie par bougie sans montrer ce qui n'était pas encore connu.
Un adaptateur (SVG, MQL5, Pine...) n'a qu'à dessiner ces primitives.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from smv.types import BULL, Event, Kind


@dataclass
class Segment:
    x0: int
    x1: int
    y: float
    style: str
    label: str = ""
    visible_from: int = 0
    meta: dict = field(default_factory=dict)


@dataclass
class Box:
    x0: int
    x1: int
    y0: float
    y1: float
    style: str
    label: str = ""
    visible_from: int = 0
    meta: dict = field(default_factory=dict)


@dataclass
class Marker:
    x: int
    y: float
    style: str
    label: str
    visible_from: int = 0
    meta: dict = field(default_factory=dict)


def build(events: list[Event], last_index: int) -> dict[str, list]:
    segs: list[Segment] = []
    boxes: list[Box] = []
    marks: list[Marker] = []
    end_of = {}
    for e in events:
        if e.kind in (Kind.LIQ_CLEAN, Kind.LIQ_BOS):
            end_of[e.data["level"]] = (e.confirm_index, "clean" if e.kind == Kind.LIQ_CLEAN else "taken")
        elif e.kind == Kind.ZONE_BROKEN:
            end_of[e.data["zone"]] = (e.confirm_index, "broken")
        elif e.kind == Kind.RANGE_EXIT:
            end_of[e.data["range"]] = (e.confirm_index, e.data["outcome"])
    for e in events:
        k = e.kind
        if k == Kind.LIQ_LEVEL:
            end, status = end_of.get(e.ref, (last_index, "intact"))
            style = f"liq_{status}"
            label = "" if status != "intact" else ("$" if e.data["source"] == "PIVOT" else "sig")
            segs.append(Segment(e.anchor_index, end, e.price, style, label, e.confirm_index,
                                {"ref": e.ref}))
        elif k in (Kind.BOS_CONTINUATION, Kind.BOS_CHANGE, Kind.TREND_INIT):
            lbl = {"BOS_CONTINUATION": "BOS", "BOS_CHANGE": "BOS CT", "TREND_INIT": "init"}[k]
            segs.append(Segment(e.anchor_index, e.confirm_index, e.price,
                                "bos_bull" if e.direction == BULL else "bos_bear", lbl, e.confirm_index,
                                {"smc_equivalent": "CHoCH" if k == Kind.BOS_CHANGE else "BOS"}))
        elif k in (Kind.ZONE, Kind.BREAKER):
            end, _ = end_of.get(e.ref, (last_index, "active"))
            base = "breaker" if k == Kind.BREAKER else ("demand" if e.direction == BULL else "supply")
            if e.data.get("decisional"):
                base += "_dec"
            lbl = {"demand": "D", "supply": "O", "breaker": "BB"}.get(base.split("_")[0], "")
            if e.data.get("doji_signature"):
                lbl += " ds"
            boxes.append(Box(e.anchor_index, end, e.data["proximal"], e.data["distal"], base, lbl,
                             e.confirm_index, {"ref": e.ref}))
        elif k == Kind.RANGE_OPEN:
            end, outcome = end_of.get(e.ref, (last_index, "open"))
            boxes.append(Box(e.anchor_index, end, e.data["low"], e.data["high"], "range",
                             e.data["context"], e.confirm_index, {"outcome": outcome}))
        elif k == Kind.FAIL:
            marks.append(Marker(e.anchor_index, e.price, "fail", "fail", e.confirm_index))
        elif k == Kind.INDUCEMENT:
            marks.append(Marker(e.anchor_index, e.price, "idm", "IDM", e.confirm_index))
        elif k == Kind.RANGE_SWEEP:
            marks.append(Marker(e.anchor_index, e.price, "sweep", e.data["label_candidate"] + "?",
                                e.confirm_index))
        elif k == Kind.EQUAL_LEVELS:
            marks.append(Marker(e.confirm_index, e.price, "eq", "EQH" if e.data["side"] == "H" else "EQL",
                                e.confirm_index))
        elif k == Kind.ODF_LINK and e.data.get("is_odf"):
            marks.append(Marker(e.anchor_index, e.price, "odf", f"ODF{e.data['chain_len']}", e.confirm_index))
        elif k == Kind.IMBALANCE:
            boxes.append(Box(e.anchor_index - 1, e.confirm_index, e.data["bottom"], e.data["top"],
                             "imbalance", "", e.confirm_index))
    return {"segments": segs, "boxes": boxes, "markers": marks}
