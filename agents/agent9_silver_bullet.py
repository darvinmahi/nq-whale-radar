import json
import os
import datetime
import pytz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent9_data.json")

# Silver Bullet windows defined in EST (start_h, start_m, end_h, end_m)
WINDOWS = [
    {"name": "London SB", "start": (3,  0), "end": (4,  0)},
    {"name": "NY AM SB",  "start": (10, 0), "end": (11, 0)},
    {"name": "NY PM SB",  "start": (14, 0), "end": (15, 0)},
]


def minutes_from_midnight(h, m=0):
    return h * 60 + m


def check_silver_bullet():
    print("\n" + "=" * 60)
    print("  AGENTE 9 · SILVER BULLET TRACKER")
    print("=" * 60 + "\n")

    # --- Current NY time ---
    try:
        tz_ny = pytz.timezone("America/New_York")
        now_ny = datetime.datetime.now(tz_ny)
    except Exception:
        # Fallback: subtract 5 h from UTC
        now_ny = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=5)

    current_time_str = now_ny.strftime("%H:%M")
    now_minutes = minutes_from_midnight(now_ny.hour, now_ny.minute)

    active_window = None
    status = "INACTIVO"
    countdown = ""

    for w in WINDOWS:
        w_start = minutes_from_midnight(*w["start"])
        w_end   = minutes_from_midnight(*w["end"])

        if w_start <= now_minutes < w_end:
            # Currently inside this window
            active_window = w["name"]
            status = "ACTIVE"
            mins_left = w_end - now_minutes
            countdown = f"{mins_left} min restantes"
            break

        elif now_minutes < w_start:
            # Next upcoming window today
            active_window = w["name"]
            status = "UPCOMING"
            mins_to = w_start - now_minutes
            h_rem, m_rem = divmod(mins_to, 60)
            countdown = f"En {h_rem}h {m_rem:02d}m" if h_rem > 0 else f"En {m_rem} min"
            break

    if status == "INACTIVO":
        # All today's windows have passed — show next day's first window
        first_start = WINDOWS[0]["start"]
        mins_to_midnight = 24 * 60 - now_minutes
        mins_to_next = mins_to_midnight + minutes_from_midnight(*first_start)
        h_rem, m_rem = divmod(mins_to_next, 60)
        active_window = f"{WINDOWS[0]['name']} (mañana)"
        countdown = f"Próxima sesión en {h_rem}h {m_rem:02d}m"

    # --- Load macro bias for confluence ---
    try:
        data_path = os.path.join(BASE_DIR, "agent4_data.json")
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                a4 = json.load(f)
                macro_bias = a4.get("global_label", "NEUTRAL")
        else:
            macro_bias = "NEUTRAL"
    except Exception:
        macro_bias = "NEUTRAL"

    output = {
        "agent": 9,
        "name": "Silver Bullet Tracker",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "ny_time": current_time_str,
        "status": status,
        "active_window": active_window or "N/A",
        "macro_confluence": macro_bias,
        "action": "BUSCAR FVG PARA ENTRADA" if status == "ACTIVE" else "ESPERAR VENTANA",
        "countdown": countdown,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"🕒 Hora NY: {current_time_str}")
    print(f"🎯 Ventana: {active_window} → {status}  |  {countdown}")


def run():
    check_silver_bullet()


if __name__ == "__main__":
    run()
