"""
Python port of u2b3k/uz-hungen (C# Hunspell dictionary generator).

Generates Hunspell .aff + .dic files from:
  - Base words with grammatical tags
  - Affix rules (.qoida style)

Uses existing uzbek_affix_rules DB as source.
Can extend dictionary on-the-fly with new pharma terminology.

Usage:
    gen = UzbekDictGenerator()
    gen.add_base_word("парацетамол", tags=["noun"])
    aff_content, dic_content = gen.generate()
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("uzbek_dict_generator")


class UzbekDictGenerator:
    """Generate Hunspell .aff + .dic files from DB affix rules + custom base words."""

    def __init__(self, script: str = "latin"):
        self.script = script
        self.base_words: List[Dict[str, Any]] = []
        self.affix_rules: List[Dict[str, Any]] = []
        self._load_affix_rules()

    def _load_affix_rules(self):
        """Load all affix rules from uzbek_affix_rules DB table."""
        try:
            import affix_db_loader
            all_rules = affix_db_loader.load_all_rules()
            self.affix_rules = [r for r in all_rules if r.get("script") == self.script]
            logger.info(f"[generator] Loaded {len(self.affix_rules)} rules ({self.script})")
        except Exception as e:
            logger.warning(f"[generator] Could not load affix rules: {e}")
            self.affix_rules = []

    def add_base_word(self, word: str, flags: List[str] = None, tags: List[str] = None):
        """Add a base word with optional Hunspell flags or semantic tags."""
        if not word or not word.strip():
            return
        self.base_words.append({
            "word": word.strip(),
            "flags": flags or [],
            "tags": tags or [],
        })

    def add_pharma_term(self, inn: str, brand: str = "", atc: str = ""):
        """Convenience: add pharma drug with standard flags."""
        # Noun-like flags (most pharma terms)
        self.add_base_word(inn, flags=["N"], tags=["noun", "pharma", "inn"])
        if brand and brand.lower() != inn.lower():
            self.add_base_word(brand, flags=["N"], tags=["noun", "pharma", "brand"])

    def _flags_to_string(self, flags: List[str]) -> str:
        """Convert flag list to Hunspell slash-separated format."""
        if not flags:
            return ""
        return "/" + "".join(flags)

    def generate_dic(self) -> str:
        """Generate .dic file content."""
        lines = [str(len(self.base_words))]
        for bw in self.base_words:
            word = bw["word"]
            flag_str = self._flags_to_string(bw.get("flags", []))
            lines.append(word + flag_str)
        return "\n".join(lines) + "\n"

    def generate_aff(self) -> str:
        """Generate .aff file content from DB rules."""
        lines = []
        lines.append("SET UTF-8")
        lines.append("LANG uz_UZ" if self.script == "latin" else "LANG uz_UZ_Cyrl")
        lines.append("TRY eauonirltsdkymhblzpgvfcwxj")
        lines.append("WORDCHARS 'ʻʼ")
        lines.append("")

        # Group rules by flag
        by_flag: Dict[str, List[Dict[str, Any]]] = {}
        for r in self.affix_rules:
            flag = r.get("flag", "")
            if not flag:
                continue
            by_flag.setdefault(flag, []).append(r)

        # Emit SFX blocks
        for flag, rules in sorted(by_flag.items()):
            if not rules:
                continue
            rule_type = rules[0].get("type", "SFX")
            lines.append(f"{rule_type} {flag} Y {len(rules)}")
            for r in rules:
                strip = r.get("strip") or "0"
                affix = r.get("affix") or "0"
                condition = r.get("condition") or "."
                morph = r.get("morph_tags") or ""
                line = f"{rule_type} {flag} {strip} {affix} {condition}"
                if morph:
                    line += f" {morph}"
                lines.append(line)
            lines.append("")

        return "\n".join(lines)

    def generate_inflected_forms(self, max_per_word: int = 20) -> List[str]:
        """Generate all inflected forms for loaded base words."""
        import affix_db_loader
        results = []
        for bw in self.base_words:
            word = bw["word"]
            flags = bw.get("flags", [])
            for flag in flags:
                rules = affix_db_loader.rules_by_flag(flag)
                for rule in rules[:max_per_word]:
                    inflected = affix_db_loader.apply_affix(word, rule)
                    if inflected:
                        results.append(inflected)
        return results

    def generate(self) -> Tuple[str, str]:
        """Return (aff_content, dic_content)."""
        return self.generate_aff(), self.generate_dic()

    def save_to_disk(self, base_path: str):
        """Write .aff and .dic files."""
        aff, dic = self.generate()
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        with open(base_path + ".aff", "w", encoding="utf-8") as f:
            f.write(aff)
        with open(base_path + ".dic", "w", encoding="utf-8") as f:
            f.write(dic)
        logger.info(f"[generator] Wrote {base_path}.aff + .dic")


def generate_pharma_dictionary() -> Dict[str, Any]:
    """Build extended pharma Hunspell dict from drugs + medical_terms tables."""
    gen = UzbekDictGenerator(script="latin")
    try:
        import sqlite3
        db_path = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Add drugs
        try:
            cur.execute("SELECT inn, brand_name, atc_code FROM drugs LIMIT 10000")
            for inn, brand, atc in cur.fetchall():
                if inn:
                    gen.add_pharma_term(inn, brand or "", atc or "")
        except Exception:
            pass

        # Add medical terms
        try:
            cur.execute("SELECT term_uz, term_ru, term_en FROM medical_terms LIMIT 10000")
            for uz, ru, en in cur.fetchall():
                if uz:
                    gen.add_base_word(uz, flags=["N"], tags=["noun", "medical"])
                if ru:
                    gen.add_base_word(ru, flags=["N"], tags=["noun", "medical", "russian"])
                if en:
                    gen.add_base_word(en, flags=["N"], tags=["noun", "medical", "english"])
        except Exception:
            pass

        conn.close()
    except Exception as e:
        logger.warning(f"[pharma dict] {e}")

    inflected = gen.generate_inflected_forms(max_per_word=10)
    return {
        "base_count": len(gen.base_words),
        "inflected_count": len(inflected),
        "aff_size": len(gen.generate_aff()),
        "dic_size": len(gen.generate_dic()),
    }
