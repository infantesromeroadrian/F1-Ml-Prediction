# 🤖 F1 ML Models Directory

This directory contains versioned machine learning models for F1 race prediction.

## 📂 Structure

```
models/
├── latest -> v1.2.0           # Symlink to current production version
├── v1.1.0/                    # Previous version
│   ├── classifier_winner.pkl
│   ├── regressor_position.pkl
│   ├── regressor_points.pkl
│   ├── features.json
│   ├── metrics.json
│   └── feature_importances_*.csv
├── v1.2.0/                    # Current version (PRODUCTION)
│   ├── classifier_winner.pkl
│   ├── regressor_position.pkl
│   ├── regressor_points.pkl
│   ├── features.json
│   ├── metrics.json
│   └── feature_importances_*.csv
└── .archive_YYYYMMDD_HHMMSS/ # Legacy models (can be deleted)
```

## 📊 Version History

### v1.2.0 (CURRENT - 2025-12-30)

**Status:** ✅ PRODUCTION

**Performance:**
- Winner ROC-AUC: **0.9936** (near perfect)
- Position RMSE: **2.79** positions (±3 positions)
- Position R²: **0.62** (explains 62% variance)
- Points RMSE: **4.44** points
- Points R²: **0.66**

**Features:** 59 (29 base + 30 enhanced)

**Enhanced Features Added:**
- Log transformations (9): Handles skewed distributions
- Normalized features (2): Better scaling
- Difference features (2): Captures penalties, temperature effects
- Momentum features (1): Recent form vs overall performance
- Categorical encodings (4): Deterministic MD5 hash
- Interaction features (5): Feature relationships
- Composite features (6): Domain-specific metrics

**Top Important Features:**
1. `points_per_race` (22.8%)
2. `momentum_score` (19.8%) - ENHANCED
3. `win_rate_log` (5.8%) - ENHANCED
4. `grid_position_normalized` (4.8%) - ENHANCED
5. `performance_index` (4.6%) - ENHANCED

**Training:**
- Data: 2023 season (440 samples, 304 finished)
- Validation: 3-Fold CV
- DNFs excluded from position/points training

**Files:**
- `classifier_winner.pkl` (168 KB) - RandomForestClassifier
- `regressor_position.pkl` (733 KB) - XGBRegressor
- `regressor_points.pkl` (676 KB) - XGBRegressor
- `features.json` (59 features)
- `metrics.json` (performance metrics)

---

### v1.1.0 (2025-12-30)

**Status:** ⚠️ DEPRECATED (use v1.2.0)

**Performance:**
- Winner ROC-AUC: 0.9896
- Position RMSE: **4.71** (too high for production)
- Position R²: 0.32
- Points RMSE: 4.70
- Points R²: 0.57

**Features:** 29 (base only)

**Issues:**
- Missing 30 enhanced features
- Position prediction too inaccurate (±5 positions)
- Lower R² values

**Files:**
- Same structure as v1.2.0
- Kept for backward compatibility testing

---

## 🔄 Model Versioning Scheme

We use **Semantic Versioning** for models:

```
vMAJOR.MINOR.PATCH

MAJOR: Breaking changes in feature set or architecture
MINOR: New features, performance improvements (backward compatible)
PATCH: Bug fixes, retraining with same features
```

**Examples:**
- `v1.0.0 → v1.1.0`: Added base features (minor)
- `v1.1.0 → v1.2.0`: Added enhanced features (minor)
- `v1.2.0 → v2.0.0`: Would be architecture change (major)

---

## 📝 File Descriptions

### Standardized Files (All Versions)

| File | Purpose |
|------|---------|
| `classifier_winner.pkl` | Winner prediction model (binary classification) |
| `regressor_position.pkl` | Final position prediction (regression 1-20) |
| `regressor_points.pkl` | Championship points prediction (regression 0-25) |
| `features.json` | List of feature names (in order) |
| `metrics.json` | Performance metrics + metadata |
| `feature_importances_*.csv` | Feature importance scores |

### metrics.json Structure

```json
{
  "version": "1.2.0",
  "trained_on": "2025-12-30T01:31:51.756573",
  "num_features": 59,
  "enhanced_features": true,
  "validation": "3-Fold CV",
  "metrics": {
    "winner": {"roc_auc": 0.9936, "f1": 0.7504},
    "position": {"rmse": 2.79, "r2": 0.6156},
    "points": {"rmse": 4.44, "r2": 0.6628}
  }
}
```

---

## 🚀 Usage

### Loading Models in Code

```python
from src.ml.prediction import create_prediction_engine

# Loads models/latest/ (automatic)
engine = create_prediction_engine()

# Or specify version explicitly
engine = create_prediction_engine(models_dir="models/v1.2.0")
```

### Making Predictions

```python
import fastf1

# Load race session
session = fastf1.get_session(2024, 1, 'R')
quali = fastf1.get_session(2024, 1, 'Q')

session.load()
quali.load()

# Predict
predictions_df = engine.predict(session, quali)

# predictions_df contains:
# - driver_code
# - winner_probability
# - predicted_position
# - predicted_points
# - confidence scores
```

---

## 🔧 Training New Versions

### Quick Training (15 min)

```bash
source f1-venv/bin/activate
python train_v1_2_0_fast.py
```

### Full Training (30 min)

```bash
source f1-venv/bin/activate
python train_v1_2_0.py
```

**Training creates:**
- `models/v1.x.x/` directory
- All model files (.pkl, .json, .csv)
- Updates `models/latest` symlink

---

## 📊 Performance Guidelines

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Winner ROC-AUC | >0.95 | 0.90-0.95 | <0.90 |
| Winner F1 | >0.75 | 0.65-0.75 | <0.65 |
| Position RMSE | <3.0 | 3.0-4.5 | >4.5 |
| Position R² | >0.60 | 0.40-0.60 | <0.40 |
| Points RMSE | <4.5 | 4.5-6.0 | >6.0 |
| Points R² | >0.60 | 0.45-0.60 | <0.45 |

**v1.2.0 Status:**
- ✅ Winner: GOOD
- ✅ Position: GOOD
- ✅ Points: GOOD

---

## 🗑️ Cleanup

### Deleting Old Archives

```bash
# Safe to delete after confirming v1.2.0 works
rm -rf models/.archive_*/
```

### Deleting Old Versions

⚠️ **Warning:** Keep at least 2 versions for rollback capability.

```bash
# Only delete if v1.2.0 is stable for >1 week
rm -rf models/v1.1.0/
```

---

## 🐛 Troubleshooting

### Models Not Loading

**Error:** `Model info file not found`

**Solution:**
```bash
# Check symlink
ls -la models/latest

# Recreate if broken
cd models
rm latest
ln -s v1.2.0 latest
```

### Wrong Version Loading

**Error:** Loading old v1.1.0 instead of v1.2.0

**Solution:**
```bash
# Force update symlink
cd models
rm latest
ln -s v1.2.0 latest
```

### Feature Count Mismatch

**Error:** `Expected 59 features, got 29`

**Solution:**
```python
# Use enhanced=True when preparing features
from src.ml.features import add_feature_columns

df = add_feature_columns(df, enhanced=True)  # Not False!
```

---

## 📚 References

- **Training Scripts:** `train_v1_2_0_fast.py`, `train_v1_2_0.py`
- **Feature Engineering:** `src/ml/features.py:add_enhanced_features()`
- **Prediction Engine:** `src/ml/prediction.py:F1PredictionEngine`
- **Validation:** `src/ml/validation.py:validate_ml_data()`

---

## 📈 Roadmap

### Planned Improvements

- [ ] **v1.3.0**: Tire strategy features (compound, age, pit stops)
- [ ] **v1.4.0**: Sector time features (S1, S2, S3)
- [ ] **v1.5.0**: Weather prediction integration
- [ ] **v2.0.0**: Deep learning architecture (LSTM/Transformer)

### Data Collection

- [ ] Collect 2024 season data (currently: 3 rounds, target: 20+)
- [ ] Add 2022 season for more training data
- [ ] Real-time data pipeline for live predictions

---

**Last Updated:** 2025-12-30  
**Maintainer:** F1-ML-Prediction Team  
**Status:** ✅ Production Ready
