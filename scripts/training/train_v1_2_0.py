"""Quick training script for v1.2.0 models with enhanced features."""

import json
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

from src.ml.features import add_feature_columns
from src.ml.validation import validate_ml_data

warnings.filterwarnings('ignore')

print("="*80)
print("🚀 F1 ML MODEL TRAINING - v1.2.0 (Enhanced Features)")
print("="*80)

# Load data
print("\n📊 Loading data...")
df = pd.read_parquet('data/processed/f1_historical_data.parquet')
print(f"   Loaded: {len(df)} rows, {len(df.columns)} columns")

# Filter to 2023 only (2024 insufficient for test set)
df_2023 = df[df['year'] == 2023].copy()
print(f"   Filtered to 2023: {len(df_2023)} rows")

# Extract targets BEFORE feature engineering
y_position = df_2023['race_position'].copy()
y_points = df_2023['points'].copy()
y_winner = df_2023['winner'].copy()
dnf_mask = df_2023['dnf'].copy()

# Add enhanced features
print("\n🔧 Engineering features...")
df_2023 = add_feature_columns(df_2023, enhanced=True)
print(f"   After feature engineering: {len(df_2023.columns)} columns")

# Drop targets and identifiers
print("\n📋 Preparing features...")
feature_cols_to_drop = [
    # Targets
    'race_position', 'points', 'winner', 'dnf', 'status', 'fastest_lap_time',
    # Identifiers
    'driver_code', 'constructor', 'circuit_name', 'country', 'event_name',
]

X = df_2023.drop(columns=[c for c in feature_cols_to_drop if c in df_2023.columns])

# Validate AFTER dropping targets
print("\n✅ Validating features...")
validate_ml_data(X, strict=True)
print("   ✅ Validation passed (no data leakage)")

X_numeric = X.drop(columns=['year', 'round_number'])

print(f"   Feature matrix: {X_numeric.shape}")
print(f"   Features: {len(X_numeric.columns)}")

# Filter out DNFs for position/points prediction
no_dnf_idx = (dnf_mask == 0) & (~y_position.isna())
print(f"\n🚗 Filtering DNFs:")
print(f"   Total samples: {len(X_numeric)}")
print(f"   DNFs: {(dnf_mask == 1).sum()}")
print(f"   Finished races (for position/points): {no_dnf_idx.sum()}")

X_no_dnf = X_numeric[no_dnf_idx].copy()
y_position_no_dnf = y_position[no_dnf_idx].copy()
y_points_no_dnf = y_points[no_dnf_idx].copy()

# Save feature names
features_list = X_numeric.columns.tolist()

# K-Fold CV
print("\n🔄 Setting up K-Fold Cross-Validation...")
kfold_all = KFold(n_splits=5, shuffle=True, random_state=42)
kfold_no_dnf = KFold(n_splits=5, shuffle=True, random_state=42)

# Initialize metrics storage
metrics = {
    'winner': {'roc_auc': [], 'f1': [], 'accuracy': []},
    'position': {'rmse': [], 'r2': []},
    'points': {'rmse': [], 'r2': []},
}

# Train models
print("\n🎯 Training models...")

# Winner prediction (uses all data including DNFs)
print("\n   📊 Winner Prediction (all samples):")
for fold_idx, (train_idx, test_idx) in enumerate(kfold_all.split(X_numeric), 1):
    X_train, X_test = X_numeric.iloc[train_idx], X_numeric.iloc[test_idx]
    y_train_w, y_test_w = y_winner.iloc[train_idx], y_winner.iloc[test_idx]
    
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=15, min_samples_split=10,
        min_samples_leaf=4, class_weight='balanced', random_state=42
    )
    clf.fit(X_train, y_train_w)
    y_pred_w = clf.predict(X_test)
    y_proba_w = clf.predict_proba(X_test)[:, 1]
    
    metrics['winner']['roc_auc'].append(roc_auc_score(y_test_w, y_proba_w))
    metrics['winner']['f1'].append(f1_score(y_test_w, y_pred_w))
    metrics['winner']['accuracy'].append(accuracy_score(y_test_w, y_pred_w))
    
    print(f"      Fold {fold_idx}/5: ROC-AUC = {metrics['winner']['roc_auc'][-1]:.4f}")

# Position & Points prediction (only finished races)
print(f"\n   📊 Position/Points Prediction ({no_dnf_idx.sum()} samples, no DNFs):")
for fold_idx, (train_idx, test_idx) in enumerate(kfold_no_dnf.split(X_no_dnf), 1):
    X_train, X_test = X_no_dnf.iloc[train_idx], X_no_dnf.iloc[test_idx]
    y_train_pos, y_test_pos = y_position_no_dnf.iloc[train_idx], y_position_no_dnf.iloc[test_idx]
    y_train_pts, y_test_pts = y_points_no_dnf.iloc[train_idx], y_points_no_dnf.iloc[test_idx]
    
    # Position Regressor
    reg_pos = XGBRegressor(
        n_estimators=200, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42
    )
    reg_pos.fit(X_train, y_train_pos)
    y_pred_pos = reg_pos.predict(X_test)
    
    metrics['position']['rmse'].append(np.sqrt(mean_squared_error(y_test_pos, y_pred_pos)))
    metrics['position']['r2'].append(r2_score(y_test_pos, y_pred_pos))
    
    # Points Regressor
    reg_pts = XGBRegressor(
        n_estimators=200, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42
    )
    reg_pts.fit(X_train, y_train_pts)
    y_pred_pts = reg_pts.predict(X_test)
    
    metrics['points']['rmse'].append(np.sqrt(mean_squared_error(y_test_pts, y_pred_pts)))
    metrics['points']['r2'].append(r2_score(y_test_pts, y_pred_pts))
    
    print(f"      Fold {fold_idx}/5: Position RMSE = {metrics['position']['rmse'][-1]:.4f}, Points RMSE = {metrics['points']['rmse'][-1]:.4f}")

# Compute mean metrics
print("\n📈 Cross-Validation Results:")
print("\n   WINNER PREDICTION:")
print(f"      ROC-AUC:  {np.mean(metrics['winner']['roc_auc']):.4f} ± {np.std(metrics['winner']['roc_auc']):.4f}")
print(f"      F1-Score: {np.mean(metrics['winner']['f1']):.4f} ± {np.std(metrics['winner']['f1']):.4f}")
print(f"      Accuracy: {np.mean(metrics['winner']['accuracy']):.4f} ± {np.std(metrics['winner']['accuracy']):.4f}")

print("\n   POSITION PREDICTION:")
print(f"      RMSE: {np.mean(metrics['position']['rmse']):.4f} ± {np.std(metrics['position']['rmse']):.4f}")
print(f"      R²:   {np.mean(metrics['position']['r2']):.4f} ± {np.std(metrics['position']['r2']):.4f}")

print("\n   POINTS PREDICTION:")
print(f"      RMSE: {np.mean(metrics['points']['rmse']):.4f} ± {np.std(metrics['points']['rmse']):.4f}")
print(f"      R²:   {np.mean(metrics['points']['r2']):.4f} ± {np.std(metrics['points']['r2']):.4f}")

# Train final models on full 2023 data
print("\n🎯 Training final models on full data...")

# Winner (all data)
clf_final = RandomForestClassifier(
    n_estimators=200, max_depth=15, min_samples_split=10,
    min_samples_leaf=4, class_weight='balanced', random_state=42
)
clf_final.fit(X_numeric, y_winner)
print("   ✅ Winner classifier")

# Position (no DNFs)
reg_pos_final = XGBRegressor(
    n_estimators=200, max_depth=8, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=42
)
reg_pos_final.fit(X_no_dnf, y_position_no_dnf)
print("   ✅ Position regressor")

# Points (no DNFs)
reg_pts_final = XGBRegressor(
    n_estimators=200, max_depth=8, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=42
)
reg_pts_final.fit(X_no_dnf, y_points_no_dnf)
print("   ✅ Points regressor")

# Save models
print("\n💾 Saving models...")
models_dir = Path("models/v1.2.0")
models_dir.mkdir(parents=True, exist_ok=True)

with open(models_dir / "classifier_winner.pkl", "wb") as f:
    pickle.dump(clf_final, f)

with open(models_dir / "regressor_position.pkl", "wb") as f:
    pickle.dump(reg_pos_final, f)

with open(models_dir / "regressor_points.pkl", "wb") as f:
    pickle.dump(reg_pts_final, f)

# Save features
with open(models_dir / "features.json", "w") as f:
    json.dump(features_list, f, indent=2)

# Save metrics
metrics_summary = {
    'version': '1.2.0',
    'trained_on': datetime.now().isoformat(),
    'training_data': '2023 season (440 samples, 304 finished races)',
    'validation_strategy': 'K-Fold CV (5 folds)',
    'num_features': len(features_list),
    'enhanced_features': True,
    'metrics': {
        'winner': {
            'roc_auc_mean': float(np.mean(metrics['winner']['roc_auc'])),
            'roc_auc_std': float(np.std(metrics['winner']['roc_auc'])),
            'f1_mean': float(np.mean(metrics['winner']['f1'])),
            'f1_std': float(np.std(metrics['winner']['f1'])),
        },
        'position': {
            'rmse_mean': float(np.mean(metrics['position']['rmse'])),
            'rmse_std': float(np.std(metrics['position']['rmse'])),
            'r2_mean': float(np.mean(metrics['position']['r2'])),
            'r2_std': float(np.std(metrics['position']['r2'])),
        },
        'points': {
            'rmse_mean': float(np.mean(metrics['points']['rmse'])),
            'rmse_std': float(np.std(metrics['points']['rmse'])),
            'r2_mean': float(np.mean(metrics['points']['r2'])),
            'r2_std': float(np.std(metrics['points']['r2'])),
        },
    }
}

with open(models_dir / "metrics.json", "w") as f:
    json.dump(metrics_summary, f, indent=2)

# Save feature importances
importances_clf = pd.DataFrame({
    'feature': features_list,
    'importance': clf_final.feature_importances_
}).sort_values('importance', ascending=False)

importances_pos = pd.DataFrame({
    'feature': features_list,
    'importance': reg_pos_final.feature_importances_
}).sort_values('importance', ascending=False)

importances_clf.to_csv(models_dir / "feature_importances_classifier.csv", index=False)
importances_pos.to_csv(models_dir / "feature_importances_position.csv", index=False)

# Update 'latest' symlink
latest_link = Path("models/latest")
if latest_link.exists() or latest_link.is_symlink():
    latest_link.unlink()
latest_link.symlink_to("v1.2.0")

print(f"\n✅ Models saved to {models_dir}")
print(f"✅ Updated models/latest -> v1.2.0")

# Comparison with v1.1.0
print("\n" + "="*80)
print("📊 PERFORMANCE COMPARISON")
print("="*80)

v110_metrics = {
    'winner_roc_auc': 0.9896,
    'winner_f1': 0.7966,
    'position_rmse': 4.71,
    'position_r2': 0.3246,
    'points_rmse': 4.70,
    'points_r2': 0.5727,
}

v120_metrics = {
    'winner_roc_auc': np.mean(metrics['winner']['roc_auc']),
    'winner_f1': np.mean(metrics['winner']['f1']),
    'position_rmse': np.mean(metrics['position']['rmse']),
    'position_r2': np.mean(metrics['position']['r2']),
    'points_rmse': np.mean(metrics['points']['rmse']),
    'points_r2': np.mean(metrics['points']['r2']),
}

print("\n   METRIC              v1.1.0     v1.2.0      CHANGE")
print("   " + "-"*58)
print(f"   Winner ROC-AUC:     {v110_metrics['winner_roc_auc']:.4f}     {v120_metrics['winner_roc_auc']:.4f}     {((v120_metrics['winner_roc_auc']/v110_metrics['winner_roc_auc']-1)*100):+.1f}%")
print(f"   Winner F1-Score:    {v110_metrics['winner_f1']:.4f}     {v120_metrics['winner_f1']:.4f}     {((v120_metrics['winner_f1']/v110_metrics['winner_f1']-1)*100):+.1f}%")
print(f"   Position RMSE:      {v110_metrics['position_rmse']:.4f}     {v120_metrics['position_rmse']:.4f}     {((v120_metrics['position_rmse']/v110_metrics['position_rmse']-1)*100):+.1f}%")
print(f"   Position R²:        {v110_metrics['position_r2']:.4f}     {v120_metrics['position_r2']:.4f}     {((v120_metrics['position_r2']/v110_metrics['position_r2']-1)*100):+.1f}%")
print(f"   Points RMSE:        {v110_metrics['points_rmse']:.4f}     {v120_metrics['points_rmse']:.4f}     {((v120_metrics['points_rmse']/v110_metrics['points_rmse']-1)*100):+.1f}%")
print(f"   Points R²:          {v110_metrics['points_r2']:.4f}     {v120_metrics['points_r2']:.4f}     {((v120_metrics['points_r2']/v110_metrics['points_r2']-1)*100):+.1f}%")

print("\n" + "="*80)
print("✅ TRAINING COMPLETE!")
print("="*80)
