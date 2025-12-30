"""Quick script to check historical data availability."""
import pandas as pd
from pathlib import Path

historical_file = Path("data/processed/historical_races.csv")

if historical_file.exists():
    df = pd.read_csv(historical_file)
    print(f"✅ Archivo existe: {historical_file}")
    print(f"📊 Total registros: {len(df)}")
    print(f"📅 Años disponibles: {df['year'].min()} - {df['year'].max()}")
    print(f"🏁 Total carreras: {df.groupby(['year', 'round_number']).ngroups}")
    print(f"\n📋 Desglose por año:")
    year_counts = df.groupby('year')['round_number'].nunique()
    for year, count in year_counts.items():
        print(f"  {year}: {count} carreras")
else:
    print(f"❌ Archivo no existe: {historical_file}")
    print("💡 Necesitas ejecutar el script de recolección de datos primero")

