#!/usr/bin/env python3
"""
run_pipeline.py
----------------
Single command to run the whole analysis: clean -> EDA -> model training.

Usage:
    python run_pipeline.py

Outputs:
    data/processed/          cleaned, merged tables
    reports/figures/         EDA + forecast plots (PNG)
    reports/model_results/   metrics.json, trained model (.pkl)
"""

from src.analysis import clean, eda, model


def main() -> None:
    print("=" * 60)
    print("STEP 1/3 -- Clean & merge source data")
    print("=" * 60)
    clean.run()

    print("\n" + "=" * 60)
    print("STEP 2/3 -- Exploratory data analysis")
    print("=" * 60)
    eda.run()

    print("\n" + "=" * 60)
    print("STEP 3/3 -- Model training & evaluation")
    print("=" * 60)
    model.run()

    print("\nDone. See data/processed/, reports/figures/, reports/model_results/")


if __name__ == "__main__":
    main()
