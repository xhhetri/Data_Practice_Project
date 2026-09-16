from src.analysis import clean, eda, model, validate
 
 
def main() -> None:
    print("=" * 60)
    print("STEP 1/4 -- Clean & merge source data")
    print("=" * 60)
    clean.run()
 
    print("\n" + "=" * 60)
    print("STEP 2/4 -- Exploratory data analysis")
    print("=" * 60)
    eda.run()
 
    print("\n" + "=" * 60)
    print("STEP 3/4 -- Model training & evaluation")
    print("=" * 60)
    model.run()
 
    print("\n" + "=" * 60)
    print("STEP 4/4 -- Data quality validation")
    print("=" * 60)
    validate.run()
 
    print("\nDone. See data/processed/, reports/figures/, "
          "reports/model_results/, and reports/validation/.")
 
 
if __name__ == "__main__":
    main()
