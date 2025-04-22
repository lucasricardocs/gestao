import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import random
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão - Clips Burger", 
    layout="centered", 
    initial_sidebar_state="expanded"
)

# --- CONSTANTES ---
CSV_FILE_RECEBIMENTOS = 'recebimentos.csv'
DADOS_SANDUICHES = """X Salada Simples R$ 18,00
X Bacon R$ 22,00
X Tudo R$ 25,00
X Frango R$ 20,00
X Egg R$ 21,00
Cebola R$ 5,00"""

DADOS_BEBIDAS = """Suco R$ 10,00
Refrigerante R$ 8,00
Água R$ 5,00
Cerveja R$ 12,00"""

# --- FUNÇÕES AUXILIARES ---
def parse_menu_string(menu_data_string):
    """Parses a multi-line string containing menu items and prices."""
    menu = {}
    lines = menu_data_string.strip().split("\n")
    for line in lines:
        parts = line.split("R$ ")
        if len(parts) == 2:
            name = parts[0].strip()
            try:
                price = float(parts[1].replace(",", "."))
                menu[name] = price
            except ValueError:
                st.warning(f"Preço inválido para '{name}'. Ignorando item.")
        elif line.strip():
            st.warning(f"Formato inválido na linha do cardápio: '{line}'. Ignorando linha.")
    return menu

def round_to_50_or_00(value):
    """Arredonda para o múltiplo de 0.50 mais próximo"""
    return round(value * 2) / 2

def generate_initial_combination(item_prices, combination_size):
    """Generates a random initial combination for the local search."""
    combination = {}
    item_names = list(item_prices.keys())
    if not item_names:
        return combination
    size = min(combination_size, len(item_names))
    chosen_names = random.sample(item_names, size)
    for name in chosen_names:
        combination[name] = round_to_50_or_00(random.uniform(1, 10))
    return combination

def calculate_combination_value(combination, item_prices):
    """Calculates the total value of a combination based on item prices."""
    return sum(item_prices.get(name, 0) * quantity for name, quantity in combination.items())

def local_search_optimization(item_prices, target_value, combination_size, max_iterations):
    """Optimiza combinações de produtos para atingir um valor alvo."""
    if not item_prices or target_value <= 0:
        return {}

    best_combination = generate_initial_combination(item_prices, combination_size)
    best_combination = {k: round_to_50_or_00(v) for k, v in best_combination.items()}
    current_value = calculate_combination_value(best_combination, item_prices)

    best_diff = abs(target_value - current_value) + (10000 if current_value > target_value else 0)
    current_items = list(best_combination.keys())

    for _ in range(max_iterations):
        if not current_items: break

        neighbor = best_combination.copy()
        item_to_modify = random.choice(current_items)

        change = random.choice([-0.50, 0.50, -1.00, 1.00])
        neighbor[item_to_modify] = round_to_50_or_00(neighbor[item_to_modify] + change)
        neighbor[item_to_modify] = max(0.50, neighbor[item_to_modify])

        neighbor_value = calculate_combination_value(neighbor, item_prices)
        neighbor_diff = abs(target_value - neighbor_value) + (10000 if neighbor_value > target_value else 0)

        if neighbor_diff < best_diff:
            best_diff = neighbor_diff
            best_combination = neighbor

    return best_combination

def format_currency(value):
    """Formats a number as Brazilian Real currency."""
    if pd.isna(value):
        return "R$ -"
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ Inválido"

def load_receipts_data():
    """Carrega os dados de recebimento do arquivo CSV."""
    if os.path.exists(CSV_FILE_RECEBIMENTOS):
        try:
            df = pd.read_csv(CSV_FILE_RECEBIMENTOS, encoding='utf-8')
            if 'Data' in df.columns:
                try:
                    df['Data'] = pd.to_datetime(df['Data'])
                except Exception as e:
                    st.warning(f"Aviso: Erro ao converter 'Data' do CSV de recebimentos: {e}")
            return df
        except Exception as e:
            st.error(f"Erro ao carregar CSV de recebimentos: {e}")
            return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])
    else:
        return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])

def save_receipts_data(df):
    """Salva os dados de recebimento no arquivo CSV."""
    try:
        if 'Data' in df.columns:
            df['Data'] = df['Data'].dt.strftime('%Y-%m-%d')
        df.to_csv(CSV_FILE_RECEBIMENTOS, index=False, encoding='utf-8')
        st.success(f"Dados de recebimento salvos em '{CSV_FILE_RECEBIMENTOS}'!")
    except Exception as e:
        st.error(f"Erro ao salvar dados de recebimento: {e}")

def plot_payment_distribution(df):
    """Gera gráfico de pizza mostrando a distribuição por forma de pagamento."""
    if not df.empty:
        df_pie = df[['Dinheiro', 'Cartao', 'Pix']].sum().reset_index()
        df_pie.columns = ['Forma de Pagamento', 'Valor']

        pie_chart = alt.Chart(df_pie).mark_arc().encode(
            theta=alt.Theta(field="Valor", type="quantitative"),
            color=alt.Color(field="Forma de Pagamento", type="nominal"),
            tooltip=["Forma de Pagamento", "Valor"]
        ).properties(
            title="Distribuição de Recebimentos por Forma de Pagamento"
        )
        st.altair_chart(pie_chart, use_container_width=True)

def plot_daily_totals(df):
    """Gera gráfico de barras com os totais diários."""
    if not df.empty:
        df['Total'] = df['Dinheiro'] + df['Cartao'] + df['Pix']
        df['Data_Formatada'] = df['Data'].dt.strftime('%d/%m/%Y')
        
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X('Data_Formatada:N', axis=alt.Axis(title='Data')),
            y=alt.Y('Total:Q', axis=alt.Axis(title='Valor (R$)')),
            tooltip=['Data_Formatada', 'Total']
        ).properties(
            title="Totais Diários de Recebimento"
        )
        st.altair_chart(chart, use_container_width=True)

def plot_payment_methods_trend(df):
    """Gera gráfico de linhas mostrando a evolução das formas de pagamento."""
    if not df.empty:
        df_melted = df.melt(
            id_vars=['Data'], 
            value_vars=['Dinheiro', 'Cartao', 'Pix'], 
            var_name='Forma', 
            value_name='Valor'
        )
        df_melted['Data_Formatada'] = df_melted['Data'].dt.strftime('%d/%m/%Y')
        
        chart = alt.Chart(df_melted).mark_line().encode(
            x=alt.X('Data_Formatada:N', axis=alt.Axis(title='Data')),
            y=alt.Y('Valor:Q', axis=alt.Axis(title='Valor (R$)')),
            color='Forma:N',
            tooltip=['Data_Formatada', 'Forma', 'Valor']
        ).properties(
            title="Evolução das Formas de Pagamento"
        ).interactive()
        st.altair_chart(chart, use_container_width=True)

# --- INTERFACE PRINCIPAL ---
# Inicialização do session_state
if 'df_receipts' not in st.session_state:
    st.session_state['df_receipts'] = load_receipts_data()

# Carrega cardápios
sanduiches_precos = parse_menu_string(DADOS_SANDUICHES)
bebidas_precos = parse_menu_string(DADOS_BEBIDAS)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações")
    
    drink_percentage = st.slider(
        "Percentual para Bebidas (%) 🍹",
        min_value=0, max_value=100, value=20, step=5
    )
    sandwich_percentage = 100 - drink_percentage
    st.caption(f"({sandwich_percentage}% será alocado para Sanduíches 🍔)")

    tamanho_combinacao_bebidas = st.slider(
        "Número de tipos de Bebidas",
        min_value=1, max_value=10, value=5, step=1
    )
    tamanho_combinacao_sanduiches = st.slider(
        "Número de tipos de Sanduíches",
        min_value=1, max_value=10, value=5, step=1
    )
    max_iterations = st.select_slider(
        "Qualidade da Otimização ✨",
        options=[1000, 5000, 10000, 20000, 50000],
        value=10000
    )
    st.info("Lembre-se: As combinações são aproximações heurísticas.")

# --- CABEÇALHO ---
col_title1, col_title2 = st.columns([0.30, 0.70])
with col_title1:
    try:
        st.image("logo.png", width=1000)
    except FileNotFoundError:
        st.warning("Logo não encontrada")
with col_title2:
    st.title("Sistema de Gestão")
    st.markdown("<p style='font-weight:bold; font-size:30px; margin-top:-15px'>Clip's Burger</p>", unsafe_allow_html=True)

st.markdown("""
Bem-vindo(a)! Esta ferramenta ajuda a visualizar suas vendas por forma de pagamento
e tenta encontrar combinações *hipotéticas* de produtos que poderiam corresponder a esses totais.
""")
st.divider()

# --- ABAS PRINCIPAIS ---
tab1, tab2, tab3 = st.tabs(["📈 Resumo das Vendas", "🧩 Detalhes das Combinações", "💰 Cadastro de Recebimentos"])

# --- TAB 1: RESUMO DAS VENDAS ---
with tab1:
    st.header("📈 Resumo das Vendas")
    arquivo = st.file_uploader("📤 Envie o arquivo de transações (.csv ou .xlsx)", type=["csv", "xlsx"])

    vendas = {}

    if arquivo:
        with st.spinner(f'Processando "{arquivo.name}"...'):
            try:
                if arquivo.name.endswith(".csv"):
                    try:
                        df = pd.read_csv(arquivo, sep=';', encoding='utf-8', dtype=str)
                    except Exception:
                        arquivo.seek(0)
                        try:
                            df = pd.read_csv(arquivo, sep=',', encoding='utf-8', dtype=str)
                        except Exception as e:
                            st.error(f"Não foi possível ler o CSV. Erro: {e}")
                            st.stop()
                else:
                    df = pd.read_excel(arquivo, dtype=str)

                st.success(f"Arquivo '{arquivo.name}' carregado com sucesso!")

                required_columns = ['Tipo', 'Bandeira', 'Valor']
                if not all(col in df.columns for col in required_columns):
                    st.error(f"Erro: O arquivo precisa conter as colunas: {', '.join(required_columns)}")
                    st.stop()

                df_processed = df.copy()
                df_processed['Tipo'] = df_processed['Tipo'].str.lower().str.strip().fillna('desconhecido')
                df_processed['Bandeira'] = df_processed['Bandeira'].str.lower().str.strip().fillna('desconhecida')
                df_processed['Valor_Numeric'] = pd.to_numeric(
                    df_processed['Valor'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                    errors='coerce'
                )
                df_processed.dropna(subset=['Valor_Numeric'], inplace=True)

                if 'Data' in df_processed.columns:
                    try:
                        df_processed['Data'] = pd.to_datetime(df_processed['Data'])
                    except:
                        st.warning("Não foi possível converter a coluna 'Data' para formato de data")

                df_processed['Categoria'] = df_processed['Tipo'] + ' ' + df_processed['Bandeira']
                categorias_desejadas = {
                    'crédito à vista elo': 'Crédito Elo',
                    'crédito à vista mastercard': 'Crédito MasterCard',
                    'crédito à vista visa': 'Crédito Visa',
                    'crédito à vista american express': 'Crédito Amex',
                    'débito elo': 'Débito Elo',
                    'débito mastercard': 'Débito MasterCard',
                    'débito visa': 'Débito Visa',
                    'pix': 'PIX'
                }
                df_processed['Forma Nomeada'] = df_processed['Categoria'].map(categorias_desejadas)
                df_filtered = df_processed.dropna(subset=['Forma Nomeada']).copy()

                if df_filtered.empty:
                    st.warning("Nenhuma transação encontrada para as formas de pagamento mapeadas.")
                    st.stop()

                vendas = df_filtered.groupby('Forma Nomeada')['Valor_Numeric'].sum().to_dict()

                # Gráfico de vendas
                st.subheader("Vendas por Forma de Pagamento")
                if vendas:
                    df_vendas = pd.DataFrame(list(vendas.items()), columns=['Forma de Pagamento', 'Valor Total'])
                    
                    chart = alt.Chart(df_vendas).mark_bar().encode(
                        x=alt.X('Forma de Pagamento:N', axis=alt.Axis(labels=False, title=None)),
                        y=alt.Y('Valor Total:Q', title=None),
                        color=alt.Color('Forma de Pagamento:N', legend=alt.Legend(
                            title="Formas de Pagamento",
                            orient='bottom',
                            titleFontSize=14,
                            labelFontSize=12
                        )),
                        tooltip=['Forma de Pagamento', 'Valor Total']
                    ).properties(
                        height=400
                    ).configure_axis(
                        grid=False
                    )
                    
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("Nenhum dado de vendas disponível")
                
                # Divisor de página no final
                st.divider()
                
                # --- Cálculo dos impostos e custos fixos ---
                st.subheader("💰 Resumo de Impostos e Custos Fixos")

                salario_minimo = st.number_input("💼 Salário Mínimo (R$)", min_value=0.0, value=1518.0, step=50.0)
                custo_contadora = st.number_input("📋 Custo com Contadora (R$)", min_value=0.0, value=316.0, step=10.0)

                total_vendas = sum(vendas.values())
                st.metric("💵 Faturamento Bruto", format_currency(total_vendas))

                aliquota_simples = 0.06
                imposto_simples = total_vendas * aliquota_simples
                st.metric("📊 Simples Nacional (6%)", format_currency(imposto_simples))
                with st.expander("📘 Como é calculado o Simples Nacional?"):
                    st.markdown(f"""
                    - Alíquota aplicada: **6%**
                    - Fórmula: `faturamento_bruto × 6%`
                    - Exemplo: `{format_currency(total_vendas)} × 0.06 = {format_currency(imposto_simples)}`
                    """)

                fgts = salario_minimo * 0.08
                ferias_mais_terco = (salario_minimo / 12) + ((salario_minimo / 12) / 3)
                decimo_terceiro = salario_minimo / 12
                custo_funcionario = salario_minimo + fgts + ferias_mais_terco + decimo_terceiro
                st.metric("👷‍♂️ Custo Mensal com Funcionário CLT", format_currency(custo_funcionario))
                with st.expander("📘 Como é calculado o custo com funcionário?"):
                    st.markdown(f"""
                    - **Salário Mínimo**: {format_currency(salario_minimo)}
                    - **FGTS (8%)**: {format_currency(fgts)}
                    - **Férias + 1/3 constitucional**: {format_currency(ferias_mais_terco)}
                    - **13º proporcional**: {format_currency(decimo_terceiro)}
                    - **Total**: {format_currency(custo_funcionario)}
                    """)

                st.metric("📋 Custo com Contadora", format_currency(custo_contadora))
                with st.expander("📘 Custo da Contadora"):
                    st.markdown(f"""
                    - Valor mensal fixo: **{format_currency(custo_contadora)}**
                    - Inclui folha, DAS, declarações, etc.
                    """)

                total_custos = imposto_simples + custo_funcionario + custo_contadora
                lucro_estimado = total_vendas - total_custos
                st.metric("💸 Total de Custos", format_currency(total_custos))
                st.metric("📈 Lucro Estimado (após custos)", format_currency(lucro_estimado))
                with st.expander("📘 Como é calculado o lucro estimado?"):
                    st.markdown(f"""
                    - Fórmula: `faturamento - (impostos + funcionário + contadora)`
                    - Cálculo:
                    ```
                    {format_currency(total_vendas)} - ({format_currency(imposto_simples)} + {format_currency(custo_funcionario)} + {format_currency(custo_contadora)})
                    = {format_currency(lucro_estimado)}
                    ```
                    """)

            except Exception as e:
                st.error(f"Erro no processamento do arquivo: {str(e)}")
    else:
        st.info("✨ Aguardando o envio do arquivo de transações para iniciar a análise...")

# --- TAB 2: DETALHES DAS COMBINAÇÕES ---
with tab2:
    st.header("🧩 Detalhes das Combinações Geradas")
    st.caption(f"Alocação: {drink_percentage}% bebidas | {sandwich_percentage}% sanduíches")

    if not vendas:
        st.warning("Nenhum dado de vendas disponível. Por favor, carregue um arquivo na aba '📈 Resumo das Vendas'.")
        st.stop()

    ordem_formas = [
        'Débito Visa', 'Débito MasterCard', 'Débito Elo',
        'Crédito Visa', 'Crédito MasterCard', 'Crédito Elo', 'PIX'
    ]
    vendas_ordenadas = {forma: vendas.get(forma, 0) for forma in ordem_formas}
    for forma, total in vendas.items():
        if forma not in vendas_ordenadas:
            vendas_ordenadas[forma] = total

    for forma, total_pagamento in vendas_ordenadas.items():
        if total_pagamento <= 0:
            continue

        with st.spinner(f"Gerando combinação para {forma}..."):
            target_bebidas = round_to_50_or_00(total_pagamento * (drink_percentage / 100.0))
            target_sanduiches = round_to_50_or_00(total_pagamento - target_bebidas)

            comb_bebidas = local_search_optimization(
                bebidas_precos, target_bebidas, tamanho_combinacao_bebidas, max_iterations
            )
            comb_sanduiches = local_search_optimization(
                sanduiches_precos, target_sanduiches, tamanho_combinacao_sanduiches, max_iterations
            )

            comb_bebidas_rounded = {name: round(qty) for name, qty in comb_bebidas.items() if round(qty) > 0}
            comb_sanduiches_rounded = {name: round(qty) for name, qty in comb_sanduiches.items() if round(qty) > 0}

            total_bebidas_inicial = calculate_combination_value(comb_bebidas_rounded, bebidas_precos)
            total_sanduiches_inicial = calculate_combination_value(comb_sanduiches_rounded, sanduiches_precos)
            total_geral_inicial = total_bebidas_inicial + total_sanduiches_inicial

            comb_sanduiches_final, total_sanduiches_final = comb_sanduiches_rounded.copy(), total_sanduiches_inicial

            if total_geral_inicial < total_pagamento and "Cebola" in sanduiches_precos:
                diferenca = total_pagamento - total_geral_inicial
                preco_cebola = sanduiches_precos["Cebola"]
                cebolas_adicionar = min(int(round(diferenca / preco_cebola)), 20)
                if cebolas_adicionar > 0:
                    comb_sanduiches_final["Cebola"] = comb_sanduiches_final.get("Cebola", 0) + cebolas_adicionar
                    total_sanduiches_final = calculate_combination_value(comb_sanduiches_final, sanduiches_precos)

            total_bebidas_final = calculate_combination_value(comb_bebidas_rounded, bebidas_precos)
            total_geral_final = total_bebidas_final + total_sanduiches_final

            with st.expander(f"**{forma}** (Total: {format_currency(total_pagamento)})", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader(f"🍹 Bebidas: {format_currency(target_bebidas)}")
                    if comb_bebidas_rounded:
                        for nome, qtt in comb_bebidas_rounded.items():
                            val_item = bebidas_precos[nome] * qtt
                            st.markdown(f"- **{qtt}** **{nome}:** {format_currency(val_item)}")
                        st.divider()
                        st.metric("Total Calculado", format_currency(total_bebidas_final))
                    else:
                        st.info("Nenhuma bebida na combinação")

                with col2:
                    st.subheader(f"🍔 Sanduíches: {format_currency(target_sanduiches)}")
                    if comb_sanduiches_final:
                        original_sandwich_value = calculate_combination_value(comb_sanduiches_rounded, sanduiches_precos)
                        has_onion_adjustment = "Cebola" in comb_sanduiches_final and comb_sanduiches_final.get("Cebola", 0) > comb_sanduiches_rounded.get("Cebola", 0)

                        for nome, qtt in comb_sanduiches_final.items():
                            display_name = nome
                            prefix = ""

                            if nome == "Cebola" and has_onion_adjustment:
                                display_name = "Cebola (Ajuste)"
                                prefix = "🔹 "

                            val_item = sanduiches_precos[nome] * qtt
                            st.markdown(f"- {prefix}**{qtt}** **{display_name}:** {format_currency(val_item)}")

                        st.divider()
                        st.metric("Total Calculado", format_currency(total_sanduiches_final))
                    else:
                        st.info("Nenhum sanduíche na combinação")

                st.divider()
                diff = total_geral_final - total_pagamento
                st.metric(
                    "💰 TOTAL GERAL (Calculado)",
                    format_currency(total_geral_final),
                    delta=f"{format_currency(diff)} vs Meta",
                    delta_color="normal" if diff <= 0 else "inverse"
                )

# --- TAB 3: CADASTRO DE RECEBIMENTOS ---
with st.tab("💰 Cadastro de Recebimentos Diários"):
    st.subheader("💰 Cadastro de Recebimentos Diários")

    # Formulário para adicionar recebimentos
    with st.form("daily_receipt_form"):
        data_hoje = st.date_input("Data do Recebimento", datetime.now().date())
        col1, col2, col3 = st.columns(3)
        dinheiro = col1.number_input("Dinheiro (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
        cartao = col2.number_input("Cartão (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
        pix = col3.number_input("Pix (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
        submitted = st.form_submit_button("Adicionar Recebimento")

        if submitted:
            if dinheiro == 0.0 and cartao == 0.0 and pix == 0.0:
                st.warning("Por favor, insira ao menos um valor de pagamento.")
            else:
                new_receipt = pd.DataFrame([{'Data': pd.to_datetime(data_hoje), 'Dinheiro': dinheiro, 'Cartao': cartao, 'Pix': pix}])
                st.session_state['df_receipts'] = pd.concat([st.session_state['df_receipts'], new_receipt], ignore_index=True)
                save_receipts_data(st.session_state['df_receipts'])
                st.success(f"Recebimento de {data_hoje.strftime('%d/%m/%Y')} adicionado e salvo!")
                st.experimental_rerun()

    st.subheader("Visualização dos Recebimentos")

    if not st.session_state['df_receipts'].empty:
        df_receipts = st.session_state['df_receipts'].copy()

        # Garantir que a coluna 'Data' está no formato datetime
        if not pd.api.types.is_datetime64_any_dtype(df_receipts['Data']):
            try:
                df_receipts['Data'] = pd.to_datetime(df_receipts['Data'], errors='coerce')
            except Exception as e:
                st.error(f"Erro ao converter a coluna 'Data': {e}")
                st.stop()

        # Adicionar colunas auxiliares
        df_receipts['Total'] = df_receipts['Dinheiro'] + df_receipts['Cartao'] + df_receipts['Pix']
        df_receipts['Ano'] = df_receipts['Data'].dt.year
        df_receipts['Mes'] = df_receipts['Data'].dt.month
        df_receipts['Dia'] = df_receipts['Data'].dt.day

        # --- Filtros de data ---
        st.subheader("📊 Vendas por Período")
        col_inicio, col_fim = st.columns(2)
        data_inicial = col_inicio.date_input("Data Inicial", value=df_receipts['Data'].min().date())
        data_final = col_fim.date_input("Data Final", value=df_receipts['Data'].max().date())

        df_periodo = df_receipts[
            (df_receipts['Data'].dt.date >= data_inicial) & 
            (df_receipts['Data'].dt.date <= data_final)
        ].copy()

        if not df_periodo.empty:
            # --- Gráficos ---
            st.subheader("📈 Gráficos de Recebimentos")

            # Gráfico de distribuição por forma de pagamento
            st.bar_chart(df_periodo[['Dinheiro', 'Cartao', 'Pix']].sum())

            # Gráfico de totais diários
            df_totais_diarios = df_periodo.groupby('Data').sum(numeric_only=True)[['Total']]
            st.line_chart(df_totais_diarios)

            # Gráfico de evolução das formas de pagamento
            df_pagamentos_trend = df_periodo.groupby('Data').sum(numeric_only=True)[['Dinheiro', 'Cartao', 'Pix']]
            st.line_chart(df_pagamentos_trend)

            # --- Tabela com dados ---
            st.subheader("📋 Dados Detalhados")
            df_periodo['Data_Formatada'] = df_periodo['Data'].dt.strftime('%d/%m/%Y')
            st.dataframe(
                df_periodo[['Data_Formatada', 'Dinheiro', 'Cartao', 'Pix', 'Total']]
                .rename(columns={'Data_Formatada': 'Data'})
                .sort_values('Data', ascending=False)
                .reset_index(drop=True)
            )

            # --- Resumo estatístico ---
            st.subheader("📌 Resumo Estatístico")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Dias", len(df_periodo))
            col2.metric("Média Diária", format_currency(df_periodo['Total'].mean()))
            col3.metric("Total no Período", format_currency(df_periodo['Total'].sum()))
        else:
            st.warning("Nenhum dado encontrado para o período selecionado.")
    else:
        st.info("Nenhum recebimento cadastrado ainda. Adicione dados usando o formulário acima.")

if __name__ == '__main__':
    pass
