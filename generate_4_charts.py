import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

CSV = 'data/research/nq_5m_polygon.csv'
df = pd.read_csv(CSV)
df['et'] = pd.to_datetime(df['Datetime_ET'])
df['date'] = df['et'].dt.date
df['time'] = df['et'].dt.time
df['dow'] = df['et'].dt.weekday

targets = [
    ('LUNES_BULL', 0, 'BULL'),
    ('MARTES_BULL', 1, 'BULL'),
    ('JUEVES_BEAR', 3, 'BEAR'),
    ('VIERNES_BEAR', 4, 'BEAR')
]

best_dates = []

# Scan for perfect textbook days
for label, dow, t_dir in targets:
    subset = df[df['dow'] == dow]
    best_day = None
    best_score = -999999
    
    for d in subset['date'].unique():
        day = subset[subset['date'] == d]
        
        o30 = day[(day['time'] >= pd.to_datetime('09:30', format='%H:%M').time()) & 
                  (day['time'] <= pd.to_datetime('09:59', format='%H:%M').time())]
        ny_core = day[(day['time'] > pd.to_datetime('09:59', format='%H:%M').time()) & 
                      (day['time'] <= pd.to_datetime('15:59', format='%H:%M').time())]
        
        full_day = day[day['time'] >= pd.to_datetime('00:00', format='%H:%M').time()]
        
        if len(o30) < 6 or len(ny_core) < 20 or len(full_day) < 80: continue
        
        o_open = float(o30.iloc[0]['Open'])
        o_close = float(o30.iloc[-1]['Close'])
        o_mv = o_close - o_open
        
        entry_price = float(ny_core.iloc[0]['Open'])
        
        if t_dir == 'BULL' and o_mv <= 10: continue
        if t_dir == 'BEAR' and o_mv >= -10: continue
        
        ny_max = float(ny_core['High'].max())
        ny_min = float(ny_core['Low'].min())
        ny_close = float(ny_core.iloc[-1]['Close'])
        
        if t_dir == 'BULL':
            profit = ny_close - entry_price
            drawdown = entry_price - ny_min
            score = profit - (drawdown * 2.5) 
            if profit > 150 and drawdown < 40 and score > best_score:
                best_score = score
                best_day = d
        else:
            profit = entry_price - ny_close
            drawdown = ny_max - entry_price
            score = profit - (drawdown * 2.5)
            if profit > 150 and drawdown < 40 and score > best_score:
                best_score = score
                best_day = d
                
    if best_day:
        best_dates.append((label, best_day, t_dir))

for label, date_str, t_dir in best_dates:
    day = df[df['date'] == pd.to_datetime(date_str).date()].copy()
    day = day[(day['time'] >= pd.to_datetime('00:00', format='%H:%M').time()) & 
              (day['time'] <= pd.to_datetime('16:15', format='%H:%M').time())] 
    day.set_index('et', inplace=True)
    
    fig, ax = plt.subplots(figsize=(15, 7.5), facecolor='#080814')
    ax.set_facecolor('#080814')
    
    up_color = '#10b981'
    down_color = '#ef4444'
    
    for idx, row in day.iterrows():
        color = up_color if row['Close'] >= row['Open'] else down_color
        ax.plot([idx, idx], [row['Low'], row['High']], color=color, linewidth=1.5, alpha=0.9)
        body_bottom = min(row['Open'], row['Close'])
        body_top = max(row['Open'], row['Close'])
        body_height = max(body_top - body_bottom, 0.5) 
        ax.add_patch(plt.Rectangle((mdates.date2num(idx)-0.0015, body_bottom), 0.003, body_height, 
                                   fill=True, color=color))
        
    y_min, y_max = ax.get_ylim()
    
    def get_time(hour, minute):
        t = pd.to_datetime(f"{date_str} {str(hour).zfill(2)}:{str(minute).zfill(2)}:00")
        if t in day.index: return t
        return day.index[day.index.searchsorted(t)] if t <= day.index[-1] else day.index[-1]
        
    t_lon_end = get_time(8, 0)
    t_ny_apertura = get_time(9, 30)
    t_or_end = get_time(10, 0)
    t_ny_close = get_time(16, 0)
    t_lunch = get_time(12, 0)
            
    # Dim session markers slightly to bring focus to the NY core session
    ax.axvspan(day.index[0], t_lon_end, color='#047857', alpha=0.08)
    ax.text(day.index[0] + (t_lon_end - day.index[0])/2, y_max - (y_max-y_min)*0.03, 
            'PRE-NY (ASIA / LONDRES)', color='#34d399', ha='center', fontweight='bold', fontsize=10, alpha=0.6)
            
    ax.axvspan(t_lon_end, t_ny_apertura, color='#b45309', alpha=0.08)
            
    # 9:30 to 10:00 EXPLICIT WAITING BOX
    or_data = day[(day.index >= t_ny_apertura) & (day.index <= t_or_end)]
    if len(or_data) > 0:
        or_h = or_data['High'].max()
        or_l = or_data['Low'].min()
        
        # Sombreado azul brillante para la ventana de espera de 30 minutos
        ax.axvspan(t_ny_apertura, t_or_end, color='#0284c7', alpha=0.3)
        ax.axvline(x=t_ny_apertura, color='#38bdf8', linestyle='-', linewidth=2, zorder=6)
        ax.text(t_ny_apertura, y_min + (y_max-y_min)*0.05, "APERTURA 9:30", color='#38bdf8', fontweight='bold', rotation=90, va='bottom', ha='right', fontsize=12)
        
        ax.axvline(x=t_or_end, color='#eab308', linestyle=':', linewidth=2, zorder=6)
        
        entry_p = or_data.iloc[-1]['Close']
        ny_close_px = day[day.index <= t_ny_close].iloc[-1]['Close']
        res_pts = ny_close_px - entry_p
        
        # STOP LOSS line explicit
        if t_dir == 'BULL':
            stop_price = or_l
            fill_color = up_color
            ax.hlines(y=stop_price, xmin=t_ny_apertura, xmax=t_ny_close, color='#fca5a5', linestyle='-', linewidth=2, zorder=5)
            ax.text(t_ny_apertura, stop_price - (y_max-y_min)*0.02, f"STOP LOSS (-): {stop_price:.0f}", color='#fca5a5', fontweight='bold', fontsize=11, zorder=6)
        else:
            stop_price = or_h
            fill_color = down_color
            ax.hlines(y=stop_price, xmin=t_ny_apertura, xmax=t_ny_close, color='#fca5a5', linestyle='-', linewidth=2, zorder=5)
            ax.text(t_ny_apertura, stop_price + (y_max-y_min)*0.02, f"STOP LOSS (-): {stop_price:.0f}", color='#fca5a5', fontweight='bold', fontsize=11, zorder=6)
        
        # BIG DOT at ENTRY
        ax.plot([t_or_end], [entry_p], marker='o', markersize=12, color='#ffffff', markeredgecolor='#000000', markeredgewidth=2, zorder=10)
        ax.annotate(f"[ ENTRADA 10:00 AM ]\n(Comienza el movimiento)", xy=(t_or_end, entry_p), 
                    xytext=(t_or_end + pd.Timedelta(minutes=30), entry_p + ((y_max-y_min)*0.1 if t_dir=='BEAR' else -(y_max-y_min)*0.1)),
                    color='#ffffff', fontweight='bold', fontsize=12,
                    arrowprops=dict(facecolor='#ffffff', headwidth=6, headlength=6, width=1.5),
                    bbox=dict(facecolor='#1e2235', edgecolor='#ffffff', boxstyle='round,pad=0.4'), zorder=10)
        
        # Line for 12PM Lunch
        ax.axvline(x=t_lunch, color='#a8a29e', linestyle='--', linewidth=1.5, alpha=0.5, zorder=4)
        lunch_px = day[day.index <= t_lunch].iloc[-1]['Close']
        ax.plot([t_lunch], [lunch_px], marker='s', markersize=8, color='#a8a29e', zorder=9)
        ax.text(t_lunch, y_max - (y_max-y_min)*0.1, "Mediodia\n(Lunch)", color='#a8a29e', fontweight='bold', ha='center', fontsize=10)

        # BIG DOT at TP (Close)
        ax.plot([t_ny_close], [ny_close_px], marker='*', markersize=18, color='#fbbf24', markeredgecolor='#000000', markeredgewidth=1.5, zorder=10)
        ax.annotate(f"[ TOMA DE GANANCIA (Cierre) ]", xy=(t_ny_close, ny_close_px), 
                    xytext=(t_ny_close - pd.Timedelta(minutes=150), ny_close_px + ((y_max-y_min)*0.12 if t_dir=='BULL' else -(y_max-y_min)*0.12)),
                    color='#fbbf24', fontweight='bold', fontsize=12,
                    arrowprops=dict(facecolor='#fbbf24', headwidth=6, headlength=6, width=1.5),
                    bbox=dict(facecolor='#1e2235', edgecolor='#fbbf24', boxstyle='round,pad=0.4'), zorder=10)

        # BIG LINE FROM ENTRY TO TP
        ax.plot([t_or_end, t_ny_close], [entry_p, ny_close_px], color=fill_color, linewidth=4, linestyle='-.', zorder=4)

        # SHADED PROFIT AREA TO VISUALLY PROVE IT
        ax.fill_between([t_or_end, t_ny_close], [entry_p]*2, [entry_p, ny_close_px], color=fill_color, alpha=0.15, zorder=3)
        
        ax.text(t_or_end + (t_ny_close - t_or_end)/2, (entry_p + ny_close_px)/2, 
                f">> GANASTE: {res_pts:+.0f} PUNTOS <<",
                color=fill_color, fontweight='bold', fontsize=18, ha='center', va='center', rotation=-15 if t_dir=='BEAR' else 15, zorder=6,
                bbox=dict(facecolor='#080814', edgecolor=fill_color, alpha=0.8, boxstyle='round,pad=0.4'))

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(color='#94a3b8', fontsize=11)
    plt.yticks(color='#94a3b8', fontsize=11)
    for spine in ax.spines.values(): spine.set_color('#1e2235')
    
    hlt = label.replace('_', ' ')
    plt.title(f"OPERACION COMPLETA: {hlt} ({date_str})", color='#ffffff', fontsize=18, pad=20, fontweight='bold')
    plt.grid(True, color='#1e2235', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"chart_{label.lower()}.png", dpi=150, facecolor='#080814', bbox_inches='tight')
    plt.close()
    print(f"Generado {label}")
