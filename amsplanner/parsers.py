"""Automatic job extraction from Bambu Studio files.

Supported inputs (per documented Bambu Studio file structure):
  * plain G-code (.gcode)     -> colour + type + estimate, used slots from tool changes
  * sliced project (.gcode.3mf) -> Metadata/slice_info.config: per-plate type, colour, grams, estimate
  * unsliced project (.3mf)   -> Metadata/project_settings.config (colour, type arrays) +
                                 Metadata/model_settings.config (filament assigned to each part)
Any field that cannot be read is reported in Job.missing so the user can fill it
in manually (with quick-select from the filament history).
"""
from __future__ import annotations
import json, re, zipfile, os
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict
from .model import Job, normalize_color, normalize_type

_TIME = re.compile(r"(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?")


def _parse_duration(s: str) -> Optional[float]:
    m = _TIME.search(s.strip())
    if not m or not any(m.groups()):
        return None
    d, h, mi, se = (int(x) if x else 0 for x in m.groups())
    return float(d * 86400 + h * 3600 + mi * 60 + se)


def _split_list(v: str) -> List[str]:
    v = v.strip()
    parts = re.split(r"[;,]", v) if v else []
    return [p.strip().strip('"') for p in parts]


def _key(t, c):
    return f"{t or '?'}:{c or '?'}"


# ------------------------------------------------------------------ G-code
def parse_gcode_text(text: str, name: str = "job", source: str = "gcode") -> Job:
    cfg: Dict[str, str] = {}
    est = None
    used = set()
    for line in text.splitlines():
        if line.startswith(";"):
            body = line[1:].strip()
            if "total estimated time:" in body:
                est = _parse_duration(body.split("total estimated time:")[1])
            elif body.startswith("estimated printing time") and "=" in body:
                est = est or _parse_duration(body.split("=", 1)[1])
            elif " = " in body:
                k, v = body.split(" = ", 1)
                cfg.setdefault(k.strip(), v.strip())
            continue
        s = line.split(";", 1)[0].strip()
        m = re.match(r"^M620\s+S(\d+)A", s)
        if m and int(m.group(1)) < 255:
            used.add(int(m.group(1)))
        m = re.match(r"^T(\d+)\b", s)
        if m and int(m.group(1)) < 255:
            used.add(int(m.group(1)))
    colors = [normalize_color(c) for c in _split_list(cfg.get("filament_colour", ""))]
    types = [normalize_type(t) for t in _split_list(cfg.get("filament_type", ""))]
    n = max(len(colors), len(types))
    if not used:
        used = set(range(n)) if n == 1 else set()
    missing = []
    keys = []
    for i in sorted(used):
        c = colors[i] if i < len(colors) else None
        t = types[i] if i < len(types) else None
        if c is None: missing.append(f"colour of slot {i+1}")
        if t is None: missing.append(f"type of slot {i+1}")
        keys.append(_key(t, c))
    if not keys:
        missing.append("filaments used")
    if est is None:
        missing.append("print time")
    return Job(name=name, filaments=frozenset(keys), est_time_s=est, source=source, missing=missing)


def parse_gcode(path: str) -> List[Job]:
    with open(path, "r", errors="ignore") as f:
        return [parse_gcode_text(f.read(), os.path.basename(path))]


# ------------------------------------------------------------------ 3MF
def _read(z: zipfile.ZipFile, name: str) -> Optional[str]:
    try:
        return z.read(name).decode("utf-8", errors="ignore")
    except KeyError:
        return None


def _paint_states(code: str) -> set:
    """Leaf states of a Bambu/Prusa 'paint_color' (TriangleSelector) string.
    Nibbles are read from the end; a nibble with two low bits 0 is a leaf whose
    state is the two high bits (3 = extended: state = 3 + next nibble)."""
    nib = [int(c, 16) for c in reversed(code)]
    out, i = set(), 0
    while i < len(nib):
        n = nib[i]; i += 1
        if n & 3:
            continue                      # split node, children follow
        st = n >> 2
        if st == 3 and i < len(nib):
            st = 3 + nib[i]; i += 1
        out.add(st)
    return out


def _painted_parts(z: zipfile.ZipFile) -> Dict[str, Dict[str, tuple]]:
    """{model file: {sub-object id: (set of painted extruders, has_unpainted)}}"""
    res: Dict[str, Dict[str, tuple]] = {}
    for name in z.namelist():
        if not (name.startswith("3D/Objects/") and name.endswith(".model")):
            continue
        x = z.read(name).decode("utf-8", errors="ignore")
        parts = {}
        for oid, body in re.findall(r"<object\s+id=\"(\d+)\"[^>]*>(.*?)</object>", x, flags=re.S):
            painted, unpainted = set(), False
            for tri in re.finditer(r"<triangle\b[^>]*>", body):
                m = re.search(r"paint_color=\"([0-9A-Fa-f]+)\"", tri.group(0))
                if not m:
                    unpainted = True; continue
                st = _paint_states(m.group(1))
                if 0 in st:
                    unpainted = True
                painted |= {v for v in st if v > 0}
            parts[oid] = (painted, unpainted)
        res["/" + name] = parts
    return res


def _core_model_colours(z: zipfile.ZipFile) -> List[Optional[str]]:
    """3MF core/material extension: colours actually referenced by objects or
    triangles (m:colorgroup / basematerials). Used for CAD exports without slicer data."""
    x = _read(z, "3D/3dmodel.model") or ""
    groups: Dict[str, List[str]] = {}
    for gid, inner in re.findall(r"<(?:\w+:)?colorgroup\s+id=\"(\d+)\"[^>]*>(.*?)</(?:\w+:)?colorgroup>", x, flags=re.S):
        groups[gid] = re.findall(r"color=\"([^\"]+)\"", inner)
    for gid, inner in re.findall(r"<(?:\w+:)?basematerials\s+id=\"(\d+)\"[^>]*>(.*?)</(?:\w+:)?basematerials>", x, flags=re.S):
        groups[gid] = re.findall(r"displaycolor=\"([^\"]+)\"", inner)
    used = set()
    for tag in re.finditer(r"<(?:object|triangle)\b[^>]*>", x):
        t = tag.group(0)
        pid = re.search(r"\bpid=\"(\d+)\"", t)
        if not pid or pid.group(1) not in groups:
            continue
        for attr in ("pindex", "p1", "p2", "p3"):
            v = re.search(r"\b" + attr + r"=\"(\d+)\"", t)
            if v:
                used.add((pid.group(1), int(v.group(1))))
    cols = []
    for gid, i in sorted(used):
        c = normalize_color(groups[gid][i]) if i < len(groups[gid]) else None
        if c and c not in cols:
            cols.append(c)
    return cols


def parse_3mf(path: str) -> List[Job]:
    base = os.path.basename(path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        # 1) sliced project: per-plate results
        si = _read(z, "Metadata/slice_info.config")
        if si:
            jobs = []
            root = ET.fromstring(si)
            for plate in root.iter("plate"):
                meta = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
                keys, missing = [], []
                for f in plate.findall("filament"):
                    c, t = normalize_color(f.get("color")), normalize_type(f.get("type"))
                    if c is None: missing.append(f"colour of slot {f.get('id')}")
                    if t is None: missing.append(f"type of slot {f.get('id')}")
                    keys.append(_key(t, c))
                est = float(meta["prediction"]) if meta.get("prediction") else None
                if est is None: missing.append("print time")
                jobs.append(Job(f"{base} / plate {meta.get('index', len(jobs)+1)}",
                                frozenset(keys), est, "gcode.3mf", missing))
            if jobs:
                return jobs
        # embedded plate G-code without slice_info
        gfiles = sorted(n for n in names if re.match(r"Metadata/plate_\d+\.gcode$", n))
        if gfiles:
            return [parse_gcode_text(_read(z, g), f"{base} / {g.split('/')[-1]}", "gcode.3mf") for g in gfiles]
        # 2) unsliced project
        ps = _read(z, "Metadata/project_settings.config")
        colors, types = [], []
        if ps:
            try:
                cfg = json.loads(ps)
                colors = [normalize_color(c) for c in cfg.get("filament_colour", [])]
                types = [normalize_type(t) for t in cfg.get("filament_type", [])]
            except json.JSONDecodeError:
                pass
        ms = _read(z, "Metadata/model_settings.config")
        jobs = []
        if ms:
            root = ET.fromstring(ms)
            paint = _painted_parts(z)
            model = _read(z, "3D/3dmodel.model") or ""
            comps: Dict[str, list] = {}
            for oid, body in re.findall(r"<object\s+id=\"(\d+)\"[^>]*>(.*?)</object>", model, flags=re.S):
                comps[oid] = re.findall(r"<component\s+[^>]*?path=\"([^\"]+)\"[^>]*?objectid=\"(\d+)\"", body)
            obj_ext: Dict[str, set] = {}
            for obj in root.findall("object"):
                default = next((int(md.get("value")) for md in obj.findall("metadata")
                                if md.get("key") == "extruder" and md.get("value", "").isdigit()), 1)
                part_ext = {}
                for part in obj.findall("part"):
                    pe = next((int(md.get("value")) for md in part.findall("metadata")
                               if md.get("key") == "extruder" and md.get("value", "").isdigit()), default)
                    part_ext[part.get("id")] = pe
                ex = set()
                parts = comps.get(obj.get("id"), [])
                if parts:
                    for path, sub in parts:
                        painted, unpainted = paint.get(path, {}).get(sub, (set(), True))
                        ex |= painted
                        if unpainted:
                            ex.add(part_ext.get(sub, default))
                else:
                    ex = set(part_ext.values()) or {default}
                obj_ext[obj.get("id")] = ex or {default}
            for plate in root.findall("plate"):
                meta = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
                slots = set()
                for inst in plate.findall("model_instance"):
                    im = {m.get("key"): m.get("value") for m in inst.findall("metadata")}
                    slots |= obj_ext.get(im.get("object_id"), {1})
                keys, missing = [], []
                for s in sorted(slots):
                    c = colors[s-1] if s-1 < len(colors) else None
                    t = types[s-1] if s-1 < len(types) else None
                    if c is None: missing.append(f"colour of slot {s}")
                    if t is None: missing.append(f"type of slot {s}")
                    keys.append(_key(t, c))
                missing.append("print time")
                jobs.append(Job(f"{base} / plate {meta.get('plater_id', len(jobs)+1)}",
                                frozenset(keys), None, "project.3mf", missing))
        if not jobs and not colors:
            # CAD export (e.g. Fusion 360): only core-3MF colour groups
            cols = _core_model_colours(z)
            keys = [_key(None, c) for c in cols]
            miss = [f"type of colour {c}" for c in cols] or ["filaments used"]
            miss += ["print time"]
            return [Job(base, frozenset(keys), None, "core.3mf", miss)]
        if not jobs:
            types = types + [None] * (len(colors) - len(types))
            keys = [_key(t, c) for t, c in zip(types, colors)]
            miss = [f"type of slot {i+1}" for i, t in enumerate(types) if t is None]
            miss += ["filaments used per plate", "print time"]
            jobs.append(Job(base, frozenset(keys), None, "project.3mf", miss))
        return jobs


def parse_file(path: str) -> List[Job]:
    p = path.lower()
    if p.endswith(".gcode") or p.endswith(".gco"):
        return parse_gcode(path)
    if p.endswith(".3mf"):
        return parse_3mf(path)
    raise ValueError(f"unsupported file: {path}")
