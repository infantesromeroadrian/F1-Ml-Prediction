# 🔍 CODE REVIEW - PHASE 3: DEEP DIVE

## Auditoría Técnica Completa del Proyecto F1-ML-Prediction

**Fecha:** 30 Diciembre 2025  
**Revisor:** Gentleman-AI (Senior Principal Architect)  
**Alcance:** src/, notebooks/, models/  
**Objetivo:** Detectar problemas arquitectónicos, bugs, y oportunidades de mejora

---

## 📊 RESUMEN EJECUTIVO

### **VEREDICTO GENERAL: ⚠️ FUNCIONAL PERO CON DEUDA TÉCNICA**

**Puntuación Global: 6.5/10**

| Categoría | Puntuación | Estado |
|-----------|------------|--------|
| **Arquitectura** | 5/10 | ⚠️ Conflictos de nombres, mezcla legacy/nuevo |
| **Código ML** | 7/10 | ✅ Funcional, pero puede mejorar |
| **Tests** | 3/10 | ❌ Coverage crítico (2%) |
| **Documentación** | 6/10 | ⚠️ Básica, falta detalle técnico |
| **Performance** | 6/10 | ⚠️ No optimizado |
| **Seguridad** | 7/10 | ✅ Básica correcta |

### **HALLAZGOS CRÍTICOS** 🔥

1. **CONFLICTO DE NOMBRES** - `src/f1_data.py` vs `src/f1_data/` (❌ CRÍTICO)
2. **DATA LEAKAGE RISK** - Feature engineering sin validación temporal estricta (⚠️ ALTO)
3. **NO HAY TESTS ML** - 0 tests para el pipeline ML completo (❌ CRÍTICO)
4. **HARDCODED PATHS** - Rutas de modelos hardcodeadas con timestamps (⚠️ MEDIO)
5. **NO HAY MODEL REGISTRY** - Modelos sin versionado semántico (⚠️ MEDIO)

---

## ══════════════════════════════════════════════════════════════
## 🏗️ PARTE 1: REVISIÓN DE ARQUITECTURA
## ══════════════════════════════════════════════════════════════

### 1.1. ESTRUCTURA ACTUAL

```
src/
├── arcade_replay.py           # ❌ Entry point antiguo
├── f1_data.py                 # ⚠️ CONFLICTO - Wrapper de compatibilidad
├── f1_data/                   # ⚠️ CONFLICTO - Package moderno
│   ├── __init__.py
│   ├── cache.py
│   ├── loaders.py
│   └── processors.py
├── config.py                  # ✅ Bien hecho
├── logging_config.py          # ✅ Bien hecho
├── interfaces/                # ✅ Separación clara
│   ├── qualifying.py
│   └── race_replay.py
├── lib/                       # ⚠️ Nombre genérico
│   ├── time.py
│   └── tyres.py
├── ml/                        # ✅ Separación correcta
│   ├── collect_historical_data.py
│   ├── data_collection.py
│   ├── features.py
│   └── prediction.py
└── ui_components/             # ✅ Modular
    ├── (múltiples archivos)
```

### **PROBLEMA #1: CONFLICTO DE NOMBRES** ❌

**Archivo:** `src/f1_data.py` vs `src/f1_data/`

**Descripción:**
- Existe `src/f1_data.py` (módulo legacy)
- Existe `src/f1_data/` (package moderno)
- Python puede confundirse en imports

**Código problemático:**
```python
# src/f1_data.py
from src.f1_data.loaders import enable_cache  # ❌ Confuso

# Imports desde otros archivos
from src.f1_data import enable_cache  # ¿Cuál es cuál?
```

**Impacto:** ⚠️ ALTO - Confusión en imports, dificulta mantenimiento

**Solución recomendada:**
```python
# Eliminar src/f1_data.py completamente
# Renombrar imports a:
from src.f1_data.loaders import enable_cache  # Explícito

# O mejor: crear package principal
# src/f1_replay/data/loaders.py
```

---

### **PROBLEMA #2: NOMBRES GENÉRICOS**

**Archivo:** `src/lib/`

**Descripción:**
- Carpeta `lib/` es demasiado genérico
- No indica qué contiene
- Mezcla utilidades de diferentes dominios

**Impacto:** ⚠️ MEDIO - Dificulta navegación

**Solución:**
```
src/
└── utils/          # En vez de lib/
    ├── time.py
    └── tyres.py
```

---

### 1.2. IMPORTS CIRCULARES POTENCIALES

**Revisión de dependencias:**

```
main.py 
  → src.f1_data (legacy)
      → src.f1_data.loaders
      → src.f1_data.processors
  → src.ml.prediction
      → src.ml.features
      → src.ml.data_collection
          → src.f1_data.loaders  # ⚠️ Dependencia cruzada
```

**Estado:** ✅ No hay circulares AHORA, pero la arquitectura es frágil

---

## ══════════════════════════════════════════════════════════════
## 🤖 PARTE 2: REVISIÓN DE CÓDIGO ML
## ══════════════════════════════════════════════════════════════

### 2.1. ANÁLISIS DE `src/ml/prediction.py` (707 líneas)

#### **✅ PUNTOS POSITIVOS:**

1. **Docstrings completos** - Bien documentado
2. **Logging estructurado** - Usa logger correctamente
3. **Manejo de errores** - Try/catch adecuados
4. **Type hints parciales** - Algunos tipos definidos

#### **❌ PROBLEMAS CRÍTICOS:**

##### **PROBLEMA #3: HARDCODED PATHS CON TIMESTAMPS** ⚠️

```python
# Líneas 30-31
DEFAULT_MODEL_INFO_FILE = "optimized_models_info_20251225_000229.json"
DEFAULT_FEATURE_NAMES_FILE = "enhanced_feature_names_20251225_000229.json"
```

**Impacto:** ⚠️ ALTO
- Cada vez que entrenes un modelo, hay que cambiar el código
- No hay versionado semántico (v1.0.0, v2.0.0)
- Difícil saber qué modelo está en producción

**Solución:**
```python
# Opción A: Symlinks
DEFAULT_MODEL_INFO_FILE = "model_info_latest.json"
# Y crear symlink: model_info_latest.json -> optimized_models_info_20251225_000229.json

# Opción B: Versionado semántico
DEFAULT_MODEL_INFO_FILE = "model_info_v2.0.0.json"

# Opción C: MLflow Model Registry (RECOMENDADO)
model_uri = "models:/fraud-detector/production"
```

---

##### **PROBLEMA #4: FEATURE PREPARATION MONOLÍTICA**

**Método:** `F1PredictionEngine._prepare_final_features()` (líneas 524-599)

```python
def _prepare_final_features(self, df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    
    # Apply transformations
    result = self._apply_transformations(result)
    
    # Create derived features
    result = self._create_derived_features(result)
    
    # Create advanced features
    result = self._create_advanced_features(result)
    
    # Encode categorical features
    result = self._encode_categorical_features(result)
    
    # ... 75 líneas más de lógica compleja
```

**Problemas:**
- ❌ Método demasiado largo (75+ líneas)
- ❌ Sin tests unitarios
- ❌ Difícil de debuggear
- ❌ No reutilizable fuera de esta clase

**Impacto:** ⚠️ MEDIO - Dificulta mantenimiento

**Solución:**
```python
# Crear una clase FeatureEngineer separada
class FeatureEngineer:
    def __init__(self, feature_names: list[str]):
        self.feature_names = feature_names
        self.transformers = self._build_transformers()
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        # Pipeline sklearn
        return self.transformers.transform(df)

# Uso
feature_engineer = FeatureEngineer(self.feature_names)
X = feature_engineer.transform(driver_features)
```

---

##### **PROBLEMA #5: ENCODING INCONSISTENTE**

**Método:** `_encode_categorical_features()` (líneas 488-522)

```python
# Líneas 507-509
encoded_col = f"{col}_encoded"
result[encoded_col] = result[col].astype(str).apply(
    lambda x: hash(x) % 1000  # ❌ Hash no determinístico entre ejecuciones
)
```

**Problemas:**
- ❌ `hash()` en Python NO es determinístico entre ejecuciones
- ❌ Modelos entrenados en una sesión no funcionarán en otra
- ❌ No hay fit/transform separation

**Ejemplo del bug:**
```python
# Sesión 1 (training)
hash("Mercedes") % 1000  # → 347

# Sesión 2 (inference)
hash("Mercedes") % 1000  # → 893  ❌ DIFERENTE!
```

**Impacto:** 🔥 CRÍTICO - Modelos NO reproducibles

**Solución:**
```python
from sklearn.preprocessing import LabelEncoder

# Opción A: Label Encoder
self.label_encoders[col] = LabelEncoder()
result[encoded_col] = self.label_encoders[col].fit_transform(result[col])

# Opción B: Hash estable
import hashlib
result[encoded_col] = result[col].apply(
    lambda x: int(hashlib.md5(x.encode()).hexdigest(), 16) % 1000
)

# Opción C: Target Encoding (mejor para ML)
from category_encoders import TargetEncoder
```

---

### 2.2. ANÁLISIS DE `src/ml/features.py` (256 líneas)

#### **✅ PUNTOS POSITIVOS:**

1. **Temporal awareness** - Filtra datos históricos correctamente
2. **Logging claro** - Buena trazabilidad
3. **Manejo de NaN** - Considera casos edge

#### **⚠️ PROBLEMA #6: DATA LEAKAGE POTENCIAL**

**Función:** `calculate_historical_stats()` (líneas 11-148)

```python
# Líneas 30-34
historical_data = df[
    (df["year"] < current_year)
    | ((df["year"] == current_year) & (df["round_number"] < current_round))
].copy()
```

**Análisis:**
- ✅ Filtra correctamente por año y round
- ⚠️ PERO: No valida que los datos de qualifying no contengan info de la carrera
- ⚠️ No hay validación de que `race_position` no se use accidentalmente

**Riesgo de leakage:**
```python
# Si alguien añade esto sin darse cuenta:
df['grid_position'] = df['race_position']  # ❌ LEAKAGE!

# Y luego se usa como feature
features['grid_position_normalized'] = ...
```

**Impacto:** 🔥 ALTO - Predicciones optimistas, falla en producción

**Solución:**
```python
# Validar que no hay features del futuro
FORBIDDEN_FEATURES_AT_PREDICTION = [
    'race_position', 'points', 'dnf', 'winner', 'fastest_lap_time'
]

def validate_no_leakage(df: pd.DataFrame) -> None:
    leaked = set(df.columns) & set(FORBIDDEN_FEATURES_AT_PREDICTION)
    if leaked:
        raise ValueError(f"Data leakage detected: {leaked}")

# Llamar antes de training
validate_no_leakage(X_train)
```

---

### 2.3. ANÁLISIS DE `src/ml/data_collection.py` (322 líneas)

#### **✅ PUNTOS POSITIVOS:**

1. **Extracción limpia** - Separa race/quali/weather
2. **Robusto** - Maneja missing data
3. **FastF1 integration** - Usa API correctamente

#### **⚠️ PROBLEMA #7: SIN VALIDACIÓN DE DATOS**

**Función:** `extract_race_results()` (líneas 35-90)

```python
position = int(row["Position"]) if pd.notna(row["Position"]) else None
points = float(row["Points"]) if pd.notna(row["Points"]) else 0.0
```

**Problemas:**
- ❌ No valida rangos (position debe ser 1-20)
- ❌ No valida consistencia (ganador debe tener 25 puntos + fastest lap)
- ❌ No detecta datos corruptos

**Solución:**
```python
# Usar Pydantic para validación
from pydantic import BaseModel, Field, field_validator

class RaceResult(BaseModel):
    driver_code: str = Field(min_length=3, max_length=3)
    race_position: int | None = Field(ge=1, le=20)
    points: float = Field(ge=0, le=26)  # Max points = 25 + 1 fastest lap
    
    @field_validator('points')
    @classmethod
    def validate_winner_points(cls, v, values):
        if values.get('race_position') == 1 and v < 25:
            raise ValueError("Winner must have at least 25 points")
        return v
```

---

## ══════════════════════════════════════════════════════════════
## 📓 PARTE 3: REVISIÓN DE NOTEBOOKS
## ══════════════════════════════════════════════════════════════

### 3.1. `notebooks/explore_dataset.ipynb`

**Análisis:**
- ✅ Carga de datos correcta
- ✅ Exploración básica (head, describe)
- ⚠️ NO HAY análisis de distribuciones
- ⚠️ NO HAY detección de outliers
- ⚠️ NO HAY correlación de features
- ❌ NO HAY validación de temporal split

**Falta:**
1. Análisis de balance de clases (winner vs no winner)
2. Distribución de features por año (drift temporal)
3. Correlation matrix
4. Missing data analysis
5. Feature importance preliminary

**Recomendación:** Expandir notebook con análisis EDA completo

---

## ══════════════════════════════════════════════════════════════
## 🎯 PARTE 4: REVISIÓN DE MODELOS
## ══════════════════════════════════════════════════════════════

### 4.1. MODELOS ENTRENADOS

**Inventario:**
```
models/
├── best_classifier_ensemble_stacking_20251225_001613.pkl  (989KB)
├── best_points_regressor_ensemble_20251225_001613.pkl     (5.5MB)
├── best_position_regressor_ensemble_20251225_001613.pkl   (2.3MB)
└── (otros 14 archivos)
```

**Total:** 12MB de modelos (17 archivos)

### 4.2. MÉTRICAS DE MODELOS

**Clasificación (Winner Prediction):**
```json
{
  "f1": 0.67,
  "roc_auc": 0.97
}
```

**Análisis:**
- ✅ ROC-AUC excelente (0.97)
- ⚠️ F1 moderado (0.67)
- ❌ NO HAY precision/recall separados
- ❌ NO HAY confusion matrix
- ❌ NO HAY calibration curve

**Regresión (Position):**
```json
{
  "r2": 0.43,
  "rmse": 4.30
}
```

**Análisis:**
- ⚠️ R² bajo (0.43) - Solo explica 43% varianza
- ⚠️ RMSE = 4.3 posiciones - Margen de error alto
- ❌ Predecir posición exacta en F1 es muy difícil
- ⚠️ ¿Es el problema correcto? Quizás clasificación en rangos (top 3, 4-10, 11-20)

**Regresión (Points):**
```json
{
  "r2": 0.51,
  "rmse": 5.10
}
```

**Análisis:**
- ✅ Mejor que position (R² = 0.51)
- ⚠️ RMSE = 5.1 puntos - Margen aceptable
- ⚠️ ¿Tiene sentido predecir puntos decimales?

---

### **PROBLEMA #8: MÉTRICAS INCORRECTAS PARA EL PROBLEMA**

**Problema:**
- Predecir posición exacta (1-20) es casi imposible
- R² = 0.43 indica que el modelo es débil
- RMSE = 4.3 posiciones → Predicción ±4 posiciones es inútil

**Solución Alternativa:**

**Opción A: Clasificación Multi-clase por Rangos**
```python
# En vez de regression:
class PositionPredictor:
    CLASSES = ["Top3", "Top10", "Midfield", "Bottom"]
    
    def predict(self, features):
        # Classifier con 4 clases
        # Top3: positions 1-3 (podium)
        # Top10: positions 4-10 (points)
        # Midfield: positions 11-15
        # Bottom: positions 16-20
```

**Ventajas:**
- Más útil para usuarios
- Métricas más interpretables
- Probabilidades calibradas

**Opción B: Ordinal Regression**
```python
# Mantiene el orden: Top3 > Top10 > Midfield > Bottom
from mord import LogisticAT
model = LogisticAT()
```

---

### **PROBLEMA #9: NO HAY ENSEMBLE DIVERSITY CHECK**

**Código actual:**
```python
# ensemble_models_info_20251225_001613.json
{
  "classification": {
    "best_model": "stacking",
    "metrics": {
      "individual": {"f1": 0.67, "roc_auc": 0.97},
      "voting": {"f1": 0.67, "roc_auc": 0.96},
      "stacking": {"f1": 0.67, "roc_auc": 0.97}
    }
  }
}
```

**Problema:**
- ❌ No hay info de qué modelos forman el ensemble
- ❌ No hay correlación entre predicciones de modelos base
- ❌ Si todos los modelos aprenden lo mismo, ensemble no ayuda

**Solución:**
```python
# Medir diversidad de ensemble
from sklearn.metrics import matthews_corrcoef

def measure_ensemble_diversity(base_predictions):
    """
    Medir correlación entre modelos base.
    Baja correlación = alta diversidad = mejor ensemble.
    """
    correlations = []
    for i, pred_i in enumerate(base_predictions):
        for j, pred_j in enumerate(base_predictions[i+1:]):
            corr = matthews_corrcoef(pred_i, pred_j)
            correlations.append(corr)
    
    avg_correlation = np.mean(correlations)
    print(f"Average correlation: {avg_correlation:.3f}")
    # Ideal: < 0.7 (modelos diversos)
    return avg_correlation
```

---

## ══════════════════════════════════════════════════════════════
## ⚡ PARTE 5: PERFORMANCE & OPTIMIZACIÓN
## ══════════════════════════════════════════════════════════════

### **PROBLEMA #10: FEATURE ENGINEERING LENTO**

**Función:** `F1PredictionEngine.prepare_features_from_session()` (líneas 198-300)

**Análisis de complejidad:**
```python
# Línea 276-290
for driver_code in result["driver_code"].unique():  # O(n_drivers)
    driver_history = historical_data[historical_data["driver_code"] == driver_code]
    # ^ Filtrado en loop: O(n_drivers * n_historical)
```

**Impacto:** ⚠️ MEDIO
- Para 20 pilotos con 10 años de historia: 20 * 200 = 4000 operaciones
- Cada filtrado recorre todo el DataFrame

**Solución:**
```python
# Usar groupby (mucho más rápido)
grouped = historical_data.groupby("driver_code")

for driver_code, driver_history in grouped:
    # Ya está filtrado, O(1) lookup
    ...
```

**Ganancia estimada:** 10-50x más rápido

---

### **PROBLEMA #11: MÚLTIPLES COPIAS DE DATAFRAME**

**Código:**
```python
# Línea 41 en calculate_historical_stats
result = df.copy()  # Copia 1

# Línea 312 en _apply_transformations
result = df.copy()  # Copia 2

# Línea 339 en _create_derived_features
result = df.copy()  # Copia 3

# ... y así sucesivamente
```

**Impacto:** ⚠️ MEDIO
- Para dataset de 500 filas x 50 cols: ~100KB por copia
- 5 copias = 500KB extra en memoria

**Solución:**
```python
# Opción A: Modificar in-place (cuidado con side effects)
def _apply_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
    # No copiar, modificar directamente
    df['feature_log'] = np.log1p(df['feature'])
    return df

# Opción B: Usar pipeline sklearn (más eficiente)
from sklearn.pipeline import Pipeline
pipeline = Pipeline([
    ('transformer', FeatureTransformer()),
    ('encoder', CategoryEncoder()),
])
```

---

## ══════════════════════════════════════════════════════════════
## 🔒 PARTE 6: SEGURIDAD & ROBUSTEZ
## ══════════════════════════════════════════════════════════════

### **PROBLEMA #12: PICKLE SECURITY**

**Código:** `src/ml/prediction.py` línea 140

```python
with open(classifier_path, 'rb') as f:
    self.classifier_model = pickle.load(f)  # ❌ Pickle inseguro
```

**Problema:**
- ❌ Pickle puede ejecutar código arbitrario
- ❌ Si alguien modifica el .pkl, puede inyectar malware
- ❌ No hay validación de checksum

**Impacto:** ⚠️ MEDIO (solo si modelos vienen de fuentes no confiables)

**Solución:**
```python
# Opción A: Joblib (más seguro)
import joblib
model = joblib.load(classifier_path)

# Opción B: Verificar checksum
import hashlib

def load_model_safe(path: Path, expected_hash: str):
    # Calcular hash del archivo
    with open(path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    if file_hash != expected_hash:
        raise ValueError(f"Model file corrupted or tampered!")
    
    with open(path, 'rb') as f:
        return pickle.load(f)

# Uso
model = load_model_safe(
    path=classifier_path,
    expected_hash="abc123..."  # Guardado en model_info.json
)
```

---

## ══════════════════════════════════════════════════════════════
## 📋 PARTE 7: RECOMENDACIONES PRIORIZADAS
## ══════════════════════════════════════════════════════════════

### 🔥 PRIORIDAD CRÍTICA (Hacer YA)

1. **FIX: Hash determinístico** (PROBLEMA #5)
   - Tiempo: 30 min
   - Impacto: CRÍTICO - Modelos no reproducibles
   - ```python
     # Usar hashlib en vez de hash()
     import hashlib
     encoded = int(hashlib.md5(value.encode()).hexdigest(), 16) % 1000
     ```

2. **FIX: Validación de data leakage** (PROBLEMA #6)
   - Tiempo: 1 hora
   - Impacto: ALTO - Predicciones incorrectas
   - Crear función `validate_no_leakage()` y añadir a pipeline

3. **REFACTOR: Eliminar conflicto de nombres** (PROBLEMA #1)
   - Tiempo: 2 horas
   - Impacto: ALTO - Confusión en imports
   - Borrar `src/f1_data.py`, actualizar todos los imports

### ⚠️ PRIORIDAD ALTA (Esta semana)

4. **ADD: Tests para ML pipeline**
   - Tiempo: 4 horas
   - Impacto: ALTO - 0 tests actual
   - Objetivo: 30% coverage en src/ml/

5. **REFACTOR: Feature engineering modular**
   - Tiempo: 3 horas
   - Impacto: MEDIO - Mantenibilidad
   - Crear clase `FeatureEngineer` separada

6. **ADD: Data validation con Pydantic** (PROBLEMA #7)
   - Tiempo: 2 horas
   - Impacto: MEDIO - Robustez
   - Validar rangos y consistencia de datos

### 📝 PRIORIDAD MEDIA (Próximas 2 semanas)

7. **OPTIMIZE: Feature engineering performance** (PROBLEMA #10)
   - Tiempo: 2 horas
   - Impacto: MEDIO - 10-50x speedup
   - Usar groupby en vez de loops

8. **REFACTOR: Model versioning semántico** (PROBLEMA #3)
   - Tiempo: 3 horas
   - Impacto: MEDIO - Mantenibilidad
   - Migrar a versionado v1.0.0, v2.0.0

9. **ADD: Model metrics expansion**
   - Tiempo: 1 hora
   - Impacto: BAJO - Interpretabilidad
   - Añadir precision/recall, confusion matrix

### 🎯 PRIORIDAD BAJA (Futuro)

10. **CONSIDER: Cambiar de regression a classification** (PROBLEMA #8)
    - Tiempo: 8 horas (re-entrenar)
    - Impacto: ALTO (si métricas no mejoran)
    - Predecir Top3/Top10/Midfield/Bottom en vez de posición exacta

11. **ADD: MLflow integration**
    - Tiempo: 4 horas
    - Impacto: MEDIO - Experiment tracking
    - Reemplazar archivos .json con MLflow

12. **ADD: Ensemble diversity check** (PROBLEMA #9)
    - Tiempo: 1 hora
    - Impacto: BAJO - Validación
    - Medir correlación entre modelos base

---

## ══════════════════════════════════════════════════════════════
## ✅ CONCLUSIONES
## ══════════════════════════════════════════════════════════════

### **VEREDICTO FINAL:**

**El proyecto es FUNCIONAL pero tiene DEUDA TÉCNICA significativa.**

**Lo bueno:** ✅
- Integración con FastF1 correcta
- Logging estructurado
- Separación de concerns básica
- Modelos entrenados y funcionando

**Lo malo:** ❌
- Hash no determinístico → Modelos no reproducibles
- Sin tests para ML
- Conflicto de nombres en arquitectura
- Riesgo de data leakage
- Performance no optimizado

**Lo feo:** 🤮
- 232 linting errors pendientes
- Coverage 2%
- Paths hardcodeados con timestamps
- No hay model registry

---

### **ESFUERZO ESTIMADO DE MEJORA:**

| Categoría | Horas | Prioridad |
|-----------|-------|-----------|
| Crítico (HACER YA) | 4h | 🔥 |
| Alto (Esta semana) | 9h | ⚠️ |
| Medio (2 semanas) | 6h | 📝 |
| Bajo (Futuro) | 13h | 🎯 |
| **TOTAL** | **32h** | - |

**Con 32 horas de trabajo enfocado, este proyecto pasa de 6.5/10 a 9/10.**

---

### **ROADMAP RECOMENDADO:**

```
SEMANA 1: Fixes críticos
├─ Día 1-2: Fix hash determinístico + validación leakage
├─ Día 3-4: Eliminar conflicto nombres
└─ Día 5: Añadir tests básicos ML

SEMANA 2: Refactoring
├─ Feature engineering modular
├─ Data validation Pydantic
└─ Model versioning

SEMANA 3: Optimización
├─ Performance improvements
├─ Fix linting errors
└─ Expandir tests (30% coverage)

SEMANA 4+: Features avanzadas
├─ MLflow integration
├─ Considerar re-diseño del problema (classification)
└─ CI/CD completo
```

---

## 📊 SCORECARD FINAL

```
┌─────────────────────────────────────────────────────────────┐
│           CODE REVIEW - F1-ML-PREDICTION                    │
├─────────────────────────────────────────────────────────────┤
│ Arquitectura:           5/10  ⚠️ Conflictos + legacy       │
│ Código ML:              7/10  ✅ Funcional                  │
│ Tests:                  3/10  ❌ Coverage crítico            │
│ Documentación:          6/10  ⚠️ Básica                     │
│ Performance:            6/10  ⚠️ No optimizado              │
│ Seguridad:              7/10  ✅ Básica correcta            │
│                                                             │
│ PUNTUACIÓN GLOBAL:    6.5/10  ⚠️ FUNCIONAL CON DEUDA       │
│                                                             │
│ BUGS CRÍTICOS:           2    🔥 Hash + Leakage            │
│ WARNINGS:                7    ⚠️ Varios                     │
│ TECH DEBT HOURS:        32h   📝 1 mes trabajo              │
└─────────────────────────────────────────────────────────────┘
```

---

**FIN DEL INFORME**

**Próximo paso:** ¿Empezamos con los fixes críticos? 🚀
