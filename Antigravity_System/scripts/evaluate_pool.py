import sys
import math

def calculate_il(price_ratio: float) -> float:
    if price_ratio <= 0: return 1.0
    return abs((2 * math.sqrt(price_ratio) / (1 + price_ratio)) - 1)

def evaluate(expected_apy: float, price_shock_ratio: float, days_held: int = 30):
    expected_yield = expected_apy * (days_held / 365.0)
    actual_il = calculate_il(price_shock_ratio)
    
    print("\n🛡️  ARSENAL DECISION ENGINE - LOCAL AUDIT")
    print("-----------------------------------------")
    print(f"Rendement attendu ({days_held} jours) : {expected_yield*100:.2f}%")
    print(f"Impermanent Loss actuel : {actual_il*100:.2f}%")
    
    if actual_il > (expected_yield * 1.5):
        print("\n=> 🔴 SIGNAL : HEDGE (Fuyez la pool en stablecoin)")
    else:
        print("\n=> 🟢 SIGNAL : EXECUTE (Maintenez la position)")
    print("-----------------------------------------\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 evaluate_pool.py <APY_ATTENDU> <RATIO_PRIX>")
        print("Exemple: python3 evaluate_pool.py 0.12 0.85")
        sys.exit(1)
        
    evaluate(float(sys.argv[1]), float(sys.argv[2]))
