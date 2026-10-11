"""SQLite catalog: raw artifacts, specimen candidates and provenance-rich observations."""
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .common import canonical, digest

FAMILIES = ("atomic_ensemble", "trapped_atom_ion", "rare_earth_solid",
            "defect_spin", "molecular_spin", "negative_ion")
EVIDENCE = ("experimental", "curated_experimental", "fit_to_experiment",
            "evaluated_reference", "computed", "hypothetical", "unknown")
SYMBOLS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni "
           "Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe "
           "Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au "
           "Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf "
           "Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()


class Catalog:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.in_transaction = False
        self.db.execute("PRAGMA foreign_keys = ON")
        for table in ("artifacts", "candidates", "observations"):
            self.db.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.db.commit()

    @contextmanager
    def transaction(self):
        if self.in_transaction:
            raise ValueError("Nested catalog transaction")
        self.in_transaction = True
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        finally:
            self.in_transaction = False

    def close(self):
        self.db.close()

    def put(self, table, record):
        if table not in {"artifacts", "candidates", "observations"}:
            raise ValueError("Invalid catalog table")
        if table == "observations":
            for key in ("subject_id", "quantity", "value", "unit", "conditions", "provenance",
                        "evidence_kind", "source_location"):
                if key not in record:
                    raise ValueError("Observation lacks " + key)
            if record["evidence_kind"] not in EVIDENCE or not record["provenance"]:
                raise ValueError("Invalid observation evidence/provenance")
        if table == "candidates":
            if record.get("family") not in FAMILIES:
                raise ValueError("Unsupported memory family")
        record = dict(record)
        record.setdefault("id", digest(record))
        old = self.db.execute(f"SELECT payload FROM {table} WHERE id=?", (record["id"],)).fetchone()
        payload = canonical(record)
        if old and old[0] != payload:
            raise ValueError("Immutable catalog identity collision")
        self.db.execute(f"INSERT OR IGNORE INTO {table} VALUES (?,?)", (record["id"], payload))
        if not self.in_transaction:
            self.db.commit()
        return record["id"]

    def rows(self, table):
        if table not in {"artifacts", "candidates", "observations"}:
            raise ValueError("Invalid table")
        return [json.loads(x[0]) for x in self.db.execute(f"SELECT payload FROM {table} ORDER BY id")]

    def summary(self):
        return {t: self.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("artifacts", "candidates", "observations")}


def composition(formula):
    """Flat elemental formula only. Parentheses, hydrates and charges require reviewed mapping."""
    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    if "".join(a+b for a, b in tokens) != formula or not tokens:
        return None
    result = {}
    for el, count in tokens:
        if el not in SYMBOLS:
            return None
        n = int(count or 1)
        if n <= 0:
            return None
        result[el] = result.get(el, 0) + n
    return result


def expand_candidates(plan):
    """Inventory of explicitly requested combinations, never a list of stable bound species."""
    import itertools
    family = plan["family"]
    if family not in FAMILIES:
        raise ValueError("Unknown family")
    result = []
    for template in plan["templates"]:
        geom = template.get("geometry_angstrom", [])
        comp = template.get("composition") or {}
        if not comp or any(el not in SYMBOLS or not isinstance(n, int) or isinstance(n, bool)
                           or n < 1 for el, n in comp.items()):
            raise ValueError("Candidate needs a valid elemental composition")
        sites = plan.get("isotope_choices_by_site", {})
        if sites and not geom:
            raise ValueError("Site isotope substitutions require explicit geometry")
        keys = sorted(sites, key=int)
        for key in keys:
            index = int(key)
            if index < 0 or index >= len(geom):
                raise ValueError("Isotope site outside geometry")
            for isotope in sites[key]:
                if isotope.split("-")[0] != geom[index][0]:
                    raise ValueError("Isotope substitution changes the element at this site")
        choices = itertools.product(*(sites[k] for k in keys)) if keys else [()]
        for isotopes in choices:
            for charge, spin, host in itertools.product(plan["charges_e"], plan["spin_2S"],
                                                        plan.get("hosts", [template.get("host")])):
                if not isinstance(charge, int) or isinstance(charge, bool) or not isinstance(spin, int) or isinstance(spin, bool) or spin < 0:
                    raise ValueError("Integer charge and nonnegative integer 2S required")
                electrons = sum((SYMBOLS.index(e)+1)*n for e, n in comp.items()) - charge
                if electrons < spin or (electrons - spin) % 2:
                    continue
                row = {**template, "family": family, "charge_e": charge, "spin_2S": spin,
                       "host": host, "isotopes_by_site": dict(zip(keys, isotopes)),
                       "status": "unassessed", "bound_state_exists": None,
                       "optical_interface": None, "network_channel_validated": False,
                       "provenance": template.get("provenance", []) +
                                     [{"kind": "generated_combination", "plan_hash": digest(plan)}]}
                row["id"] = digest(row)[:24]
                result.append(row)
                if len(result) > plan.get("max_candidates", 10000):
                    raise ValueError("Candidate count exceeds explicit budget")
    return result
