# 🏎️ F1 Race Replay - Usage Guide

## 🚀 Quick Start

### Interactive Mode (Recommended)

Simply run:

```powershell
python main.py
```

You'll see an interactive menu:

```
════════════════════════════════════════════════════════════════════════════════
                    🏎️  F1 RACE REPLAY - SESSION SELECTOR 🏎️
════════════════════════════════════════════════════════════════════════════════

📅 Available Years: 2018-2025
Enter year (default: 2024): 2024

✅ Selected year: 2024

🔍 Fetching race calendar...

🏁 2024 F1 Season - 24 Rounds

────────────────────────────────────────────────────────────────────────────────
Round    Date            Location                       Event Name                    
────────────────────────────────────────────────────────────────────────────────
1        2024-03-02      Sakhir                         Bahrain Grand Prix            
2        2024-03-09      Jeddah                         Saudi Arabian Grand Prix      
3        2024-03-24      Melbourne                      Australian Grand Prix         
...
────────────────────────────────────────────────────────────────────────────────

Enter round number (1-24, default: 1): 5

✅ Selected round: 5 - Miami Grand Prix (2024-05-05)

📺 Available Sessions:
  [R]  Race (default)
  [Q]  Qualifying
  [S]  Sprint
  [SQ] Sprint Qualifying

Enter session type (R/Q/S/SQ, default: R): R

✅ Selected session: Race

════════════════════════════════════════════════════════════════════════════════
📋 SELECTION SUMMARY:
   Year:          2024
   Round:         5 - Miami Grand Prix
   Date:          2024-05-05
   Session:       Race
════════════════════════════════════════════════════════════════════════════════

Proceed? (Y/n): y

🚀 Loading session...
```

---

## 📋 Command Line Options

### Option 1: Interactive Mode

```powershell
python main.py
# or explicitly:
python main.py --interactive
```

### Option 2: Quick Latest Race

```powershell
python main.py --latest
```

Automatically loads the most recent completed race.

### Option 3: CLI Arguments (Advanced)

```powershell
# Specific race
python main.py --year 2024 --round 5

# Qualifying session
python main.py --year 2024 --round 5 --qualifying

# Sprint
python main.py --year 2024 --round 6 --sprint

# Sprint Qualifying
python main.py --year 2024 --round 6 --sprint-qualifying

# Adjust playback speed
python main.py --year 2024 --round 5 --speed 2.0

# Hide HUD
python main.py --year 2024 --round 5 --no-hud
```

---

## 🛠️ Utility Commands

### List All Rounds for a Year

```powershell
python main.py --list-rounds 2024
```

Output:
```
2024 F1 Season Calendar:
────────────────────────────────────────────────────────────────────────────────
Round 1  - Bahrain Grand Prix (Sakhir)
Round 2  - Saudi Arabian Grand Prix (Jeddah)
Round 3  - Australian Grand Prix (Melbourne)
...
```

### List Sprint Weekends

```powershell
python main.py --list-sprints 2024
```

---

## 🎮 Controls (In-Game)

| Key | Action |
|-----|--------|
| **Space** | Play / Pause |
| **←** | Slow down (0.5x) |
| **→** | Speed up (2x) |
| **↑** | Jump forward 10 seconds |
| **↓** | Jump backward 10 seconds |
| **R** | Restart replay |
| **H** | Toggle HUD visibility |
| **ESC** | Exit |

---

## 📊 Features

### 1. **Race Replay**
- Full race telemetry visualization
- Real-time positions, lap times, and gaps
- Tire compound tracking
- Weather conditions
- Track status (green flag, yellow flag, safety car, red flag)

### 2. **Qualifying Replay**
- Q1, Q2, Q3 progression
- Fastest lap times
- Elimination visualization

### 3. **ML Predictions** (When Available)
- Race winner probability
- Expected final position
- Predicted points

### 4. **Track Visualization**
- Accurate circuit layout
- DRS zones
- Speed visualization
- Sector timing

---

## 🔍 Examples

### Watch Monaco 2024 Race
```powershell
python main.py
# Select:
#   Year: 2024
#   Round: 8 (Monaco)
#   Session: R (Race)
```

### Watch 2023 Spa Qualifying
```powershell
python main.py --year 2023 --round 14 --qualifying
```

### Watch Latest Sprint at 1.5x Speed
```powershell
python main.py --latest --sprint --speed 1.5
```

---

## ⚠️ Troubleshooting

### "No data found for this session"

Some sessions (especially 2025) may not have complete data yet. Try:
- Using 2024 or earlier years
- Checking with `--list-rounds 2024` to see available races

### "grid_position validation failed"

This is normal for incomplete data. The app will continue without ML predictions.

### Slow Performance

Reduce playback speed or close other applications. First-time loads cache data for faster subsequent runs.

---

## 📁 Data Caching

The app caches downloaded F1 data in:
- **Windows**: `C:\Users\<user>\AppData\Local\Temp\fastf1`
- **Linux/Mac**: `/tmp/fastf1`

Processed telemetry is cached in:
- `computed_data/`

This makes subsequent runs **much faster**.

---

## 🎯 Recommended Sessions

Great races to watch:

| Year | Round | Event | Why Watch |
|------|-------|-------|-----------|
| 2024 | 5 | Miami GP | Close finish, overtakes |
| 2024 | 14 | Spa | Classic track, strategy battle |
| 2023 | 1 | Bahrain GP | Season opener action |
| 2023 | 16 | Singapore GP | Night race, street circuit |
| 2022 | 1 | Bahrain GP | New regulations debut |

---

**Happy watching! 🏎️💨**
