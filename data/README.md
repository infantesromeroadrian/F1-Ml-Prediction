# F1 Race Prediction - Data Collection

Este directorio contiene los scripts y datos para el modelo de predicción de ganadores de F1.

## Estructura

```
data/
  raw/                    # Datos crudos (si es necesario)
  processed/              # Datos procesados listos para ML
    historical_races.csv # Dataset principal con todas las features
  README.md             # Este archivo
```

## Uso

### Recolectar datos históricos

Para recolectar datos de múltiples temporadas:

```bash
python -m src.ml.collect_historical_data --years 2020 2021 2022 2023 2024
```

Para un rango de años:

```bash
python -m src.ml.collect_historical_data --start-year 2020 --end-year 2024
```

Para especificar archivo de salida:

```bash
python -m src.ml.collect_historical_data --years 2023 2024 --output data/processed/my_dataset.csv
```

### Datos recolectados

El script recolecta:

**Features pre-carrera:**
- Posición en parrilla (grid position)
- Resultados de clasificación (Q1, Q2, Q3)
- Tiempos de clasificación

**Features históricas (hasta ese momento):**
- Victorias acumuladas
- Puntos acumulados
- Podios acumulados
- Promedio de posiciones
- Estadísticas del constructor
- Rendimiento histórico en el circuito

**Features contextuales:**
- Información del circuito
- Condiciones meteorológicas
- Año y ronda

**Target variables:**
- Posición final en la carrera
- ¿Ganó? (winner: 1/0)
- Puntos obtenidos
- DNF (Did Not Finish)

## Notas

- El script usa el caché de FastF1 para evitar descargas repetidas
- Los datos se procesan en orden temporal para calcular correctamente las estadísticas históricas
- El proceso puede tardar varios minutos dependiendo de cuántas temporadas se recolecten

