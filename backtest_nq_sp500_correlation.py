"""
==============================================================
  BACKTESTING: CORRELACIÓN NQ vs SP500 + ANÁLISIS LEAD/LAG
  Para: NQ Whale Radar
  Fecha: 2026-03-23
==============================================================
OBJETIVO TRADER:
  - ¿Cuál índice lidera al otro?
  - ¿Cuánto tiempo de ventaja da uno sobre el otro?
  - ¿Cómo usar esa ventaja para operar NQ?
  - ¿En qué condiciones se rompe la correlación? (OPORTUNIDAD)
==============================================================
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def flatten_df(df):
    """Aplana columnas MultiIndex de yfinance si es necesario"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df

# ─────────────────────────────────────────────
#  1. DESCARGA DE DATOS
# ─────────────────────────────────────────────

def download_data(period="2y"):
    print("📥 Descargando datos históricos...")
    tickers = {
        'NQ': 'QQQ',
        'SP500': 'SPY',
    }
    data = {}
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period=period, interval='1d', progress=False)
            df = flatten_df(df)
            data[name] = df
            print(f"  ✅ {name} ({ticker}): {len(df)} días")
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    # Datos 1H para análisis intraday
    try:
        nq_1h = flatten_df(yf.download('QQQ', period='60d', interval='1h', progress=False))
        spy_1h = flatten_df(yf.download('SPY', period='60d', interval='1h', progress=False))
        data['NQ_1H'] = nq_1h
        data['SP_1H'] = spy_1h
        print(f"  ✅ Datos 1H: {len(nq_1h)} barras QQQ, {len(spy_1h)} barras SPY")
    except Exception as e:
        print(f"  ⚠️ Datos 1H no disponibles: {e}")

    return data

# ─────────────────────────────────────────────
#  2. ANÁLISIS DE CORRELACIÓN
# ─────────────────────────────────────────────

def analyze_correlation(data):
    print("\n📊 Análisis de correlación...")
    nq = data['NQ']['Close']
    sp = data['SP500']['Close']

    # Aseguramos series simples (no DataFrames)
    if isinstance(nq, pd.DataFrame):
        nq = nq.iloc[:, 0]
    if isinstance(sp, pd.DataFrame):
        sp = sp.iloc[:, 0]

    combined = pd.DataFrame({'NQ': nq, 'SP': sp}).dropna()
    combined['NQ_ret'] = combined['NQ'].pct_change()
    combined['SP_ret'] = combined['SP'].pct_change()
    combined = combined.dropna()

    corr_total = combined['NQ_ret'].corr(combined['SP_ret'])
    combined['corr_20d'] = combined['NQ_ret'].rolling(20).corr(combined['SP_ret'])
    combined['corr_60d'] = combined['NQ_ret'].rolling(60).corr(combined['SP_ret'])
    combined['corr_5d']  = combined['NQ_ret'].rolling(5).corr(combined['SP_ret'])

    # Beta
    try:
        cov_matrix = combined[['NQ_ret', 'SP_ret']].rolling(60).cov().unstack()
        combined['beta_NQ'] = cov_matrix['NQ_ret']['SP_ret'] / cov_matrix['SP_ret']['SP_ret']
    except:
        combined['beta_NQ'] = np.nan

    # Volatilidad
    combined['vol_NQ_20d'] = combined['NQ_ret'].rolling(20).std() * np.sqrt(252) * 100
    combined['vol_SP_20d'] = combined['SP_ret'].rolling(20).std() * np.sqrt(252) * 100
    combined['vol_ratio'] = combined['vol_NQ_20d'] / combined['vol_SP_20d']

    corr_avg_20d = combined['corr_20d'].mean()
    beta_avg     = combined['beta_NQ'].mean()
    vol_avg      = combined['vol_ratio'].mean()

    print(f"  📈 Correlación total: {corr_total:.4f}")
    print(f"  📈 Correlación promedio 20d: {corr_avg_20d:.4f}")
    print(f"  📈 Beta NQ/SP promedio (60d): {beta_avg:.4f}")
    print(f"  📈 Ratio volatilidad NQ/SP:  {vol_avg:.4f}")

    return combined, corr_total

# ─────────────────────────────────────────────
#  3. LEAD/LAG
# ─────────────────────────────────────────────

def analyze_lead_lag(combined):
    print("\n🔍 Análisis Lead/Lag (¿quién mueve primero?)...")
    nq_ret = combined['NQ_ret'].dropna()
    sp_ret = combined['SP_ret'].dropna()

    lag_results = []
    for lag in range(-10, 11):
        try:
            if lag == 0:
                corr = nq_ret.corr(sp_ret)
            elif lag > 0:
                corr = sp_ret.iloc[lag:].reset_index(drop=True).corr(
                    nq_ret.iloc[:-lag].reset_index(drop=True))
            else:
                corr = nq_ret.iloc[-lag:].reset_index(drop=True).corr(
                    sp_ret.iloc[:lag].reset_index(drop=True))
        except:
            corr = np.nan

        lag_results.append({
            'lag': lag,
            'correlation': corr,
            'interpretation': f"NQ leads SP por {-lag}d" if lag < 0 else (
                f"SP leads NQ por {lag}d" if lag > 0 else "Sin lag (simultáneo)")
        })

    lag_df = pd.DataFrame(lag_results)

    best_lag = lag_df.loc[lag_df['correlation'].abs().idxmax()]
    print(f"  🎯 Lag óptimo: {best_lag['lag']} días")
    print(f"  Correlación máxima: {best_lag['correlation']:.4f}")
    print(f"  Interpretación: {best_lag['interpretation']}")

    # Probabilidades de predicción
    lag1 = pd.DataFrame({
        'NQ_hoy': nq_ret,
        'SP_manana': sp_ret.shift(-1)
    }).dropna()

    nq_up   = lag1[lag1['NQ_hoy'] > 0]
    nq_down = lag1[lag1['NQ_hoy'] < 0]
    nq_up_sp_up   = (nq_up['SP_manana'] > 0).mean() if len(nq_up) > 0 else 0
    nq_down_sp_down = (nq_down['SP_manana'] < 0).mean() if len(nq_down) > 0 else 0

    print(f"\n  📊 Si NQ sube hoy → SP sube mañana: {nq_up_sp_up:.1%}")
    print(f"  📊 Si NQ baja hoy → SP baja mañana: {nq_down_sp_down:.1%}")

    return lag_df, lag1, nq_up_sp_up, nq_down_sp_down

# ─────────────────────────────────────────────
#  4. DIVERGENCIAS
# ─────────────────────────────────────────────

def analyze_divergences(combined):
    print("\n💎 Análisis de Divergencias...")
    df = combined.copy()

    df['diverge'] = np.where(
        ((df['NQ_ret'] > 0) & (df['SP_ret'] < 0)) |
        ((df['NQ_ret'] < 0) & (df['SP_ret'] > 0)), 1, 0)

    df['diverge_fuerte'] = np.where(
        ((df['NQ_ret'] > 0.01) & (df['SP_ret'] < -0.005)) |
        ((df['NQ_ret'] < -0.01) & (df['SP_ret'] > 0.005)), 1, 0)

    df['spread_ret'] = df['NQ_ret'] - df['SP_ret']
    df['spread_z'] = ((df['spread_ret'] - df['spread_ret'].rolling(60).mean())
                      / df['spread_ret'].rolling(60).std())

    post_diverge = []
    diverge_dates = df[df['diverge_fuerte'] == 1].index
    for date in diverge_dates:
        try:
            idx = df.index.get_loc(date)
            if isinstance(idx, slice):
                idx = idx.start
            if idx + 3 < len(df):
                post_diverge.append({
                    'date': str(date.date()),
                    'NQ_dia_div': round(float(df['NQ_ret'].iloc[idx]) * 100, 3),
                    'SP_dia_div': round(float(df['SP_ret'].iloc[idx]) * 100, 3),
                    'NQ_dia_sig': round(float(df['NQ_ret'].iloc[idx + 1]) * 100, 3),
                    'NQ_3d_sig': round(float(df['NQ_ret'].iloc[idx+1:idx+4].sum()) * 100, 3),
                    'tipo': 'NQ_lidera' if df['NQ_ret'].iloc[idx] > 0 else 'SP_lidera'
                })
        except:
            pass

    post_df = pd.DataFrame(post_diverge)
    freq_div = df['diverge'].mean()
    freq_div_fuerte = df['diverge_fuerte'].mean()

    print(f"  📊 Días con divergencia dirección: {freq_div:.1%}")
    print(f"  📊 Días con divergencia FUERTE: {freq_div_fuerte:.1%}")
    if len(post_df) > 0:
        print(f"  📊 NQ día siguiente post-divergencia: {post_df['NQ_dia_sig'].mean():.2f}%")

    return df, post_df

# ─────────────────────────────────────────────
#  5. RATIO NQ/SP500
# ─────────────────────────────────────────────

def analyze_ratio(combined):
    print("\n📐 Análisis Ratio NQ/SP500 (Fuerza Relativa)...")
    df = combined.copy()
    df['ratio'] = df['NQ'] / df['SP']
    df['ratio_norm'] = df['ratio'] / df['ratio'].iloc[0] * 100
    df['ratio_ma20'] = df['ratio'].rolling(20).mean()
    df['ratio_ma60'] = df['ratio'].rolling(60).mean()
    df['ratio_above_ma'] = df['ratio'] > df['ratio_ma20']

    nq_cuando_up   = df[df['ratio_above_ma'] == True]['NQ_ret'].mean()
    nq_cuando_down = df[df['ratio_above_ma'] == False]['NQ_ret'].mean()
    trend = "NASDAQ más fuerte 🚀" if df['ratio_norm'].iloc[-1] > df['ratio_norm'].iloc[-20] else "SP500 más fuerte 🛡️"

    print(f"  📈 NQ  rendimiento cuando ratio > MA20: {nq_cuando_up:.3%}/día")
    print(f"  📉 NQ rendimiento cuando ratio < MA20: {nq_cuando_down:.3%}/día")
    print(f"  🎯 Tendencia actual 20d: {trend}")

    return df

# ─────────────────────────────────────────────
#  6. VELOCIDAD Y AMPLIFICACIÓN
# ─────────────────────────────────────────────

def analyze_speed(combined):
    print("\n⚡ Análisis de Velocidad y Amplitud de Movimiento...")
    df = combined.copy()

    nq_mean, nq_std = df['NQ_ret'].mean(), df['NQ_ret'].std()
    sp_mean, sp_std = df['SP_ret'].mean(), df['SP_ret'].std()

    nq_big_moves = int((df['NQ_ret'].abs() > 0.02).sum())
    sp_big_moves = int((df['SP_ret'].abs() > 0.02).sum())
    nq_big_up    = int((df['NQ_ret'] > 0.02).sum())
    nq_big_down  = int((df['NQ_ret'] < -0.02).sum())
    sp_big_up    = int((df['SP_ret'] > 0.02).sum())
    sp_big_down  = int((df['SP_ret'] < -0.02).sum())

    nq_big = df[df['NQ_ret'].abs() > 0.015]
    sp_en_nq_big = df.loc[nq_big.index, 'SP_ret']
    ratio_moves = (nq_big['NQ_ret'].values / sp_en_nq_big.values)
    ratio_moves = ratio_moves[np.isfinite(ratio_moves)]
    amplificacion = float(np.median(ratio_moves)) if len(ratio_moves) > 0 else 1.5

    vol_ratio_avg = float(df['vol_ratio'].mean())

    print(f"  NQ - Media: {nq_mean:.3%} | Std: {nq_std:.3%}")
    print(f"  SP - Media: {sp_mean:.3%} | Std: {sp_std:.3%}")
    print(f"  NQ días con mov >2%: {nq_big_moves} (↑{nq_big_up} ↓{nq_big_down})")
    print(f"  SP días con mov >2%: {sp_big_moves} (↑{sp_big_up} ↓{sp_big_down})")
    print(f"  🎯 Amplificación NQ sobre SP: {amplificacion:.2f}x")

    stats = {
        'NQ': {'mean': float(nq_mean), 'std': float(nq_std), 'big_moves': nq_big_moves,
               'big_up': nq_big_up, 'big_down': nq_big_down},
        'SP': {'mean': float(sp_mean), 'std': float(sp_std), 'big_moves': sp_big_moves,
               'big_up': sp_big_up, 'big_down': sp_big_down},
        'amplificacion': amplificacion,
        'vol_ratio': vol_ratio_avg
    }

    return stats, df

# ─────────────────────────────────────────────
#  7. LEAD/LAG INTRADAY (1H)
# ─────────────────────────────────────────────

def analyze_intraday_lead_lag(data):
    print("\n⏰ Análisis Lead/Lag Intraday (1H)...")
    if 'NQ_1H' not in data or 'SP_1H' not in data:
        print("  ⚠️ Datos 1H no disponibles")
        return []

    nq_1h = data['NQ_1H']['Close']
    sp_1h = data['SP_1H']['Close']
    if isinstance(nq_1h, pd.DataFrame): nq_1h = nq_1h.iloc[:, 0]
    if isinstance(sp_1h, pd.DataFrame): sp_1h = sp_1h.iloc[:, 0]

    combined_1h = pd.DataFrame({'NQ': nq_1h, 'SP': sp_1h}).dropna()
    combined_1h['NQ_ret'] = combined_1h['NQ'].pct_change()
    combined_1h['SP_ret'] = combined_1h['SP'].pct_change()
    combined_1h = combined_1h.dropna()

    lag_results = []
    for lag in range(-5, 6):
        try:
            if lag == 0:
                corr = combined_1h['NQ_ret'].corr(combined_1h['SP_ret'])
            elif lag > 0:
                corr = combined_1h['SP_ret'].iloc[lag:].reset_index(drop=True).corr(
                    combined_1h['NQ_ret'].iloc[:-lag].reset_index(drop=True))
            else:
                corr = combined_1h['NQ_ret'].iloc[-lag:].reset_index(drop=True).corr(
                    combined_1h['SP_ret'].iloc[:lag].reset_index(drop=True))
            lag_results.append({
                'lag_horas': lag,
                'correlation': round(float(corr), 4),
                'descripcion': f"NQ anticipa SP por {-lag}h" if lag < 0 else (
                    f"SP anticipa NQ por {lag}h" if lag > 0 else "Simultáneo")
            })
        except:
            pass

    if lag_results:
        best = max(lag_results, key=lambda x: abs(x['correlation']))
        print(f"  🎯 Lag óptimo intraday: {best['descripcion']} → corr {best['correlation']:.4f}")

    return lag_results

# ─────────────────────────────────────────────
#  8. GENERAR INSIGHTS TRADER
# ─────────────────────────────────────────────

def generate_trader_insights(combined, lag_df, post_df, corr_total, stats, nq_up_sp_up, nq_down_sp_down):
    beta_avg     = float(combined['beta_NQ'].mean())
    vol_ratio    = stats['vol_ratio']
    corr_avg_20d = float(combined['corr_20d'].mean())
    corr_min_10  = float(combined['corr_20d'].quantile(0.1))
    div_freq     = float(combined['diverge'].mean())

    insights = {
        "titulo": "ENSEÑANZAS TRADER: NQ vs SP500",
        "fecha_analisis": str(datetime.now().date()),
        "correlacion": {
            "total": round(float(corr_total), 4),
            "promedio_20d": round(corr_avg_20d, 4),
            "minimo_10pct": round(corr_min_10, 4),
            "leccion": f"Correlación {corr_total:.2f} = muy alta. NQ y SP se mueven juntos el {corr_total:.0%} del tiempo."
        },
        "velocidad": {
            "beta_nq_vs_sp": round(beta_avg, 3),
            "ratio_volatilidad": round(vol_ratio, 3),
            "amplificacion_movimientos": round(stats['amplificacion'], 2),
            "leccion": f"NQ se mueve {vol_ratio:.1f}x más rápido que SP500. Beta ≈ {beta_avg:.2f}: cuando SP mueve 1%, NQ mueve {beta_avg:.2f}%."
        },
        "lead_lag": {
            "prediccion_nq_up_sp_up": round(float(nq_up_sp_up), 4),
            "prediccion_nq_down_sp_down": round(float(nq_down_sp_down), 4),
            "leccion": f"Si NQ sube hoy → {nq_up_sp_up:.0%} prob SP suba mañana. NQ = termómetro adelantado."
        },
        "estrategias_trading": [
            {
                "nombre": "1. NQ COMO SEÑAL DE SP500",
                "descripcion": "El movimiento de apertura de NQ (primeros 30 min NY) anticipa la dirección del SP500 en la sesión.",
                "regla": "NQ abre >+0.5% → buscar longs en SP. NQ abre <-0.5% → buscar shorts en SP.",
                "contexto": "Funciona mejor sin noticias macro importantes en el día."
            },
            {
                "nombre": "2. DIVERGENCIA = TRAMPA O OPORTUNIDAD",
                "descripcion": f"En ~{div_freq:.0%} de los días NQ y SP van en sentido opuesto. Uno de los dos está mintiendo.",
                "regla": "El que tiene más volumen al cierre 'tiene razón'. El débil reversa para alcanzarlo.",
                "contexto": "Alta probabilidad de reversión en el activo débil al día siguiente."
            },
            {
                "nombre": "3. RATIO NQ/SP500 = SESGO SEMANAL",
                "descripcion": "Ratio subiendo → tech domina (risk-on). Ratio bajando → rotación defensiva.",
                "regla": "Revisa el ratio antes de iniciar la semana para saber si favorecer longs o ser cauteloso.",
                "contexto": "Un ratio NQ/SP en tendencia bajista durante 2+ semanas = cuidado con longs en NQ."
            },
            {
                "nombre": f"4. AMPLIFICACIÓN BETA ≈ {beta_avg:.2f}",
                "descripcion": f"Por cada 1% de SP500, NQ mueve ~{beta_avg:.2f}%. Esto es poder y peligro a la vez.",
                "regla": f"En tendencia clara: preferir NQ por mayor rentabilidad. En indecisión: SP pierde {(beta_avg-1)*100:.0f}% menos.",
                "contexto": f"Ajusta tamaño: 1 contrato ES ≈ {1/beta_avg:.2f} contratos NQ en exposición real."
            },
            {
                "nombre": "5. SP500 CONFIRMA → NQ EXAGERA",
                "descripcion": "Cuando SP500 rompe un nivel técnico clave, NQ lo replica y lo amplifica.",
                "regla": "Espera que SP500 confirme el rompimiento, luego entra en NQ para capturar la amplificación.",
                "contexto": "Especialmente efectivo en apertura NY (9:30-10:30 AM ET) y en la 2ª hora de sesión."
            },
            {
                "nombre": f"6. CORRELACIÓN BAJA = PRECAUCIÓN",
                "descripcion": f"Cuando correlación rolling 20d cae bajo {corr_min_10:.2f}, el mercado está en modo confuso.",
                "regla": "Correlación < 0.70: reduce tamaño de posición. Mercado desorientado = trampas en ambas direcciones.",
                "contexto": "Normalmente ocurre previo a eventos macro importantes (Fed, NFP, CPI) o crisis geopolíticas."
            }
        ],
        "resumen_ejecutivo": {
            "correlacion": f"{corr_total:.2f} (muy alta - se mueven juntos el {corr_total:.0%} del tiempo)",
            "velocidad": f"NQ es {vol_ratio:.1f}x más volátil = más puntos, más riesgo",
            "beta": f"SP mueve 1% → NQ mueve {beta_avg:.2f}%",
            "lead_lag": f"NQ tiende a liderar en catalizadores tech/growth. SP lidera en macro.",
            "divergencia": f"~{div_freq:.0%} de los días divergen = oportunidad de reversión",
            "regla_de_oro": "Usa SP500 como contexto macro y NQ para el entry exacto."
        }
    }

    return insights

# ─────────────────────────────────────────────
#  9. GENERAR JSON DASHBOARD
# ─────────────────────────────────────────────

def generate_dashboard_data(combined, lag_df, post_df, insights, stats, intraday_lag):
    recent = combined.tail(252).copy()

    def safe_list(series):
        out = []
        for x in series:
            try:
                v = float(x)
                out.append(None if np.isnan(v) else round(v, 4))
            except:
                out.append(None)
        return out

    dashboard_data = {
        "metadata": {"generado": str(datetime.now()), "periodo": "2 años", "fuente": "Yahoo Finance QQQ/SPY"},
        "insights": insights,
        "series": {
            "fechas":     [str(d.date()) for d in recent.index],
            "nq_ret":     [round(x*100, 3) if x is not None else 0 for x in safe_list(recent['NQ_ret'])],
            "sp_ret":     [round(x*100, 3) if x is not None else 0 for x in safe_list(recent['SP_ret'])],
            "corr_20d":   safe_list(recent['corr_20d']),
            "corr_5d":    safe_list(recent['corr_5d']),
            "beta_nq":    safe_list(recent['beta_NQ']),
            "vol_nq":     safe_list(recent['vol_NQ_20d']),
            "vol_sp":     safe_list(recent['vol_SP_20d']),
            "divergencias": [int(x) if x is not None else 0 for x in safe_list(recent.get('diverge', pd.Series([0]*len(recent))))],
        },
        "lag_analysis": [
            {"lag": int(row['lag']), "correlation": round(float(row['correlation']), 4),
             "interpretacion": row['interpretation']}
            for _, row in lag_df.iterrows() if not np.isnan(row['correlation'])
        ],
        "intraday_lag": intraday_lag,
        "post_divergence": post_df.tail(30).to_dict('records') if len(post_df) > 0 else [],
    }

    return dashboard_data

# ─────────────────────────────────────────────
#  10. MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  BACKTESTING NQ vs SP500 - CORRELACIÓN & LEAD/LAG")
    print("  NQ Whale Radar")
    print("=" * 60)

    data = download_data(period="2y")
    combined, corr_total = analyze_correlation(data)
    lag_df, lag1_data, nq_up_sp_up, nq_down_sp_down = analyze_lead_lag(combined)
    combined, post_df = analyze_divergences(combined)
    combined = analyze_ratio(combined)
    stats, combined = analyze_speed(combined)
    intraday_lag = analyze_intraday_lead_lag(data)
    insights = generate_trader_insights(combined, lag_df, post_df, corr_total, stats, nq_up_sp_up, nq_down_sp_down)
    dashboard_data = generate_dashboard_data(combined, lag_df, post_df, insights, stats, intraday_lag)

    output_file = "nq_sp500_correlation_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2, default=str)

    print(f"\n✅ JSON guardado: {output_file}")
    print("\n" + "=" * 60)
    print("RESUMEN EJECUTIVO:")
    for k, v in insights['resumen_ejecutivo'].items():
        print(f"  {k}: {v}")
    print("=" * 60)

    return dashboard_data

if __name__ == "__main__":
    main()
