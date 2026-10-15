# Student Performance Predictor

The initial API uses a transparent weighted baseline score so the feature works without a separately supplied dataset. Inputs are previous marks, attendance, study hours per day, and assignment completion. This is **not a trained or validated ML model** and must not be presented as a reliable prediction of a student's future grades.

For a genuine machine-learning extension:
1. Obtain a permitted, anonymized dataset with a clear target variable and consent/legal basis.
2. Split train/validation/test sets before model selection.
3. Train and evaluate a suitable regression model (e.g., scikit-learn RandomForestRegressor or HistGradientBoostingRegressor).
4. Compare against a simple baseline and report MAE/RMSE and limitations.
5. Check bias and data leakage; avoid using the estimate for high-stakes student decisions.
6. Version the model, save preprocessing with the model, and add tests for input bounds.
