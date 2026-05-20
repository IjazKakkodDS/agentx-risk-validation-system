# AgentX Risk Validator -- Verified Model Metrics
Generated: 2026-05-20 17:29
Phase: 5B.5 -- FastAPI boundary added (metrics unchanged from 5B.1)

## Dataset
- Source: LendingClub public loan data, 2007-2018Q4 sample
- Total rows loaded: 5,000
- Rows after preprocessing: 5,000
- Features: 12
- Target: loan_status (0 = Fully Paid, 1 = Charged Off)
- Class balance: {'0': 0.8098, '1': 0.1902}

## Preprocessing
- Drop ID-like columns
- Impute numeric columns with column median
- LabelEncode all categorical columns
- StandardScaler: fit on training split only, applied inside Pipeline

## Train / Test Split
- 80% train / 20% test
- random_state=42, stratified on loan_status
- Train rows: 4,000
- Test rows: 1,000

## Model
- sklearn Pipeline: StandardScaler + LogisticRegression(max_iter=1000, random_state=42)
- Artifact: data/incoming_models/credit_model.pkl (includes scaler)

## Metrics
| Metric | Value |
|---|---|
| Accuracy | 0.804 |
| Precision | 0.35 |
| Recall | 0.0368 |
| F1 Score | 0.0667 |
| ROC-AUC | 0.6776 |

## Confusion Matrix
```
                Predicted 0   Predicted 1
  Actual 0           797            13
  Actual 1           183             7
```

## Limitations
- Logistic Regression is the baseline model. It is not the best-performing model
  for this dataset; it serves as the validation target for the AgentX pipeline.
- The dataset is a 5,000-row public sample, not a full production portfolio.
- Compliance outputs are LLM-generated illustrative examples, not regulatory assessments.

## Claim Safety
- These metrics may be cited after this phase.
- Prior metrics (ROC-AUC 0.668 from markdown report, 0.333 from JSON) are invalidated.
- See docs/evidence/metric_inconsistency_diagnosis.md for root cause.