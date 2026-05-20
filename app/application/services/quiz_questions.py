# Professional Suitability Questions - CEA/Anbima Level
# 7 Sections x 4 Questions = 28 Questions

QUIZ_QUESTIONS = [
    # SEÇÃO 1: OBJETIVOS DE INVESTIMENTO
    {
        "id": "q1",
        "text": "Qual o seu principal objetivo ao investir seus recursos?",
        "section": "objetivos",
        "options": [
            {"id": "o1a", "text": "Preservar o capital e garantir liquidez imediata.", "score": 1},
            {"id": "o1b", "text": "Gerar uma renda mensal estável para complementar meus gastos.", "score": 2},
            {"id": "o1c", "text": "Aumentar meu patrimônio a longo prazo, superando a inflação.", "score": 3},
            {"id": "o1d", "text": "Maximizar o retorno total, aceitando flutuações agressivas.", "score": 4}
        ]
    },
    {
        "id": "q2",
        "text": "Como você define sua estratégia de novos aportes?",
        "section": "objetivos",
        "options": [
            {"id": "o2a", "text": "Não pretendo fazer novos aportes, apenas manter o que tenho.", "score": 1},
            {"id": "o2b", "text": "Aportes esporádicos quando sobra algum recurso.", "score": 2},
            {"id": "o2c", "text": "Aportes mensais constantes para formação de patrimônio.", "score": 3},
            {"id": "o2d", "text": "Aportes agressivos em momentos de oportunidade de mercado.", "score": 4}
        ]
    },
    {
        "id": "q3",
        "text": "Qual a finalidade principal deste patrimônio específico?",
        "section": "objetivos",
        "options": [
            {"id": "o3a", "text": "Reserva de emergência para imprevistos.", "score": 1},
            {"id": "o3b", "text": "Aposentadoria ou sucessão familiar.", "score": 2},
            {"id": "o3c", "text": "Compra de um bem de alto valor (ex: imóvel) em poucos anos.", "score": 3},
            {"id": "o3d", "text": "Investimento especulativo para ganhos rápidos.", "score": 4}
        ]
    },
    {
        "id": "q4",
        "text": "Qual a sua prioridade em relação à rentabilidade?",
        "section": "objetivos",
        "options": [
            {"id": "o4a", "text": "Priorizo não perder dinheiro, mesmo que ganhe pouco.", "score": 1},
            {"id": "o4b", "text": "Aceito oscilações leves para ganhar um pouco acima do CDI.", "score": 2},
            {"id": "o4c", "text": "Busco retornos significativamente acima da inflação.", "score": 3},
            {"id": "o4d", "text": "Priorizo o máximo retorno, independente do risco de perda.", "score": 4}
        ]
    },

    # SEÇÃO 2: HORIZONTE DE INVESTIMENTO
    {
        "id": "q5",
        "text": "Por quanto tempo você pretende manter o valor principal investido?",
        "section": "horizonte",
        "options": [
            {"id": "o5a", "text": "Menos de 6 meses.", "score": 1},
            {"id": "o5b", "text": "De 6 meses a 2 anos.", "score": 2},
            {"id": "o5c", "text": "De 2 a 5 anos.", "score": 3},
            {"id": "o5d", "text": "Mais de 5 anos.", "score": 4}
        ]
    },
    {
        "id": "q6",
        "text": "Quando você planeja começar a retirar parte dos recursos?",
        "section": "horizonte",
        "options": [
            {"id": "o6a", "text": "Imediatamente ou em poucos meses.", "score": 1},
            {"id": "o6b", "text": "Em 1 ou 2 anos.", "score": 2},
            {"id": "o6c", "text": "Em 5 anos.", "score": 3},
            {"id": "o6d", "text": "Não planejo retiradas nos próximos 10 anos.", "score": 4}
        ]
    },
    {
        "id": "q7",
        "text": "Seu horizonte de investimento pode ser alterado por imprevistos?",
        "section": "horizonte",
        "options": [
            {"id": "o7a", "text": "Sim, dependo desse dinheiro para viver.", "score": 1},
            {"id": "o7b", "text": "Talvez, se tiver um grande imprevisto de saúde/carreira.", "score": 2},
            {"id": "o7c", "text": "Dificilmente, tenho outras reservas para imprevistos.", "score": 3},
            {"id": "o7d", "text": "Não, este capital é totalmente excedente.", "score": 4}
        ]
    },
    {
        "id": "q8",
        "text": "Qual o seu ciclo de vida atual (idade/carreira)?",
        "section": "horizonte",
        "options": [
            {"id": "o8a", "text": "Aposentado, dependendo dos rendimentos.", "score": 1},
            {"id": "o8b", "text": "Próximo da aposentadoria (5-10 anos).", "score": 2},
            {"id": "o8c", "text": "Fase madura da carreira, com renda estável.", "score": 3},
            {"id": "o8d", "text": "Início de carreira, com longo prazo pela frente.", "score": 4}
        ]
    },

    # SEÇÃO 3: TOLERÂNCIA A RISCOS
    {
        "id": "q9",
        "text": "Como você reagiria se seus investimentos caíssem 15% em um mês?",
        "section": "risco",
        "options": [
            {"id": "o9a", "text": "Venderia tudo imediatamente para evitar mais perdas.", "score": 1},
            {"id": "o9b", "text": "Ficaria muito ansioso e buscaria ativos mais seguros.", "score": 2},
            {"id": "o9c", "text": "Entenderia como flutuação normal e manteria o plano.", "score": 3},
            {"id": "o9d", "text": "Aproveitaria a queda para comprar mais ativos baratos.", "score": 4}
        ]
    },
    {
        "id": "q10",
        "text": "Qual a variação máxima negativa anual que você suportaria?",
        "section": "risco",
        "options": [
            {"id": "o10a", "text": "Nenhuma queda. O capital deve ser preservado.", "score": 1},
            {"id": "o10b", "text": "Quedas leves de até 5%.", "score": 2},
            {"id": "o10c", "text": "Quedas moderadas de até 20%.", "score": 3},
            {"id": "o10d", "text": "Qualquer queda, desde que o potencial futuro seja alto.", "score": 4}
        ]
    },
    {
        "id": "q11",
        "text": "Em qual dessas situações você se sente mais confortável?",
        "section": "risco",
        "options": [
            {"id": "o11a", "text": "Retorno fixo de 10% sem risco.", "score": 1},
            {"id": "o11b", "text": "Chance de 12% com risco de perder 2%.", "score": 2},
            {"id": "o11c", "text": "Chance de 20% com risco de perder 10%.", "score": 3},
            {"id": "o11d", "text": "Chance de 50% com risco de perder 30%.", "score": 4}
        ]
    },
    {
        "id": "q12",
        "text": "Você já operou produtos alavancados ou derivativos?",
        "section": "risco",
        "options": [
            {"id": "o12a", "text": "Não, e nem pretendo.", "score": 1},
            {"id": "o12b", "text": "Não conheço o funcionamento.", "score": 2},
            {"id": "o12c", "text": "Sim, esporadicamente para proteção (hedge).", "score": 3},
            {"id": "o12d", "text": "Sim, com frequência para especulação.", "score": 4}
        ]
    },

    # SEÇÃO 4: CONHECIMENTO DO MERCADO
    {
        "id": "q13",
        "text": "Qual a sua formação ou experiência profissional em finanças?",
        "section": "conhecimento",
        "options": [
            {"id": "o13a", "text": "Nenhuma formação ou experiência na área.", "score": 1},
            {"id": "o13b", "text": "Formação em áreas correlatas, mas não atuo na área.", "score": 2},
            {"id": "o13c", "text": "Atuo ou atuei no mercado financeiro.", "score": 3},
            {"id": "o13d", "text": "Possuo certificações profissionais (CPA, CEA, CFP, etc).", "score": 4}
        ]
    },
    {
        "id": "q14",
        "text": "Com qual frequência você acompanha notícias do mercado financeiro?",
        "section": "conhecimento",
        "options": [
            {"id": "o14a", "text": "Raramente ou nunca.", "score": 1},
            {"id": "o14b", "text": "Mensalmente, quando olho meu extrato.", "score": 2},
            {"id": "o14c", "text": "Semanalmente.", "score": 3},
            {"id": "o14d", "text": "Diariamente, várias vezes ao dia.", "score": 4}
        ]
    },
    {
        "id": "q15",
        "text": "Você entende o conceito de 'Marcação a Mercado' em Renda Fixa?",
        "section": "conhecimento",
        "options": [
            {"id": "o15a", "text": "Não faço ideia do que se trata.", "score": 1},
            {"id": "o15b", "text": "Já ouvi falar, mas não sei como afeta meus investimentos.", "score": 2},
            {"id": "o15c", "text": "Entendo que os preços dos títulos podem oscilar antes do vencimento.", "score": 3},
            {"id": "o15d", "text": "Entendo perfeitamente e utilizo para trades de juros.", "score": 4}
        ]
    },
    {
        "id": "q16",
        "text": "Quais ativos você já investiu nos últimos 2 anos?",
        "section": "conhecimento",
        "options": [
            {"id": "o16a", "text": "Apenas Poupança e Tesouro Selic.", "score": 1},
            {"id": "o16b", "text": "CDBs, LCIs e Fundos de Renda Fixa.", "score": 2},
            {"id": "o16c", "text": "Ações, FIIs e COEs.", "score": 3},
            {"id": "o16d", "text": "Opções, Cripto e Ativos Internacionais.", "score": 4}
        ]
    },

    # SEÇÃO 5: SITUAÇÃO FINANCEIRA
    {
        "id": "q17",
        "text": "Qual o valor total do seu patrimônio investido hoje?",
        "section": "situacao",
        "options": [
            {"id": "o17a", "text": "Até R$ 50 mil.", "score": 1},
            {"id": "o17b", "text": "R$ 50 mil a R$ 200 mil.", "score": 2},
            {"id": "o17c", "text": "R$ 200 mil a R$ 1 milhão.", "score": 3},
            {"id": "o17d", "text": "Mais de R$ 1 milhão.", "score": 4}
        ]
    },
    {
        "id": "q18",
        "text": "Qual o percentual da sua renda mensal você consegue poupar?",
        "section": "situacao",
        "options": [
            {"id": "o18a", "text": "Minha renda mal cobre meus gastos.", "score": 1},
            {"id": "o18b", "text": "Até 10% da minha renda.", "score": 2},
            {"id": "o18c", "text": "De 10% a 30% da minha renda.", "score": 3},
            {"id": "o18d", "text": "Mais de 30% da minha renda.", "score": 4}
        ]
    },
    {
        "id": "q19",
        "text": "Qual a sua estabilidade de renda profissional?",
        "section": "situacao",
        "options": [
            {"id": "o19a", "text": "Baixa (sou autônomo ou renda variável).", "score": 1},
            {"id": "o19b", "text": "Média (CLT em setor volátil).", "score": 2},
            {"id": "o19c", "text": "Alta (CLT estável ou empresário sólido).", "score": 3},
            {"id": "o19d", "text": "Altíssima (Servidor público concursado).", "score": 4}
        ]
    },
    {
        "id": "q20",
        "text": "Qual a relação entre seus investimentos e suas dívidas?",
        "section": "situacao",
        "options": [
            {"id": "o20a", "text": "Possuo dívidas que superam meus investimentos.", "score": 1},
            {"id": "o20b", "text": "Possuo dívidas controladas (ex: financiamento imobiliário).", "score": 2},
            {"id": "o20c", "text": "Não possuo dívidas relevantes.", "score": 3},
            {"id": "o20d", "text": "Sou credor (recebo juros de terceiros/empréstimos).", "score": 4}
        ]
    },

    # SEÇÃO 6: NECESSIDADE DE LIQUIDEZ
    {
        "id": "q21",
        "text": "Quanto tempo você conseguiria viver apenas com seus investimentos?",
        "section": "liquidez",
        "options": [
            {"id": "o21a", "text": "Menos de 3 meses.", "score": 1},
            {"id": "o21b", "text": "De 3 a 6 meses.", "score": 2},
            {"id": "o21c", "text": "De 6 meses a 1 ano.", "score": 3},
            {"id": "o21d", "text": "Mais de 2 anos.", "score": 4}
        ]
    },
    {
        "id": "q22",
        "text": "Qual a sua necessidade de resgate imediato (D+0 ou D+1)?",
        "section": "liquidez",
        "options": [
            {"id": "o22a", "text": "Preciso de 100% com liquidez diária.", "score": 1},
            {"id": "o22b", "text": "Preciso de 50% com liquidez diária.", "score": 2},
            {"id": "o22c", "text": "Preciso de apenas 20% com liquidez diária.", "score": 3},
            {"id": "o22d", "text": "Não preciso de liquidez diária para este capital.", "score": 4}
        ]
    },
    {
        "id": "q23",
        "text": "Você possui seguro de vida ou plano de saúde robusto?",
        "section": "liquidez",
        "options": [
            {"id": "o23a", "text": "Não possuo nenhum dos dois.", "score": 1},
            {"id": "o23b", "text": "Apenas plano de saúde.", "score": 2},
            {"id": "o23c", "text": "Apenas seguro de vida.", "score": 3},
            {"id": "o23d", "text": "Possuo ambos com coberturas amplas.", "score": 4}
        ]
    },
    {
        "id": "q24",
        "text": "Como você lida com gastos inesperados?",
        "section": "liquidez",
        "options": [
            {"id": "o24a", "text": "Uso o cheque especial ou cartão.", "score": 1},
            {"id": "o24b", "text": "Resgato meus investimentos principais.", "score": 2},
            {"id": "o24c", "text": "Uso uma reserva específica em conta corrente.", "score": 3},
            {"id": "o24d", "text": "Tenho fluxo de caixa mensal que cobre a maioria dos imprevistos.", "score": 4}
        ]
    },

    # SEÇÃO 7: COMPORTAMENTO EM CRISES
    {
        "id": "q25",
        "text": "O que você faria se a bolsa caísse 50% em um ano (como 2008 ou 2020)?",
        "section": "comportamento",
        "options": [
            {"id": "o25a", "text": "Entraria em pânico e nunca mais investiria em bolsa.", "score": 1},
            {"id": "o25b", "text": "Esperaria recuperar e depois venderia tudo.", "score": 2},
            {"id": "o25c", "text": "Manteria minha estratégia de longo prazo.", "score": 3},
            {"id": "o25d", "text": "Venderia outros ativos para comprar ações na baixa.", "score": 4}
        ]
    },
    {
        "id": "q26",
        "text": "Qual sua visão sobre a relação Risco vs Retorno?",
        "section": "comportamento",
        "options": [
            {"id": "o26a", "text": "Quero o menor risco possível, aceito retornos baixos.", "score": 1},
            {"id": "o26b", "text": "Busco equilíbrio, mas o risco me preocupa.", "score": 2},
            {"id": "o26c", "text": "Aceito risco para ter retornos melhores que a média.", "score": 3},
            {"id": "o26d", "text": "Sem risco não há retorno expressivo, eu abraço o risco.", "score": 4}
        ]
    },
    {
        "id": "q27",
        "text": "Como você se sente ao ver notícias de 'Crashes' financeiros?",
        "section": "comportamento",
        "options": [
            {"id": "o27a", "text": "Muito amedrontado, me faz querer sacar tudo.", "score": 1},
            {"id": "o27b", "text": "Desconfortável, mas tento ignorar.", "score": 2},
            {"id": "o27c", "text": "Analítico, busco entender as causas.", "score": 3},
            {"id": "o27d", "text": "Otimista, vejo como uma 'promoção' de ativos.", "score": 4}
        ]
    },
    {
        "id": "q28",
        "text": "Qual frase melhor descreve sua filosofia de investimento?",
        "section": "comportamento",
        "options": [
            {"id": "o28a", "text": "Segurança em primeiro lugar, sempre.", "score": 1},
            {"id": "o28b", "text": "Devagar e sempre, com foco na estabilidade.", "score": 2},
            {"id": "o28c", "text": "Diversificação inteligente para crescer com segurança.", "score": 3},
            {"id": "o28d", "text": "Sorte favorece os audazes; foco em crescimento explosivo.", "score": 4}
        ]
    },

    # SEÇÃO 8: DIAGNÓSTICO FINANCEIRO (NOVA)
    {
        "id": "q29",
        "text": "Qual a sua despesa mensal média (moradia + alimentação + transporte + saúde)?",
        "section": "diagnostico",
        "options": [
            {"id": "o29a", "text": "Até R$ 3.000.", "score": 1},
            {"id": "o29b", "text": "R$ 3.000 a R$ 8.000.", "score": 2},
            {"id": "o29c", "text": "R$ 8.000 a R$ 15.000.", "score": 3},
            {"id": "o29d", "text": "Mais de R$ 15.000.", "score": 4}
        ]
    },
    {
        "id": "q30",
        "text": "Quantas pessoas dependem financeiramente de você?",
        "section": "diagnostico",
        "options": [
            {"id": "o30a", "text": "5+ pessoas.", "score": 1},
            {"id": "o30b", "text": "3-4 pessoas (família completa).", "score": 2},
            {"id": "o30c", "text": "1-2 pessoas (cônjuge ou filho).", "score": 3},
            {"id": "o30d", "text": "Nenhuma, sou responsável apenas por mim.", "score": 4}
        ]
    },
    {
        "id": "q31",
        "text": "Possui financiamentos ativos (imóvel, veículo, etc.)?",
        "section": "diagnostico",
        "options": [
            {"id": "o31a", "text": "Sim, com parcelas que comprometem > 30% da renda.", "score": 1},
            {"id": "o31b", "text": "Sim, com parcelas controladas (< 30% da renda).", "score": 2},
            {"id": "o31c", "text": "Sim, mas perto de quitar.", "score": 3},
            {"id": "o31d", "text": "Não possuo financiamentos.", "score": 4}
        ]
    },
    {
        "id": "q32",
        "text": "Possui imóveis ou bens de alto valor além dos investimentos?",
        "section": "diagnostico",
        "options": [
            {"id": "o32a", "text": "Não possuo bens relevantes.", "score": 1},
            {"id": "o32b", "text": "Sim, um imóvel onde moro.", "score": 2},
            {"id": "o32c", "text": "Sim, imóvel + veículo.", "score": 3},
            {"id": "o32d", "text": "Sim, patrimônio imobilizado relevante (> R$ 500k).", "score": 4}
        ]
    },

    # SEÇÃO 9: OBJETIVOS DETALHADOS (NOVA)
    {
        "id": "q33",
        "text": "Qual objetivo está mais próximo de acontecer?",
        "section": "objetivos_detalhados",
        "options": [
            {"id": "o33a", "text": "Montar minha reserva de emergência.", "score": 1},
            {"id": "o33b", "text": "Quitar uma dívida ou financiamento.", "score": 2},
            {"id": "o33c", "text": "Comprar/trocar um bem (carro, imóvel).", "score": 3},
            {"id": "o33d", "text": "Gerar renda passiva / aposentadoria.", "score": 4}
        ]
    },
    {
        "id": "q34",
        "text": "Você busca renda mensal dos investimentos para uso corrente?",
        "section": "objetivos_detalhados",
        "options": [
            {"id": "o34a", "text": "Sim, preciso de uma renda mensal fixa dos investimentos.", "score": 1},
            {"id": "o34b", "text": "Gostaria, mas não dependo disso agora.", "score": 2},
            {"id": "o34c", "text": "Não pensei nisso ainda.", "score": 3},
            {"id": "o34d", "text": "Prefiro reinvestir tudo para crescer mais rápido.", "score": 4}
        ]
    },
    {
        "id": "q35",
        "text": "Qual rendimento anual você consideraria satisfatório?",
        "section": "objetivos_detalhados",
        "options": [
            {"id": "o35a", "text": "Acima da poupança já está bom (~7% a.a.).", "score": 1},
            {"id": "o35b", "text": "Quero pelo menos acompanhar a inflação + um pouco mais (~10% a.a.).", "score": 2},
            {"id": "o35c", "text": "Busco retornos de 15-20% ao ano, mesmo com mais risco.", "score": 3},
            {"id": "o35d", "text": "Quero retornos acima de 20%, aceito alta volatilidade.", "score": 4}
        ]
    },
    {
        "id": "q36",
        "text": "Prefere uma carteira simples (poucos ativos) ou mais sofisticada?",
        "section": "objetivos_detalhados",
        "options": [
            {"id": "o36a", "text": "O mais simples possível — não quero acompanhar nada.", "score": 1},
            {"id": "o36b", "text": "Simples, com revisão trimestral.", "score": 2},
            {"id": "o36c", "text": "Intermediária, aceito 5-8 ativos e acompanhar mensalmente.", "score": 3},
            {"id": "o36d", "text": "Complexa, quero diversificação máxima e acompanhar o mercado.", "score": 4}
        ]
    }
]
