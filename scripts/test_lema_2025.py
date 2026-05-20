import os
from pathlib import Path
from app.application.services.alm_engine import ALMEngine, calculate_required_return

def main():
    config_path = Path("app/alm/config/ipsemb_2025_lema.json")
    
    print("=== INICIANDO VALIDAÇÃO LEMA 2025 ===")
    
    engine = ALMEngine(config_path)
    engine.load_cashflows()
    
    result = engine.run(n_scenarios=100)
    
    # Calculate ruin year under Meta Atuarial
    ruin_year_meta = "Não Zera"
    current_balance_meta = config_path["patrimony"] if isinstance(config_path, dict) else engine.config["patrimony"]
    meta = engine.config["actuarial_rate"] / 100
    
    # Calculate ruin year under Equilibrium (Required Return)
    ruin_year_eq = "Não Zera"
    current_balance_eq = current_balance_meta
    eq_rate = calculate_required_return(engine.cashflows, current_balance_meta)
    
    for cf in result.cashflows:
        # Meta
        current_balance_meta += (current_balance_meta * meta) + cf.net_flow
        if current_balance_meta <= 0 and ruin_year_meta == "Não Zera":
            ruin_year_meta = str(cf.year)
            
        # Equilibrium
        current_balance_eq += (current_balance_eq * eq_rate) + cf.net_flow
        if current_balance_eq <= 0 and ruin_year_eq == "Não Zera":
            ruin_year_eq = str(cf.year)
            
    print(f"\n[RUÍNA - META ATUARIAL ({meta*100:.2f}%)] Exaustão do patrimônio no ano: {ruin_year_meta}")
    print(f"[RUÍNA - TAXA DE EQUILÍBRIO ({eq_rate*100:.4f}%)] Exaustão do patrimônio no ano: {ruin_year_eq}")
    
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
