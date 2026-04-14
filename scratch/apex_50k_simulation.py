import random
import sys

# APEX 50k Account Rules
STARTING_BALANCE = 50000
TRAILING_THRESHOLD = 2500 # The trailing drawdown limit
PROFIT_GOAL = 53000

# Trading Parameters
CONTRACTS = 5 # 5 Micro NQ (MNQ) = 0.5 Mini NQ equivalent. 
# In MNQ, 1 point = $2. Therefore 5 MNQ = $10 per point.
DOLLARS_PER_POINT = 2 * CONTRACTS

# Strategy Averages (approximated from NQ studies)
AVG_STOP_LOSS_POINTS = 50 # If the OR is 50 points wide
AVG_TAKE_PROFIT_POINTS = 75 # Standard expansion (1.5x to 2.0x RR)

LOSS_AMOUNT = AVG_STOP_LOSS_POINTS * DOLLARS_PER_POINT # $500 per loss
WIN_AMOUNT = AVG_TAKE_PROFIT_POINTS * DOLLARS_PER_POINT # $750 per win

# Weekly Schedule & Win Rates
# Monday: 71% (BULL/LONG)
# Tuesday: 72% (BULL/LONG)
# Wednesday: 0% (SKIP DAY)
# Thursday: 71% (BEAR/SHORT)
# Friday: 73% (BEAR/SHORT)
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
WIN_RATES = {
    'Monday': 0.71,
    'Tuesday': 0.72,
    'Wednesday': 0.0, # Do not trade
    'Thursday': 0.71,
    'Friday': 0.73
}

def simulate_1_year():
    balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    
    trades_taken = 0
    wins = 0
    losses = 0
    
    # 52 weeks in a year
    for week in range(52):
        for day in DAYS:
            if day == 'Wednesday':
                continue # Skipped
                
            win_rate = WIN_RATES[day]
            
            # Incorporate 15% chance of "No Trade" because conditions weren't met (Filter rule)
            if random.random() < 0.15:
                continue 
                
            trades_taken += 1
            
            # Trade outcome
            if random.random() < win_rate:
                balance += WIN_AMOUNT
                wins += 1
            else:
                balance -= LOSS_AMOUNT
                losses += 1
                
            # Update high water mark
            if balance > high_water_mark:
                high_water_mark = balance
                
            # Check for APEX failure (Trailing Drawdown)
            # Trailing stops updating once starting balance + profit goal is reached usually, 
            # but simplest math: if we drop more than $2,500 below the high water mark, we fail.
            current_drawdown = high_water_mark - balance
            if current_drawdown >= TRAILING_THRESHOLD:
                return {
                    'passed': False, 
                    'final_balance': balance, 
                    'trades': trades_taken, 
                    'wins': wins,
                    'losses': losses,
                    'reason': 'Hit Trailing Drawdown'
                }
                
            # Did we pass? We assume we stop tracking "failure" strictly once passed or we continue trading?
            # Let's see if we pass the 3k goal.
            # We'll just continue to see the full year potential.
            
    return {
        'passed': balance >= PROFIT_GOAL,
        'final_balance': balance,
        'trades': trades_taken,
        'wins': wins,
        'losses': losses,
        'reason': 'Completed 1 Year'
    }

# Run Monte Carlo 10,000 times
simulations = 10000
passed_evals = 0
total_failed = 0
balances_passed = []

for _ in range(simulations):
    res = simulate_1_year()
    if res['passed']:
        passed_evals += 1
        balances_passed.append(res['final_balance'])
    else:
        total_failed += 1

success_rate = (passed_evals / simulations) * 100
avg_final_balance = sum(balances_passed) / len(balances_passed) if balances_passed else 0

print("==================================================")
print(" MONTE CARLO APEX 50k - OR 30m STRATEGY (1 YEAR) ")
print("==================================================")
print(f"Risk per trade: ~${LOSS_AMOUNT} (Stop Loss: {AVG_STOP_LOSS_POINTS} pts with {CONTRACTS} MNQ)")
print(f"Profit per trade: ~${WIN_AMOUNT} (Take Profit: {AVG_TAKE_PROFIT_POINTS} pts with {CONTRACTS} MNQ)")
print(f"Total Simulations: {simulations}")
print(f"Accounts that survived & passed: {passed_evals} ({success_rate:.2f}%)")
print(f"Accounts blown (Hit $2,500 trailing DD): {total_failed} ({(total_failed/simulations)*100:.2f}%)")
if balances_passed:
    print(f"Average Final Balance (if passed): ${avg_final_balance:,.2f} USD")
    print(f"Average NET PROFIT (1 year): ${avg_final_balance - STARTING_BALANCE:,.2f} USD")
print("==================================================")
