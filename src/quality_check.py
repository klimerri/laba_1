import json
from pathlib import Path

def validate_product(item, quality_logger, quarantine_dir):
    errors = []

    if not item.get("name") or not str(item.get("name")).strip():
        errors.append("empty name")

    price = item.get("price")
    if price is None or price == 0:
        errors.append("price is None or 0")

    if errors:
        quality_logger.warning(
            "Invalid data | errors=%s | raw=%s",
            ", ".join(errors),
            json.dumps(item, ensure_ascii=False)
        )
        Path(quarantine_dir).mkdir(parents=True, exist_ok=True)
        raw_file = Path(quarantine_dir) / "invalid_data.jsonl"
        with raw_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")
        return False

    return True
