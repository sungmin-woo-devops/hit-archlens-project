import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple
from rapidfuzz import process, fuzz

@dataclass
class Taxonomy:
    canonical_to_aliases: Dict[str, List[str]]
    alias_to_canonical: Dict[str, str]
    names: List[str]

    @classmethod
    def from_csv(cls, path: str) -> "Taxonomy":
        """
        Expect CSV columns like:
          canonical,aliases
        where aliases is '|' separated optional list
        If your CSV has different columns (e.g., 'service','family', etc),
        tweak the parsing below accordingly.
        """
        df = pd.read_csv(path)
        # Heuristics: find best columns
        cols = [c.lower() for c in df.columns]
        try:
            name_col = next(c for c in df.columns if c.lower() in ("canonical","name","service","label"))
        except StopIteration:
            name_col = df.columns[0]
        alias_col = None
        for c in df.columns:
            if c.lower() in ("aliases","alias","aka"):
                alias_col = c
                break

        canonical_to_aliases = {}
        alias_to_canonical = {}

        for _, row in df.iterrows():
            canon = str(row[name_col]).strip()
            aliases = []
            if alias_col and not pd.isna(row[alias_col]):
                aliases = [a.strip() for a in str(row[alias_col]).split("|") if a.strip()]
            all_keys = set([canon] + aliases)
            canonical_to_aliases[canon] = list(all_keys)
            for k in all_keys:
                alias_to_canonical[k.lower()] = canon

        names = list(canonical_to_aliases.keys())
        return cls(canonical_to_aliases, alias_to_canonical, names)

    def normalize(self, s: str) -> Tuple[str, float]:
        """Map arbitrary text to canonical via fuzzy matching + alias map."""
        key = s.strip().lower()
        if key in self.alias_to_canonical:
            return self.alias_to_canonical[key], 1.0
        # fuzzy to all aliases
        best = process.extractOne(
            key,
            list(self.alias_to_canonical.keys()),
            scorer=fuzz.WRatio
        )
        if best:
            alias, score, _ = best
            return self.alias_to_canonical[alias], score/100.0
        # fallback to canonical names
        best2 = process.extractOne(
            key, self.names, scorer=fuzz.WRatio
        )
        if best2:
            name, score, _ = best2
            return name, score/100.0
        return s, 0.0
