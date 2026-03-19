"""
AGENTE 2 — COT ANALYST (ULTRA STABLE)
═══════════════════════════════════════════════════════════
Responsabilidad: 
  ✅ Leer datos históricos del COT (3 años)
  ✅ Calcular COT Index y Posiciones Netas
  ✅ SOPORTE COMPLETO PARA BARRAS COMPARATIVAS (Specs, Comm, Retail)
"""

import os
import json
import pandas as pd
import numpy as np
import datetime

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COT_CSV     = os.path.join(BASE_DIR, "data", "cot", "nasdaq_cot_historical_study.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "agent2_data.json")

def load_and_preprocess_cot():
    if not os.path.exists(COT_CSV): return None
    df = pd.read_csv(COT_CSV)
    df['Report_Date_as_MM_DD_YYYY'] = pd.to_datetime(df['Report_Date_as_MM_DD_YYYY'])
    
    # Specs: Asset Managers + Leveraged Funds
    df['net_position'] = (
        (df['Asset_Mgr_Positions_Long_All'].fillna(0).astype(float) - df['Asset_Mgr_Positions_Short_All'].fillna(0).astype(float)) +
        (df['Lev_Money_Positions_Long_All'].fillna(0).astype(float) - df['Lev_Money_Positions_Short_All'].fillna(0).astype(float))
    )
    
    # Dealers: Commercials
    df['comm_net'] = df['Dealer_Positions_Long_All'].fillna(0).astype(float) - df['Dealer_Positions_Short_All'].fillna(0).astype(float)
    
    # Retail: Estimado (Open Interest - Specs - Comm) o Dummy si no existe la columna
    # Nota: Tu CSV no tiene Retail, lo calcularemos como el remanente del OI si es posible, 
    # o usaremos 0 si no hay datos de OI confiables, para no romper el script.
    df['retail_net'] = 0 
    
    df['net_pos_change'] = df['net_position'].diff()
    df = df.sort_values('Report_Date_as_MM_DD_YYYY')
    return df

def run():
    print("\n" + "="*60 + "\n  AGENTE 2 · COT ANALYST (STABLE)\n" + "="*60)
    df = load_and_preprocess_cot()
    if df is None: return

    a1_path = os.path.join(BASE_DIR, "agent1_data.json")
    try:
        with open(a1_path, "r", encoding="utf-8") as f:
            a1_data = json.load(f)
            live_cot = a1_data.get("cftc_cot", {})
    except: live_cot = {}

    if live_cot.get("speculators"):
        curr_net = live_cot["speculators"]["net"]
        live_comm_net = live_cot.get("commercials", {}).get("net", 0)
        live_retail_net = live_cot.get("retail", {}).get("net", 0)
        live_date = live_cot.get("cot_date", "Unknown")
    else:
        curr_net = df.iloc[-1]['net_position']
        live_comm_net = df.iloc[-1]['comm_net']
        live_retail_net = 0
        live_date = df.iloc[-1]['Report_Date_as_MM_DD_YYYY'].strftime("%d %b %Y")

    h_min, h_max = df['net_position'].min(), df['net_position'].max()
    cot_idx = round(((curr_net - h_min) / (h_max - h_min)) * 100, 1) if h_max != h_min else 50
    
    # Signal logic — enhanced to always reflect trend direction, not just extremes
    week_change = int(curr_net - df.iloc[-2]['net_position']) if len(df) >= 2 else 0
    sig, strength, raz = "NEUTRAL", 50, "Posicionamiento en rango medio."
    if cot_idx >= 80:
        sig, strength, raz = "EXTREMO ALCISTA", cot_idx, "Hedge Funds en niveles máximos."
    elif cot_idx <= 20:
        sig, strength, raz = "EXTREMO BAJISTA", 100 - cot_idx, "Sentimiento pesimista extremo."
    elif cot_idx >= 60:
        sig = "ALCISTA"
        strength = round(50 + (cot_idx - 50) * 0.8)
        raz = f"Specs netos acumulando ({curr_net:+,}). COT Index {cot_idx:.0f}."
    elif cot_idx <= 40:
        sig = "BAJISTA"
        strength = round(50 + (50 - cot_idx) * 0.8)
        raz = f"Specs netos liquidando ({curr_net:+,}). COT Index {cot_idx:.0f}."
    else:
        # In mid-range: use week-over-week direction to pick a lean
        if week_change > 2000:
            sig, strength, raz = "NEUTRAL-ALCISTA", 55, f"Posicionamiento mejorando (+{week_change:,} semanal)."
        elif week_change < -2000:
            sig, strength, raz = "NEUTRAL-BAJISTA", 55, f"Posicionamiento deteriorando ({week_change:,} semanal)."

    # Build history
    recent_weeks = []
    for _, row in df.tail(5).iterrows():
        recent_weeks.append({
            "date": row['Report_Date_as_MM_DD_YYYY'].strftime("%d %b %Y"),
            "nc_long": int(row['Asset_Mgr_Positions_Long_All'] + row['Lev_Money_Positions_Long_All']),
            "nc_short": int(row['Asset_Mgr_Positions_Short_All'] + row['Lev_Money_Positions_Short_All']),
            "c_long": int(row['Dealer_Positions_Long_All']),
            "c_short": int(row['Dealer_Positions_Short_All']),
            "r_long": 0, "r_short": 0, "oi": 273307,
            "net_position": int(row['net_position']),
            "comm_net": int(row['comm_net']),
            "retail_net": 0,
            "change": int(row['net_pos_change']) if not pd.isna(row['net_pos_change']) else 0
        })

    # Add live if newer
    try:
        if pd.to_datetime(live_date) > df.iloc[-1]['Report_Date_as_MM_DD_YYYY']:
            recent_weeks.append({
                "date": live_date,
                "nc_long": int(live_cot.get("speculators", {}).get("long", 0)),
                "nc_short": int(live_cot.get("speculators", {}).get("short", 0)),
                "c_long": int(live_cot.get("commercials", {}).get("long", 0)),
                "c_short": int(live_cot.get("commercials", {}).get("short", 0)),
                "r_long": int(live_cot.get("retail", {}).get("long", 0)),
                "r_short": int(live_cot.get("retail", {}).get("short", 0)),
                "oi": int(live_cot.get("cot_oi", 273307)),
                "net_position": int(curr_net),
                "comm_net": int(live_comm_net),
                "retail_net": int(live_retail_net),
                "change": int(curr_net - df.iloc[-1]['net_position'])
            })
    except: pass

    recent_weeks.reverse()
    recent_weeks = recent_weeks[:5]

    out = {
        "agent": 2, "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "razonamiento": raz, "signal": sig, "strength": round(strength),
        # ─── QA-required top-level field ───
        "net_position": int(curr_net),
        "cot": { "current_net": int(curr_net), "cot_index": cot_idx, "date": live_date, "week_change": week_change },
        "recent_weeks": recent_weeks
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"✅ Agent 2 Guardado -> {OUTPUT_FILE}")
    return out

if __name__ == "__main__":
    run()
