#!/usr/bin/env python3
"""Drive the model logger example with fixture data."""

import argparse
import json
from pathlib import Path

from model_logger import ModelLogger

from labapi import Client


def main() -> None:
    """Run the model logger fixture script."""
    parser = argparse.ArgumentParser(description="Test ModelLogger with files")
    parser.add_argument(
        "--notebook", "-n", required=True, help="LabArchives notebook name"
    )
    args = parser.parse_args()

    data_dir = Path(__file__).parent / "test_data"

    # 1. Load Metrics
    with (data_dir / "metrics.json").open("r", encoding="utf-8") as f:
        metrics = json.load(f)

    # 2. Load Results
    with (data_dir / "results.csv").open("rb") as f:
        results_bytes = f.read()

    # 3. Load Figure
    with (data_dir / "dummy_figure.png").open("rb") as f:
        figure_bytes = f.read()

    with Client() as client:
        user = client.default_authenticate()
        logger = ModelLogger(notebook_name=args.notebook, user=user)
        logger.log(
            tags=["production", ["cnn", "pytorch"], "experiment-12"],
            metrics=metrics,
            results=results_bytes,
            figures=[figure_bytes],
            commit="f7e2a4c1",
        )


if __name__ == "__main__":
    main()
