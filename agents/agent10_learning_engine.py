import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE  = os.path.join(BASE_DIR, "intelligence_history.jsonl")
WEIGHTS_FILE  = os.path.join(BASE_DIR, "ai_weights.json")
# Must match OUTPUT_FILE in agent12_backtester.py
BACKTEST_FILE = os.path.join(BASE_DIR, "agent12_backtest_results.json")


def run():
    print("🧠 [LEARNING ENGINE]: Analizando rendimiento neural...")

    # Valores base
    weights = {
        "layer1": 0.25,  # Posicionamiento (COT)
        "layer2": 0.20,  # Macro
        "layer3": 0.15,  # Liquidez
        "layer4": 0.15,  # Timing
        "layer5": 0.25,  # Algorithmic (SMC/Prob)
        "status": "Calibrating - Awaiting Backtest Data",
        "last_learning": datetime.datetime.utcnow().isoformat()
    }

    try:
        if os.path.exists(BACKTEST_FILE):
            with open(BACKTEST_FILE, "r") as f:
                bt = json.load(f)

            # win_rate may be stored as float (55.0) or "55.32%" string
            raw_wr = bt.get("win_rate", bt.get("overall_win_rate", 50))
            if isinstance(raw_wr, str):
                raw_wr = float(raw_wr.replace("%", "").strip())
            win_rate = float(raw_wr)

            if win_rate < 50:
                weights["layer5"] = round(weights["layer5"] + 0.05, 2)
                weights["layer2"] = round(weights["layer2"] + 0.05, 2)
                weights["layer1"] = round(weights["layer1"] - 0.10, 2)
                weights["status"] = "Adaptive - Boosting Intel Layers"
            elif win_rate > 60:
                weights["layer1"] = round(weights["layer1"] + 0.05, 2)
                weights["layer5"] = round(weights["layer5"] - 0.05, 2)
                weights["status"] = "Reinforced - Positioning Dominant"
            else:
                # Win rate in 50-60 range: balanced but explicitly acknowledged
                weights["status"] = f"Balanced - WR {win_rate:.1f}% (neutral zone)"

        # Normalise so layers sum to 1.0
        layer_keys = [k for k in weights if k.startswith("layer")]
        total = sum(weights[k] for k in layer_keys)
        for k in layer_keys:
            weights[k] = round(weights[k] / total, 3)

        with open(WEIGHTS_FILE, "w") as f:
            json.dump(weights, f, indent=4)

        print(f"✅ Aprendizaje completado. Estado: {weights['status']}")
        return f"Recalibración finalizada con éxito."

    except Exception as e:
        print(f"❌ Error learning: {str(e)}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    run()
