import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

CSV = 'data/research/nq_5m_polygon.csv'
df = pd.read_csv(CSV)
df['et'] = pd.to_datetime(df['Datetime_ET'])
df['date'] = df['et'].dt.date
df['time'] = df['et'].dt.time

# Filtrar el día: 19 Abril 2024
day = df[df['date'] == pd.to_datetime('2024-04-19').date()].copy()

# Nos quedamos con la sesión de 09:30 a 16:00
day = day[(day['time'] >= pd.to_datetime('09:30', format='%H:%M').time()) & 
          (day['time'] <= pd.to_datetime('16:00', format='%H:%M').time())]

day.set_index('et', inplace=True)

# Crear plot
fig, ax = plt.subplots(figsize=(14, 7), facecolor='#080814')
ax.set_facecolor('#080814')

# Color de velas
up_color = '#10b981'
down_color = '#ef4444'

for idx, row in day.iterrows():
    color = up_color if row['Close'] >= row['Open'] else down_color
    # Mecha
    ax.plot([idx, idx], [row['Low'], row['High']], color=color, linewidth=1.5)
    # Cuerpo
    body_bottom = min(row['Open'], row['Close'])
    body_top = max(row['Open'], row['Close'])
    body_height = body_top - body_bottom
    # Pequeño hack de matplotlib para cuerpo de velas
    ax.add_patch(plt.Rectangle((mdates.date2num(idx)-0.0015, body_bottom), 0.003, body_height, 
                               fill=True, color=color))

# Marcar el rango de 30 min (9:30 a 10:00)
or_data = day.between_time('09:30', '09:59')
or_high = or_data['High'].max()
or_low = or_data['Low'].min()
or_open = or_data.iloc[0]['Open']
or_close = or_data.iloc[-1]['Close']
t_start = or_data.index[0]
t_end = or_data.index[-1]

# Dibujar la caja del OR
ax.axvspan(t_start, t_end, color='white', alpha=0.05)
ax.hlines(y=or_high, xmin=t_start, xmax=day.index[-1], color='#ef4444', linestyle='--', linewidth=1.5, alpha=0.8)
ax.hlines(y=or_low, xmin=t_start, xmax=day.index[-1], color='#64748b', linestyle=':', linewidth=1, alpha=0.5)

# Textos explicativos en el gráfico
ax.text(t_start, or_high + 20, f"STOP LOSS (Máx OR): {or_high:.0f}", color='#ef4444', fontsize=11, fontweight='bold')
ax.text(t_end + pd.Timedelta(minutes=15), or_close + 10, "10:00 AM: OR cierra BEAR\n¡ENTRADA EN VENTA (SHORT)!", color='#38bdf8', fontsize=12, fontweight='bold',
        bbox=dict(facecolor='#0e0e1c', edgecolor='#38bdf8', boxstyle='round,pad=0.5'))

ax.annotate('', xy=(t_end + pd.Timedelta(minutes=5), or_close-10), 
            xytext=(t_end + pd.Timedelta(minutes=5), or_close+50),
            arrowprops=dict(facecolor='#ef4444', shrink=0.05, width=3, headwidth=10))

# Cierre
ny_close = day.iloc[-1]['Close']
ax.text(day.index[-1], ny_close - 30, f"CIERRE NY: {ny_close:.0f}\nGANANCIA: -296 pts", color='#10b981', fontsize=12, fontweight='bold', ha='right',
        bbox=dict(facecolor='#0e0e1c', edgecolor='#10b981', boxstyle='round,pad=0.5'))

# Formato visual
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
plt.xticks(color='#94a3b8', fontsize=10)
plt.yticks(color='#94a3b8', fontsize=10)
for spine in ax.spines.values():
    spine.set_color('#1e2235')
plt.title("Ejemplo Real: Viernes 19/04/2024 (OR 30m BEAR)", color='#f59e0b', fontsize=18, pad=20, fontweight='bold')
plt.grid(True, color='#1e2235', linestyle='--', alpha=0.5)
plt.tight_layout()

# Guardar
plt.savefig('or_chart_19apr.png', dpi=150, facecolor='#080814', bbox_inches='tight')
print("Imagen or_chart_19apr.png generada.")
