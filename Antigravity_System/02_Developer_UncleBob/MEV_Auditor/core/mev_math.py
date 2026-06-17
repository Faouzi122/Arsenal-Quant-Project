# [MODULE: ENTITÉ MATHÉMATIQUE - TORVALDS O(1) COMPLIANT]
# Définit la structure pure de la détection de Slippage. Zéro dépendance externe.

class AMMPoolState:
    def __init__(self, reserve_token_a: int, reserve_token_b: int, fee_tier: float = 0.003):
        self.r_a = reserve_token_a
        self.r_b = reserve_token_b
        self.fee = fee_tier

    def calculate_expected_output(self, amount_in_a: int) -> int:
        """ Formule du Produit Constant (x * y = k) en O(1) """
        amount_in_with_fee = amount_in_a * (1 - self.fee)
        numerator = amount_in_with_fee * self.r_b
        denominator = self.r_a + amount_in_with_fee
        return int(numerator / denominator)

def calculate_s_mev(expected_output: int, actual_output: int) -> int:
    """ Calcule le préjudice financier net (Slippage dû au MEV) """
    if actual_output >= expected_output:
        return 0 # Pas de perte, ou slippage positif
    return expected_output - actual_output
