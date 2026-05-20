from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def validate_data(df):
    report = {
        "missing_values": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "class_distribution": df["loan_status"].value_counts(normalize=True).round(3).to_dict(),
        "summary_statistics": df.describe().round(2).to_dict(),
    }
    logger.info(
        "Data validation complete -- missing: %d, duplicates: %d",
        report["missing_values"],
        report["duplicate_rows"],
    )
    return report
