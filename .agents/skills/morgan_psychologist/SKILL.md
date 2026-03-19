# Skill: Morgan Psychologist (Anti-Bias Engine)

## Description
Skills focused on neutralizing the trader's emotional bias using institutional psychology logic (inspired by Morgan Stanley's market sentiment analysis). It identifies if the current market move is driven by raw data or emotional extremes like FOMO or Panic.

## Input
- Outputs from Agent 1 (Price Change, VIX, VXN)
- Outputs from Agent 3 (GEX)
- Outputs from Agent 4 (Global Bias Score)
- Outputs from Agent 2 (COT Index)

## Analysis Logic
1. **FOMO Detector**: If NDX Change > 1% AND VXN < 18 AND DIX < 40.
   - *Message*: "Advertencia de FOMO. Estás comprando euforia retail. Los datos institucionales no acompañan."
2. **Panic / Capitulation**: If NDX Change < -1.5% AND VXN > 30 AND GEX < -2B.
   - *Message*: "Riesgo de Capitulación. El pánico es real. Mantén la calma, los niveles de soporte SMC están cerca."
3. **Confirmation Bias Check**: If Bias Score > 80.
   - *Message*: "Sesgo de confirmación extremo. Antigravity te desafía: ¿Y si el mercado gira mañana?"

## Action
- Generate specific psychological alerts.
- Adjust "Operational Confidence" based on emotional stability of the market.
