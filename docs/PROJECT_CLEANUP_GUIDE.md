# 🧹 F1 Race Replay - Guía de Limpieza del Proyecto

**Fecha:** 2025-12-30  
**Estado:** CRÍTICO - Múltiples directorios y archivos duplicados/innecesarios  
**Acción Requerida:** Limpieza inmediata antes de continuar desarrollo

---

## 📋 TABLA DE CONTENIDOS

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Problemas Detectados](#problemas-detectados)
3. [Explicación de Directorios](#explicación-de-directorios)
4. [Plan de Acción](#plan-de-acción)
5. [Estructura Final Recomendada](#estructura-final-recomendada)

---

## 🎯 RESUMEN EJECUTIVO

El proyecto tiene **MÚLTIPLES PROBLEMAS DE ORGANIZACIÓN**:

- ❌ **3 entornos virtuales** cuando solo necesitas 1
- ❌ **Documentación duplicada** en root y en `docs/`
- ❌ **Directorios de cache** sin limpiar
- ❌ **Versiones antiguas de modelos** sin archivar
- ❌ **Directorio `history/` duplicado**
- ⚠️ **Directorios vacíos** (`computed_data/`)

**Impacto:**
- Confusión sobre qué entorno usar
- Espacio de disco desperdiciado (~500MB+)
- Riesgo de usar dependencias incorrectas
- Dificulta onboarding de nuevos desarrolladores

---

## 🔍 PROBLEMAS DETECTADOS

### 1. ENTORNOS VIRTUALES DUPLICADOS (CRÍTICO)

```
.venv/                    ✅ CORRECTO - Creado con uv
f1-venv/                  ❌ DUPLICADO - Borrar
f1-prediction-venv/       ❌ DUPLICADO - Borrar
```

**¿Por qué es un problema?**
- Si activas el entorno incorrecto, tendrás dependencias distintas
- Desperdicia ~150MB por entorno
- Confusión sobre cuál es el "verdadero"

**Solución:**
```bash
rm -rf f1-venv/
rm -rf f1-prediction-venv/
# Usar SOLO .venv/
```

---

### 2. CACHES Y TEMPORALES (MODERADO)

```
.ruff_cache/              ℹ️ Cache de Ruff (se regenera)
.pytest_cache/            ℹ️ Cache de pytest (se regenera)
.fastf1-cache/            ✅ NECESARIO (datos de FastF1)
htmlcov/                  ℹ️ Reporte de coverage (se regenera)
.coverage                 ℹ️ Archivo de coverage (se regenera)
```

**¿Qué es cada uno?**

#### `.ruff_cache/`
- **Qué es:** Cache de análisis de código de Ruff
- **Necesario:** NO (se regenera en <1 segundo)
- **Acción:** Borrar (ya está en `.gitignore`)

#### `.pytest_cache/`
- **Qué es:** Cache de pytest para tests más rápidos
- **Necesario:** NO (se regenera automáticamente)
- **Acción:** Borrar (ya está en `.gitignore`)

#### `.fastf1-cache/`
- **Qué es:** Cache de datos descargados de FastF1 API
- **Necesario:** SÍ (evita descargar datos repetidamente)
- **Acción:** MANTENER (pero debe estar en `.gitignore`)

#### `htmlcov/`
- **Qué es:** Reporte HTML de cobertura de tests
- **Necesario:** NO (se regenera con `make coverage`)
- **Acción:** Borrar (ya está en `.gitignore`)

#### `.coverage`
- **Qué es:** Archivo de datos de coverage
- **Necesario:** NO (se regenera con `pytest --cov`)
- **Acción:** Borrar (ya está en `.gitignore`)

**Solución:**
```bash
rm -rf .ruff_cache/ .pytest_cache/ htmlcov/ .coverage
# Se regenerarán automáticamente cuando sea necesario
```

---

### 3. DOCUMENTACIÓN DESORGANIZADA (MODERADO)

```
README.md                          ✅ CORRECTO (root)
CLEANUP_SUMMARY.md                 ❌ Mover a docs/history/
PROJECT_STRUCTURE_AUDIT.md         ❌ Mover a docs/
history/                           ❌ Duplicado (consolidar en docs/history/)
docs/history/                      ✅ CORRECTO
```

**¿Por qué es un problema?**
- Archivos `.md` en root hacen ruido
- `history/` está duplicado
- Dificulta encontrar documentación

**Solución:**
```bash
# Mover archivos
mv CLEANUP_SUMMARY.md docs/history/
mv PROJECT_STRUCTURE_AUDIT.md docs/

# Consolidar history/
cp -r history/* docs/history/
rm -rf history/

# Mantener solo README.md en root
```

---

### 4. MODELOS CON VERSIONES ANTIGUAS (MODERADO)

```
models/
├── .archive_20251230_011549/     ❌ Archivo temporal - Borrar
├── latest → v1.2.0               ✅ CORRECTO (symlink)
├── v1.1.0/                       ⚠️ Versión antigua - Archivar o borrar
├── v1.2.0/                       ✅ CORRECTO (versión actual)
└── README.md                     ✅ CORRECTO
```

**¿Qué hacer con versiones antiguas?**

**Opción 1: Borrar** (si v1.2.0 es claramente superior)
```bash
rm -rf models/v1.1.0/
rm -rf models/.archive_20251230_011549/
```

**Opción 2: Archivar** (si quieres mantener historial)
```bash
mkdir -p models/archived/
mv models/v1.1.0/ models/archived/
mv models/.archive_20251230_011549/ models/archived/
```

**Recomendación:** **BORRAR** v1.1.0 porque:
- Ya tienes v1.2.0 que es superior
- Si necesitas el modelo antiguo, está en git history
- Los modelos deben versionarse con DVC, no con git

---

### 5. COMPUTED_DATA (CRÍTICO)

```
computed_data/
├── 2024_Season_Round_4           (0 bytes - vacío)
├── 2024_Season_Round_5           (0 bytes - vacío)
└── 2024_Season_Round_12          (0 bytes - vacío)
```

**¿Qué es esto?**
- Parece ser un intento de cachear datos procesados
- Todos los archivos están vacíos (0 bytes)
- No hay código que lo use

**Acción:** **BORRAR** porque:
- Archivos vacíos sin propósito
- No está documentado
- Si necesitas cache, usa `data/processed/`

```bash
rm -rf computed_data/
```

---

### 6. IMAGES VS RESOURCES (MENOR)

```
images/                   ✅ CORRECTO (assets de UI: controles, neumáticos, clima)
resources/                ℹ️ Contiene preview.png
```

**¿Qué diferencia hay?**

- **`images/`**: Assets del UI (botones, iconos, etc.)
  - `controls/` - Controles del reproductor
  - `tyres/` - Estados de neumáticos
  - `weather/` - Iconos de clima

- **`resources/`**: Recursos adicionales
  - `preview.png` - Captura de pantalla del proyecto

**Acción:** **MANTENER AMBOS** porque:
- `images/` son assets de la aplicación
- `resources/` son recursos de documentación

**Alternativa (opcional):** Renombrar a:
```
assets/
├── ui/          (lo que ahora es images/)
└── media/       (lo que ahora es resources/)
```

---

### 7. MAKEFILE (CORRECTO ✅)

```
Makefile                  ✅ CORRECTO - ¡NO BORRAR!
```

**¿Para qué es?**
El Makefile proporciona comandos rápidos para desarrolladores:

```bash
make test          # Ejecutar tests
make lint          # Linting con ruff
make format        # Formatear código
make coverage      # Reporte de coverage
make clean         # Limpiar caches
```

**Beneficios:**
- Comandos consistentes para todo el equipo
- Documentación ejecutable
- Onboarding más rápido

**Acción:** **MANTENER** - Es una buena práctica.

---

## 🎯 PLAN DE ACCIÓN

### OPCIÓN 1: Script Automático (Recomendado)

```bash
# Ejecutar script de limpieza
./scripts/utilities/cleanup_deep.sh
```

El script:
- ✅ Pide confirmación antes de cada acción
- ✅ Muestra el tamaño de lo que se borra
- ✅ Crea backups si es necesario

---

### OPCIÓN 2: Manual (Para Control Total)

```bash
# 1. Borrar entornos virtuales duplicados
rm -rf f1-venv/
rm -rf f1-prediction-venv/

# 2. Borrar caches
rm -rf .ruff_cache/ .pytest_cache/ htmlcov/
rm -f .coverage

# 3. Borrar computed_data
rm -rf computed_data/

# 4. Reorganizar documentación
mv CLEANUP_SUMMARY.md docs/history/
mv PROJECT_STRUCTURE_AUDIT.md docs/
cp -r history/* docs/history/
rm -rf history/

# 5. Limpiar modelos antiguos
rm -rf models/v1.1.0/
rm -rf models/.archive_20251230_011549/

# 6. Verificar .gitignore
cat .gitignore  # Asegurar que todo esté cubierto

# 7. Regenerar caches limpios
make test       # Regenera .pytest_cache y .coverage
make lint       # Regenera .ruff_cache
```

---

## 🏗️ ESTRUCTURA FINAL RECOMENDADA

```
f1-race-replay/
├── .github/                    # ✅ CI/CD workflows
│   └── workflows/
├── .venv/                      # ✅ Único entorno virtual (uv)
├── assets/                     # ℹ️ (Opcional) Renombrar images/ + resources/
│   ├── ui/
│   └── media/
├── data/                       # ✅ Datos del proyecto
│   ├── raw/                    # Datos originales (no procesados)
│   └── processed/              # Datos procesados (cache)
├── docs/                       # ✅ Documentación
│   ├── history/                # Documentos históricos
│   ├── PROJECT_CLEANUP_GUIDE.md
│   └── *.md
├── images/                     # ✅ Assets de UI (si no renombras)
│   ├── controls/
│   ├── tyres/
│   └── weather/
├── logs/                       # ✅ Logs (en .gitignore)
├── models/                     # ✅ Modelos ML (en .gitignore)
│   ├── latest → v1.2.0         # Symlink a versión actual
│   ├── v1.2.0/                 # Versión en producción
│   └── README.md
├── notebooks/                  # ✅ Notebooks de exploración
│   ├── explore_dataset.ipynb
│   └── train_production_model.ipynb
├── resources/                  # ✅ Recursos adicionales (si no renombras)
│   └── preview.png
├── scripts/                    # ✅ Scripts utilitarios
│   ├── training/
│   └── utilities/
├── src/                        # ✅ Código fuente
│   ├── f1_data/
│   ├── interfaces/
│   ├── ml/
│   ├── ui_components/
│   └── utils/
├── tests/                      # ✅ Tests
│   ├── integration/
│   └── unit/
├── .env.example                # ✅ Plantilla de variables de entorno
├── .gitignore                  # ✅ Ignorar temporales y secretos
├── .pre-commit-config.yaml     # ✅ Pre-commit hooks
├── main.py                     # ✅ Entry point
├── Makefile                    # ✅ Comandos comunes
├── pyproject.toml              # ✅ Configuración del proyecto
├── README.md                   # ✅ Documentación principal
└── requirements.txt            # ⚠️ (Deprecated - usar pyproject.toml)

ARCHIVOS/DIRECTORIOS ELIMINADOS:
❌ f1-venv/
❌ f1-prediction-venv/
❌ .ruff_cache/
❌ .pytest_cache/
❌ htmlcov/
❌ .coverage
❌ computed_data/
❌ history/
❌ CLEANUP_SUMMARY.md (movido a docs/history/)
❌ PROJECT_STRUCTURE_AUDIT.md (movido a docs/)
❌ models/v1.1.0/
❌ models/.archive_20251230_011549/
```

---

## 🚦 SIGUIENTES PASOS

### 1. Ejecutar Limpieza

```bash
# Opción A: Script automático
./scripts/utilities/cleanup_deep.sh

# Opción B: Manual (ver arriba)
```

### 2. Verificar que Todo Funciona

```bash
# Activar entorno
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Verificar tests
make test

# Verificar linting
make lint

# Verificar que la app arranca
python main.py
```

### 3. Commit de Cambios

```bash
git status
git add .
git commit -m "chore: deep cleanup - remove duplicate venvs, reorganize docs, clean caches"
```

### 4. Actualizar Documentación

```bash
# Actualizar README.md con estructura limpia
# Actualizar docs/ con guías de desarrollo
```

---

## 📚 GLOSARIO

| Término | Qué es | ¿Borrar? |
|---------|--------|----------|
| `.venv/` | Entorno virtual de Python | ✅ MANTENER |
| `*-venv/` | Entornos virtuales duplicados | ❌ BORRAR |
| `.ruff_cache/` | Cache de Ruff linter | ❌ BORRAR (se regenera) |
| `.pytest_cache/` | Cache de pytest | ❌ BORRAR (se regenera) |
| `.fastf1-cache/` | Cache de datos de FastF1 | ✅ MANTENER |
| `htmlcov/` | Reporte HTML de coverage | ❌ BORRAR (se regenera) |
| `.coverage` | Datos de coverage | ❌ BORRAR (se regenera) |
| `computed_data/` | Directorio vacío sin uso | ❌ BORRAR |
| `models/v1.1.0/` | Modelo antiguo | ❌ BORRAR (usar v1.2.0) |
| `Makefile` | Comandos de desarrollo | ✅ MANTENER |

---

## ✅ CHECKLIST DE LIMPIEZA

Antes de continuar desarrollo, asegúrate de:

- [ ] Solo existe `.venv/` (no `f1-venv/` ni `f1-prediction-venv/`)
- [ ] No hay caches en root (`.ruff_cache/`, `.pytest_cache/`, `htmlcov/`)
- [ ] Documentación está en `docs/` (no en root)
- [ ] Solo existe `models/v1.2.0/` y `models/latest` (symlink)
- [ ] `computed_data/` borrado
- [ ] `history/` consolidado en `docs/history/`
- [ ] `.gitignore` cubre todos los temporales
- [ ] `make test` funciona
- [ ] `make lint` funciona
- [ ] `python main.py` arranca correctamente

---

**Autor:** Gentleman-AI System  
**Última Actualización:** 2025-12-30  
**Versión:** 1.0.0
