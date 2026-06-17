"""
Infrastructure Layer : Adaptateur RPC Uniswap V2
Conforme aux principes de Clean Architecture (Uncle Bob) et Sympathie Mécanique (Linus Torvalds).
"""
import time
from abc import ABC, abstractmethod
from web3 import Web3

# ==============================================================================
# 1. CONTRAT D'INTERFACE (INVERSION DE DÉPENDANCE)
# ==============================================================================
class IBlockchainStateReader(ABC):
    @abstractmethod
    def get_reserves(self, pool_address: str) -> tuple:
        """Doit retourner (reserve0, reserve1) de manière déterministe."""
        pass

# ==============================================================================
# 2. ADAPTATEUR CONCRET (DÉTAIL D'IMPLÉMENTATION)
# ==============================================================================
class UniswapV2RPCAdapter(IBlockchainStateReader):
    def __init__(self, rpc_url: str, timeout_seconds: float = 1.5):
        # CIRCUIT BREAKER : Rejet immédiat si latence > 1.5s (Loi de Torvalds)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': timeout_seconds}))
        
        # ABI Minimaliste (Soustraction Fabuleuse) : Juste ce qu'il faut pour getReserves
        self.pair_abi = '''[{"constant":true,"inputs":[],"name":"getReserves",
        "outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},
        {"internalType":"uint112","name":"_reserve1","type":"uint112"},
        {"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],
        "payable":false,"stateMutability":"view","type":"function"}]'''

    def get_reserves(self, pool_address: str) -> tuple:
        if not self.w3.is_connected():
            raise ConnectionError("[CIRCUIT BREAKER] Échec de connexion RPC.")
        
        try:
            start_time = time.time()
            checksum_addr = self.w3.to_checksum_address(pool_address)
            contract = self.w3.eth.contract(address=checksum_addr, abi=self.pair_abi)
            
            # Appel On-Chain
            reserves = contract.functions.getReserves().call()
            
            latency = (time.time() - start_time) * 1000
            print(f"[RESEAU] eth_call réussi en {latency:.2f} ms")
            
            return reserves[0], reserves[1]
        except Exception as e:
            raise RuntimeError(f"[ERREUR DÉTERMINISTE] Échec de la lecture d'état : {str(e)}")

# ==============================================================================
# 3. PREUVE D'EXÉCUTION (MOTEUR MATHÉMATIQUE MEV EN O(1))
# ==============================================================================
def get_amount_out(amount_in: int, reserve_in: int, reserve_out: int) -> int:
    """Formule de prix Uniswap V2 : x * y = k (avec frais de 0.3%)"""
    amount_in_with_fee = amount_in * 997
    numerator = amount_in_with_fee * reserve_out
    denominator = (reserve_in * 1000) + amount_in_with_fee
    return numerator // denominator

if __name__ == "__main__":
    print("=== DÉMARRAGE SIMULATION MEV (SANDWICH ATTACK) ===")
    
    # Configuration : Nœud public sans clé API pour réduire la friction (Lean Startup)
    PUBLIC_RPC = "https://ethereum-rpc.publicnode.com"
    # Pool USDC/WETH sur Ethereum Mainnet
    USDC_WETH_POOL = "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc"
    
    adapter = UniswapV2RPCAdapter(rpc_url=PUBLIC_RPC)
    
    try:
        # ÉTAPE 1 : ANCRAGE AU RÉEL (Discipline Fabuleux)
        print("[1] Interrogation de l'état réel de la blockchain...")
        res0, res1 = adapter.get_reserves(USDC_WETH_POOL)
        
        # USDC a 6 décimales, WETH a 18 décimales.
        # Pour simplifier la simulation mathématique, on réduit l'échelle.
        reserve_usdc = res0 / 1e6
        reserve_weth = res1 / 1e18
        
        print(f"    -> État Initial : {reserve_usdc:,.2f} USDC | {reserve_weth:,.2f} WETH")
        print(f"    -> Prix Spot : {(reserve_usdc / reserve_weth):,.2f} USDC/WETH\n")

        # ÉTAPE 2 : PARAMÈTRES DE LA TRANSACTION VICTIME
        victim_weth_in = 10.0 # La victime veut vendre 10 WETH
        attacker_weth_in = 50.0 # L'attaquant intercepte avec 50 WETH (Flash Loan)
        
        print("[2] Exécution de la Sandwich Attack (Mathématiques Pures O(1))...")
        
        # --- A) FRONT-RUN (Attaquant vend WETH pour USDC avant la victime)
        att_usdc_out_1 = get_amount_out(attacker_weth_in, reserve_weth, reserve_usdc)
        res_w_1 = reserve_weth + attacker_weth_in
        res_u_1 = reserve_usdc - att_usdc_out_1
        print(f"    [Front-Run] L'attaquant injecte {attacker_weth_in} WETH et retire {att_usdc_out_1:,.2f} USDC.")
        
        # --- B) VICTIME (Subit un slippage massif car la pool est déséquilibrée)
        vic_usdc_out = get_amount_out(victim_weth_in, res_w_1, res_u_1)
        res_w_2 = res_w_1 + victim_weth_in
        res_u_2 = res_u_1 - vic_usdc_out
        print(f"    [Victime]   La victime injecte {victim_weth_in} WETH mais ne reçoit que {vic_usdc_out:,.2f} USDC.")
        
        # --- C) BACK-RUN (Attaquant revend ses USDC pour récupérer du WETH)
        att_weth_out_2 = get_amount_out(att_usdc_out_1, res_u_2, res_w_2)
        res_w_3 = res_w_2 - att_weth_out_2
        res_u_3 = res_u_2 + att_usdc_out_1
        print(f"    [Back-Run]  L'attaquant réinjecte ses {att_usdc_out_1:,.2f} USDC et retire {att_weth_out_2:,.2f} WETH.")
        
        # ÉTAPE 3 : CONCLUSION ET CREATION DE VALEUR
        profit_net_weth = att_weth_out_2 - attacker_weth_in
        print("\n=== RÉSULTAT DE L'ORACLE (R_NET) ===")
        print(f"Profit Brut Attaquant (S_mev) : {profit_net_weth:.4f} WETH")
        if profit_net_weth > 0:
            print("SIGNAL : [ DELAY ] - Transaction victime toxique, exécution bloquée par l'Antigravity Engine.")
        else:
            print("SIGNAL : [ EXECUTE ] - Voie libre.")

    except Exception as e:
        print(f"\n[!] ERREUR CRITIQUE : {e}")
