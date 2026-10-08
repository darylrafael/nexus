import logging
import re
from typing import Any, Optional

logger = logging.getLogger("nexus.validator")

# --- 1. Commodity Economics ---
COMMODITY_ECONOMICS = {
    "CPO": {
        "producers": ["AALI", "LSIP", "SIMP", "TBLA"],
        "consumers": ["UNVR", "ICBP", "INDF", "MYOR"],
        "note": "Rising CPO price = margin expansion for planters, margin compression for consumer goods manufacturers."
    },
    "Coal": {
        "producers": ["ADRO", "PTBA", "ITMG", "HRUM", "BYAN", "BUMI"],
        "consumers": ["electricity-intensive manufacturers, cement"],
        "note": "Rising coal = revenue uplift for miners, higher input cost for power-intensive industries."
    },
    "Nickel": {
        "producers": ["INCO", "ANTM", "MBMA", "NCKL"],
        "consumers": ["EV battery supply chain"],
        "note": "Rising nickel = good for miners, raises battery production costs."
    },
    "Crude Oil": {
        "producers": ["MEDC", "ENRG", "RUIS"],
        "consumers": ["transport, petrochemical, aviation"],
        "note": "Rising oil = revenue boost for oil firms, cost pressure for transport and industrial sectors."
    }
}


def build_commodity_context(commodity_text: str) -> str:
    """Inject correct producer/consumer logic into commodity data."""
    context = commodity_text + "\n\n## Commodity Economics Rules (DO NOT REVERSE):\n"
    for commodity, data in COMMODITY_ECONOMICS.items():
        producers = ", ".join(data["producers"]) if isinstance(data["producers"], list) else data["producers"]
        consumers = ", ".join(data["consumers"]) if isinstance(data["consumers"], list) else data["consumers"]
        context += f"- {commodity}: Producers (benefit from price rise) = {producers}. Consumers (hurt by price rise) = {consumers}. {data['note']}\n"
    return context


# --- 2. Numeric-Consistency Checker (Bilingual: ID & EN) ---
POSITIVE_TERMS = [
    "naik", "menguat", "mengalami kenaikan", "kenaikan", "lonjakan", "menguat sebesar",
    "rose", "rise", "gained", "gain", "climbed", "rallied", "uptick", "increased", "jumped"
]

NEGATIVE_TERMS = [
    "turun", "melemah", "merosot", "tertekan", "anjlok", "penurunan", "melemah sebesar",
    "fell", "dropped", "declined", "slid", "slipped", "weakened", "lost", "dipped"
]


def check_numeric_consistency(
    text: str,
    reference_data: Optional[dict[str, Any]] = None
) -> list[dict[str, Any]]:
    """Verify sign/direction word consistency in Indonesian and English.

    FLAGS inconsistencies rather than mutating LLM text silently.
    """
    flags: list[dict[str, Any]] = []
    lines = text.splitlines()

    for line_idx, line in enumerate(lines, 1):
        line_clean = line.strip()
        if not line_clean:
            continue

        line_lower = line_clean.lower()

        # Check positive terms paired with negative percentages (e.g. 'naik -1.5%' or 'rose -0.8%')
        has_negative_pct = bool(re.search(r'[‑\-]\s*\d+(?:[.,]\d+)?\s*%', line_clean))
        has_positive_pct = bool(re.search(r'\+\s*\d+(?:[.,]\d+)?\s*%', line_clean))

        has_pos_term = any(re.search(r'\b' + re.escape(term) + r'\b', line_lower) for term in POSITIVE_TERMS)
        has_neg_term = any(re.search(r'\b' + re.escape(term) + r'\b', line_lower) for term in NEGATIVE_TERMS)

        if has_negative_pct and has_pos_term and not has_neg_term:
            flag = {
                "type": "sign_contradiction",
                "line_number": line_idx,
                "line": line_clean,
                "issue": "Positive direction term used with negative percentage",
            }
            logger.warning("Numeric consistency flag: %s in line: %s", flag["issue"], line_clean)
            flags.append(flag)

        elif has_positive_pct and has_neg_term and not has_pos_term:
            flag = {
                "type": "sign_contradiction",
                "line_number": line_idx,
                "line": line_clean,
                "issue": "Negative direction term used with positive percentage",
            }
            logger.warning("Numeric consistency flag: %s in line: %s", flag["issue"], line_clean)
            flags.append(flag)

        # Cross-reference with external reference_data if provided
        if reference_data:
            for entity, ref_val in reference_data.items():
                if ref_val is None or not isinstance(ref_val, (int, float)):
                    continue
                if entity.lower() in line_lower:
                    if ref_val > 0.1 and has_neg_term and not has_pos_term:
                        flag = {
                            "type": "reference_data_contradiction",
                            "entity": entity,
                            "reference_value": ref_val,
                            "line_number": line_idx,
                            "line": line_clean,
                            "issue": f"{entity} is positive ({ref_val:+.2f}%) in data, but line uses negative term",
                        }
                        logger.warning("Numeric consistency flag: %s", flag["issue"])
                        flags.append(flag)
                    elif ref_val < -0.1 and has_pos_term and not has_neg_term:
                        flag = {
                            "type": "reference_data_contradiction",
                            "entity": entity,
                            "reference_value": ref_val,
                            "line_number": line_idx,
                            "line": line_clean,
                            "issue": f"{entity} is negative ({ref_val:+.2f}%) in data, but line uses positive term",
                        }
                        logger.warning("Numeric consistency flag: %s", flag["issue"])
                        flags.append(flag)

    return flags


def validate(text: str, reference_data: Optional[dict[str, Any]] = None) -> str:
    """Run non-destructive validation pass.

    Never mutates LLM text silently; checks consistency and logs any
    detected flags.
    """
    flags = check_numeric_consistency(text, reference_data)
    if flags:
        print(f"  [validator] ⚠️ Flagged {len(flags)} directional/numeric inconsistencies (text not mutated).")
    else:
        print("  [validator] ✅ Directional and numeric language consistent.")
    return text


# Backwards compatibility alias
validate_predictions_post_hoc = validate
