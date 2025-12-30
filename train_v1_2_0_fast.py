"""Fast training for v1.2.0 - 3 folds instead of 5, fewer estimators."""

import json
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score, roc_auc_score
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

from src.ml.features import add_feature_columns
from src.ml.validation import validate_ml_data

warnings.filterwarnings('ignore')

print("="*80)
print("🚀 F1 ML TRAINING v1.2.0 - ENHANCED FEATURES (FAST MODE)")
print("="*80)

# Load & filter data
df = pd.read_parquet('data/processed/f1_historical_data.parquet')
df_2023 = df[df['year'] == 2023].copy()
print(f"\n📊 Data: {len(df_2023)} samples (2023 only)")

# Extract targets
y_position = df_2023['race_position'].copy()
y_points = df_2023['points'].copy()
y_winner = df_2023['winner'].copy()
dnf_mask = df_2023['dnf'].copy()

# Add ENHANCED features
print("\n🔧 Engineering features (ENHANCED MODE)...")
df_2023 = add_feature_columns(df_2023, enhanced=True)
print(f"   Features after enhancement: {len(df_2023.columns)}")

# Prepare features
feature_cols_to_drop = [
    'race_position', 'points', 'winner', 'dnf', 'status', 'fastest_lap_time',
    'driver_code', 'constructor', 'circuit_name', 'country', 'event_name',
]
X = df_2023.drop(columns=[c for c in feature_cols_to_drop if c in df_2023.columns])

# Validate
print("\n✅ Validating...")
validate_ml_data(X, strict=True)

X_numeric = X.drop(columns=['year', 'round_number'])
print(f"   Final feature count: {len(X_numeric.columns)}")

# Filter DNFs
no_dnf_idx = (dnf_mask == 0) & (~y_position.isna())
X_no_dnf = X_numeric[no_dnf_idx].copy()
y_position_no_dnf = y_position[no_dnf_idx].copy()
y_points_no_dnf = y_points[no_dnf_idx].copy()

print(f"\n🚗 Samples: {len(X_numeric)} total, {len(X_no_dnf)} finished")

# K-Fold (3 folds for speed)
kfold = KFold(n_splits=3, shuffle=True, random_state=42)
metrics = {'winner': {'roc_auc': [], 'f1': []}, 'position': {'rmse': [], 'r2': []}, 'points': {'rmse': [], 'r2': []}}

print("\n🎯 Training (3-Fold CV)...")

# Winner
print("   Winner...")
for train_idx, test_idx in kfold.split(X_numeric):
    clf = RandomForestClassifier(n_estimators=100, max_depth=15, min_samples_split=10, 
                                   min_samples_leaf=4, class_weight='balanced', random_state=42, n_jobs=-1)
    clf.fit(X_numeric.iloc[train_idx], y_winner.iloc[train_idx])
    y_proba = clf.predict_proba(X_numeric.iloc[test_idx])[:, 1]
    y_pred = clf.predict(X_numeric.iloc[test_idx])
    metrics['winner']['roc_auc'].append(roc_auc_score(y_winner.iloc[test_idx], y_proba))
    metrics['winner']['f1'].append(f1_score(y_winner.iloc[test_idx], y_pred))

# Position & Points
print("   Position & Points...")
for train_idx, test_idx in kfold.split(X_no_dnf):
    # Position
    reg_pos = XGBRegressor(n_estimators=100, max_depth=8, learning_rate=0.05, 
                           subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1)
    reg_pos.fit(X_no_dnf.iloc[train_idx], y_position_no_dnf.iloc[train_idx])
    y_pred_pos = reg_pos.predict(X_no_dnf.iloc[test_idx])
    metrics['position']['rmse'].append(np.sqrt(mean_squared_error(y_position_no_dnf.iloc[test_idx], y_pred_pos)))
    metrics['position']['r2'].append(r2_score(y_position_no_dnf.iloc[test_idx], y_pred_pos))
    
    # Points
    reg_pts = XGBRegressor(n_estimators=100, max_depth=8, learning_rate=0.05, 
                           subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1)
    reg_pts.fit(X_no_dnf.iloc[train_idx], y_points_no_dnf.iloc[train_idx])
    y_pred_pts = reg_pts.predict(X_no_dnf.iloc[test_idx])
    metrics['points']['rmse'].append(np.sqrt(mean_squared_error(y_points_no_dnf.iloc[test_idx], y_pred_pts)))
    metrics['points']['r2'].append(r2_score(y_points_no_dnf.iloc[test_idx], y_pred_pts))

# Results
print("\n📈 RESULTS:")
print(f"   Winner ROC-AUC:  {np.mean(metrics['winner']['roc_auc']):.4f} ± {np.std(metrics['winner']['roc_auc']):.4f}")
print(f"   Winner F1:       {np.mean(metrics['winner']['f1']):.4f} ± {np.std(metrics['winner']['f1']):.4f}")
print(f"   Position RMSE:   {np.mean(metrics['position']['rmse']):.4f} ± {np.std(metrics['position']['rmse']):.4f}")
print(f"   Position R²:     {np.mean(metrics['position']['r2']):.4f} ± {np.std(metrics['position']['r2']):.4f}")
print(f"   Points RMSE:     {np.mean(metrics['points']['rmse']):.4f} ± {np.std(metrics['points']['rmse']):.4f}")
print(f"   Points R²:       {np.mean(metrics['points']['r2']):.4f} ± {np.std(metrics['points']['r2']):.4f}")

# Train finals
print("\n🎯 Training final models...")
clf_final = RandomForestClassifier(n_estimators=150, max_depth=15, min_samples_split=10, 
                                   min_samples_leaf=4, class_weight='balanced', random_state=42, n_jobs=-1)
clf_final.fit(X_numeric, y_winner)

reg_pos_final = XGBRegressor(n_estimators=150, max_depth=8, learning_rate=0.05, 
                             subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1)
reg_pos_final.fit(X_no_dnf, y_position_no_dnf)

reg_pts_final = XGBRegressor(n_estimators=150, max_depth=8, learning_rate=0.05, 
                             subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1)
reg_pts_final.fit(X_no_dnf, y_points_no_dnf)

# Save
print("\n💾 Saving...")
models_dir = Path("models/v1.2.0")
models_dir.mkdir(exist_ok=True)

pickle.dump(clf_final, open(models_dir / "classifier_winner.pkl", "wb"))
pickle.dump(reg_pos_final, open(models_dir / "regressor_position.pkl", "wb"))
pickle.dump(reg_pts_final, open(models_dir / "regressor_points.pkl", "wb"))

json.dump(X_numeric.columns.tolist(), open(models_dir / "features.json", "w"), indent=2)

metrics_summary = {
    'version': '1.2.0',
    'trained_on': datetime.now().isoformat(),
    'num_features': len(X_numeric.columns),
    'enhanced_features': True,
    'validation': '3-Fold CV',
    'metrics': {
        'winner': {'roc_auc': float(np.mean(metrics['winner']['roc_auc'])), 'f1': float(np.mean(metrics['winner']['f1']))},
        'position': {'rmse': float(np.mean(metrics['position']['rmse'])), 'r2': float(np.mean(metrics['position']['r2']))},
        'points': {'rmse': float(np.mean(metrics['points']['rmse'])), 'r2': float(np.mean(metrics['points']['r2']))},
    }
}
json.dump(metrics_summary, open(models_dir / "metrics.json", "w"), indent=2)

# Feature importances
pd.DataFrame({'feature': X_numeric.columns.tolist(), 'importance': clf_final.feature_importances_}).sort_values('importance', ascending=False).to_csv(models_dir / "feature_importances_classifier.csv", index=False)
pd.DataFrame({'feature': X_numeric.columns.tolist(), 'importance': reg_pos_final.feature_importances_}).sort_values('importance', ascending=False).to_csv(models_dir / "feature_importances_position.csv", index=False)

# Update latest
latest = Path("models/latest")
if latest.exists() or latest.is_symlink():
    latest.unlink()
latest.symlink_to("v1.2.0")

print(f"✅ Saved to {models_dir}")
print("✅ Updated models/latest -> v1.2.0")

# Comparison
print("\n" + "="*80)
print("📊 v1.1.0 vs v1.2.0 COMPARISON")
print("="*80)
print(f"   Position RMSE:   4.71 → {np.mean(metrics['position']['rmse']):.2f}   ({((np.mean(metrics['position']['rmse'])/4.71-1)*100):+.1f}%)")
print(f"   Position R²:     0.32 → {np.mean(metrics['position']['r2']):.2f}   ({((np.mean(metrics['position']['r2'])/0.32-1)*100):+.1f}%)")
print(f"   Features:        29 → {len(X_numeric.columns)}   (+{len(X_numeric.columns)-29})")
print("="*80)
