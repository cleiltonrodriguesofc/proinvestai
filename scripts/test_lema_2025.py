import os
from pathlib import Path
from app.application.services.alm_engine import ALMEngine

def main():
    config_path = Path("app/alm/config/ipsemb_2026.json")
    
    print("=== INICIANDO VALIDAÇÃO LEMA 2025 ===")
    
    engine = ALMEngine(config_path)
    engine.load_cashflows()
    
    result = engine.run(n_scenarios=100)
    
    print("\n--- FRONTEIRA EFICIENTE (10 PORTFÓLIOS) ---")
    for p in result.efficient_frontier:
        print(f"\nPortfólio {p.portfolio_id} | Retorno: {p.expected_return}% | Volatilidade: {p.volatility}% | Sharpe: {p.sharpe_ratio}")
        for asset, weight in sorted(p.weights.items(), key=lambda x: -x[1]):
            if weight > 0.005:
                print(f"  - {asset}: {weight*100:.1f}%")

    if result.recommended_portfolio:
        print(f"\n[RECOMENDADO] Portfólio {result.recommended_portfolio.portfolio_id} foi selecionado pelo maior Sharpe.")

    print("\n--- TESTE DE SOLVÊNCIA (CARTEIRA RECOMENDADA) ---")
    sr = result.solvency_results[0]
    print(f"Probabilidade de Solvência: {sr.pct_solvent}%")
    print(f"Funding Ratio Médio: {sr.mean_funding_ratio:.2f}")

    print("\n--- ALOCAÇÃO DE NTN-B (MATCHING) ---")
    for b in result.bond_allocations:
        print(f"{b.period}: {b.bond_name} ({b.weight_total*100:.1f}% da carteira)")

if __name__ == "__main__":
    main()
