# F1 ML Notebooks

This directory contains Jupyter notebooks for F1 race prediction model development and analysis.

---

## 📓 Notebooks

### 1. `explore_dataset.ipynb` - Exploratory Data Analysis
**Purpose:** Initial data exploration, feature engineering experimentation, and model prototyping

**Status:** ⚠️ EXPLORATION ONLY - Not for production use

**What's Inside:**
- 139 cells of comprehensive EDA
- Multiple model experiments (RF, XGBoost, Ensembles)
- Hyperparameter tuning with GridSearch
- Feature engineering prototypes

**Models Trained:**
- Winner Classifier (ROC-AUC: 0.97)
- Position Regressor (RMSE: 4.3)
- Points Regressor (RMSE: 5.1)

**Issues:**
- No integrated data validation
- No cross-validation
- Timestamp-based model naming
- Missing feature importance analysis

**Use For:**
- Understanding data patterns
- Testing new feature ideas
- Quick experimentation

**DON'T Use For:**
- Production model training
- Performance benchmarks
- Deployment

---

### 2. `train_production_model.ipynb` - Production Model Training ✨ NEW
**Purpose:** Train production-ready models with best practices

**Status:** ✅ PRODUCTION READY

**Key Features:**
- ✅ Integrated data validation (`src/ml/validation.py`)
- ✅ Cross-validation for robust metrics
- ✅ Feature importance analysis (RF + SHAP)
- ✅ Semantic versioning (`v1.1.0`, `v1.2.0`, etc.)
- ✅ Comprehensive logging and metrics
- ✅ Reproducible training pipeline

**Workflow:**
```
1. Load Data
   ↓
2. Feature Engineering (using src/ml/features.py)
   ↓
3. 🔒 DATA VALIDATION (CRITICAL - anti-leakage)
   ↓
4. Train/Test Split (Temporal: 2023/2024)
   ↓
5. Cross-Validation Training
   ↓
6. Feature Importance Analysis
   ↓
7. Evaluation & Model Saving
   ↓
8. Model Versioning (semantic versions)
```

**Target Metrics:**
- Position RMSE < 2.5 positions (current: 4.3)
- Winner ROC-AUC > 0.95 (current: 0.97 ✅)
- Points RMSE < 4.0 points (current: 5.1)

**Use For:**
- Training production models
- Benchmarking improvements
- Model versioning
- Feature analysis

---

## 🚀 How to Use

### Option 1: Quick Start (Use Existing Models)
```bash
# Current models are in models/ (v1.0.0)
# They are validated (no data leakage) but have high RMSE
```

### Option 2: Re-train Models (Recommended)
```bash
# 1. Activate environment
source f1-venv/bin/activate  # Linux/Mac
# or
.\f1-venv\Scripts\Activate.ps1  # Windows

# 2. Open production training notebook
jupyter notebook notebooks/train_production_model.ipynb

# 3. Run all cells (Kernel > Restart & Run All)

# 4. Check output in models/v1.1.0/
ls -lah models/v1.1.0/
```

### Option 3: Experiment with New Features
```bash
# Use explore_dataset.ipynb for experimentation
# Then copy successful features to src/ml/features.py
# Then re-train with train_production_model.ipynb
```

---

## 📂 Directory Structure

```
notebooks/
├── README.md                        # This file
├── explore_dataset.ipynb            # EDA & experimentation (3 MB)
├── train_production_model.ipynb     # Production training (NEW)
└── (future notebooks)
    ├── hyperparameter_tuning.ipynb  # Planned
    ├── feature_selection.ipynb      # Planned
    └── model_comparison.ipynb       # Planned
```

---

## ⚠️ Important Notes

### DO:
- ✅ Use `train_production_model.ipynb` for production models
- ✅ Run data validation before training
- ✅ Use cross-validation
- ✅ Document model versions
- ✅ Save feature importance
- ✅ Track metrics over time

### DON'T:
- ❌ Deploy models from `explore_dataset.ipynb` to production
- ❌ Skip data validation
- ❌ Use timestamp-based model naming
- ❌ Train without cross-validation
- ❌ Ignore feature importance

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
```bash
# Make sure you're in the project root
cd /path/to/f1-race-replay

# Install in editable mode
pip install -e .
```

### "Data file not found"
```bash
# Run data collection first
python src/ml/collect_historical_data.py

# Or specify existing data path in notebook
DATA_PATH = Path("your/data/path.parquet")
```

### "Validation failed: Data leakage detected"
```python
# Check which features are forbidden
from src.ml.validation import FORBIDDEN_FEATURES_AT_PREDICTION
print(FORBIDDEN_FEATURES_AT_PREDICTION)

# Make sure you dropped targets before training
X = df.drop(columns=['winner', 'race_position', 'points', ...])
```

---

## 📊 Model Versioning

### Current Versions

| Version | Date | Position RMSE | Winner AUC | Status | Notes |
|---------|------|---------------|------------|--------|-------|
| v1.0.0 | 2024-12-25 | 4.30 | 0.97 | ⚠️ High RMSE | From explore_dataset.ipynb |
| v1.1.0 | TBD | TBD | TBD | 🔄 In Progress | From train_production_model.ipynb |

### Version Naming

```
models/
├── v1.0.0/          # Initial production model
├── v1.1.0/          # Improved features (target: RMSE < 2.5)
├── v1.2.0/          # Hyperparameter tuning
├── v2.0.0/          # Architecture change (e.g., neural nets)
└── latest -> v1.1.0 # Symlink to current production
```

**Semantic Versioning:**
- **Major (v2.0.0):** Breaking changes (different features, architecture)
- **Minor (v1.1.0):** New features, improvements (backward compatible)
- **Patch (v1.0.1):** Bug fixes, small tweaks

---

## 📚 Resources

### Documentation
- [Model Validation Report](../MODEL_VALIDATION_REPORT.md)
- [Code Review Phase 3](../CODE_REVIEW_PHASE3.md)
- [Phase 1 Complete](../PHASE1_COMPLETE.md)

### Code References
- Feature Engineering: `src/ml/features.py`
- Data Validation: `src/ml/validation.py`
- Data Collection: `src/ml/data_collection.py`
- Prediction Engine: `src/ml/prediction.py`

### External Resources
- [FastF1 Documentation](https://docs.fastf1.dev/)
- [Scikit-learn User Guide](https://scikit-learn.org/stable/user_guide.html)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [SHAP for Model Interpretability](https://shap.readthedocs.io/)

---

## 🎯 Next Steps

1. **Run `train_production_model.ipynb`** to create v1.1.0
2. **Compare metrics** with v1.0.0 baseline
3. **Deploy v1.1.0** if metrics improve
4. **Iterate** on features/hyperparameters

---

**Last Updated:** 2025-12-30  
**Maintainer:** Adrian Infantes (infantesromeroadrian@gmail.com)
