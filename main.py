from datetime import datetime
from pathlib import Path

from src.config_loader import load_config
from src.logger import setup_logger
from src.parser import collect_products, save_incremental

def main():
    config = load_config()

    errors_logger = setup_logger(
        "scraper_errors",
        "logs/scraper_errors.log"
    )
    quality_logger = setup_logger(
        "quality_alerts",
        "logs/quality_alerts.log"
    )

    items = collect_products(config, errors_logger, quality_logger)

    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(config["save_dir"]) / today
    output_file = output_dir / config["csv_filename"]

    added = save_incremental(items, output_file)
    print(f"Собрано валидных товаров: {len(items)}")
    print(f"Добавлено новых товаров: {added}")
    print(f"Файл: {output_file}")

if __name__ == "__main__":
    main()
