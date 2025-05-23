import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import random
import os

# --- CONFIGURAÇÃO DA PÁGINA (DEVE SER A PRIMEIRA CHAMADA STREAMLIT) ---
st.set_page_config(page_title="Sistema de Gestao - Clips Burger", layout="centered", initial_sidebar_state="expanded")

# Nome do arquivo CSV para armazenar os dados de recebimento
CSV_FILE_RECEBIMENTOS = 'recebimentos.csv'

# ----- Funções Auxiliares -----
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

def calculate_combination_value(combination, item_prices):
    """Calculates the total value of a combination based on item prices."""
    return sum(item_prices.get(name, 0) * quantity for name, quantity in combination.items())

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

def local_search_optimization(item_prices, target_value, combination_size, max_iterations):
    """
    Versão modificada para:
    - Valores terminarem em ,00 ou ,50
    - Nunca ultrapassar o target_value
    """
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

# Função para carregar os dados de recebimento do CSV
def load_receipts_data():
    if os.path.exists(CSV_FILE_RECEBIMENTOS):
        try:
            df = pd.read_csv(CSV_FILE_RECEBIMENTOS)
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

# Função para salvar os dados de recebimento no CSV
def save_receipts_data(df):
    try:
        df['Data'] = df['Data'].dt.strftime('%Y-%m-%d')
        df.to_csv(CSV_FILE_RECEBIMENTOS, index=False)
        st.success(f"Dados de recebimento salvos em '{CSV_FILE_RECEBIMENTOS}'!")
    except Exception as e:
        st.error(f"Erro ao salvar dados de recebimento: {e}")

# Inicialização do estado da sessão (garantindo que 'df_receipts' sempre exista)
if 'df_receipts' not in st.session_state:
    st.session_state['df_receipts'] = load_receipts_data()
    st.info("✅ 'df_receipts' foi inicializado (carregando do arquivo).")
else:
    st.info("✅ 'df_receipts' já existia na sessão.")

# ----- Funções para visualização -----
def plot_daily_receipts(df, date_column, value_column, title):
    if not df.empty:
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X(date_column, axis=alt.Axis(title='Data')),
            y=alt.Y(value_column, axis=alt.Axis(title='Valor (R$)')),
            tooltip=[date_column, value_column]
        ).properties(
            title=title
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir no gráfico.")

def display_receipts_table(df):
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum dado de recebimento cadastrado.")

# ----- Interface Streamlit -----

# Colunas para Título e Logo
col_title1, col_title2 = st.columns([0.30, 0.70])
with col_title1:
    st.image("logo.png", width=100)  # Ajustei a largura para melhor visualização
with col_title2:
    st.title("Sistema de Gestão")
    st.markdown("**Clip's Burger**")

st.markdown("""
Bem-vindo(a)! Esta ferramenta ajuda a visualizar suas vendas por forma de pagamento
e tenta encontrar combinações *hipotéticas* de produtos que poderiam corresponder a esses totais.

**Como usar:**
1. Ajuste as configurações na barra lateral (para análise do arquivo)
2. Faça o upload do seu arquivo de transações (.csv ou .xlsx) na aba "📈 Resumo das Vendas"
3. Cadastre os valores recebidos diariamente na aba "💰 Cadastro de Recebimentos"
4. Explore os resultados nas abas abaixo
""")
st.divider()

# --- Configuration Sidebar ---
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

# --- Abas ---
tab1, tab2, tab3 = st.tabs(["📈 Resumo das Vendas", "🧩 Detalhes das Combinações", "💰 Cadastro de Recebimentos"])

# --- Tab 1: Resumo das Vendas ---
with tab1:
    st.header("📈 Resumo das Vendas")
    arquivo = st.file_uploader("📤 Envie o arquivo de transações (.csv ou .xlsx)", type=["csv", "xlsx"])

    # Inicialize 'vendas' com um dicionário vazio
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
                    try:
                        df = pd.read_excel(arquivo, dtype=str)
                    except ImportError:
                        st.error("Para ler arquivos XLSX, a biblioteca 'openpyxl' é necessária. Por favor, instale-a com: `pip install openpyxl`")
                        st.stop()

                st.success(f"Arquivo '{arquivo.name}' carregado com sucesso!")

                # Processamento dos dados
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

                # Adicionando coluna de data se existir no arquivo
                if 'Data' in df_processed.columns:
                    try:
                        df_processed['Data'] = pd.to_datetime(df_processed['Data'])
                    except Exception:
                        st.warning("Não foi possível converter a coluna 'Data' para formato de data")

                df_processed['Categoria'] = df_processed['Tipo'] + ' ' + df_processed['Bandeira']
                categorias_desejadas = {
                    'crédito à vista elo': 'Crédito Elo',
                    'crédito à vista mastercard': 'Crédito MasterCard',
                    'crédito à vista visa': 'Crédito Visa',
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

                # Definição dos Cardápios
                dados_sanduiches = """
                    X Salada Simples R$ 18,00
                    X Salada Especial R$ 20,00
                    X Especial Duplo R$ 24,00
                    X Bacon Simples R$ 22,00
                    X Bacon Especial R$ 24,00
                    X Bacon Duplo R$ 28,00
                    X Hamburgão R$ 35,00
                    X Mata-Fome R$ 39,00
                    X Frango Simples R$ 22,00
                    X Frango Especial R$ 24,00
                    X Frango Bacon R$ 27,00
                    X Frango Tudo R$ 30,00
                    X Lombo Simples R$ 23,00
                    X Lombo Especial R$ 25,00
                    X Lombo Bacon R$ 28,00
                    X Lombo Tudo R$ 31,00
                    X Filé Simples R$ 28,00
                    X Filé Especial R$ 30,00
                    X Filé Bacon R$ 33,00
                    X Filé Tudo R$ 36,00
                    Cebola R$ 0.50
                    """
                dados_bebidas = """
                    Suco R$ 10,00
                    Creme R$ 15,00
                    Refri caçula R$ 3.50
                    Refri Lata R$ 7,00
                    Refri 600 R$ 8,00
                    Refri 1L R$ 10,00
                    Refri 2L R$ 15,00
                    Água R$ 3,00
                    Água com Gas R$ 4,00
                    """
                sanduiches_precos = parse_menu_string(dados_sanduiches)
                bebidas_precos = parse_menu_string(dados_bebidas)

                if not sanduiches_precos or not bebidas_precos:
                    st.error("Erro ao carregar cardápios. Verifique os dados no código.")
                    st.stop()

                # Gráfico de vendas por forma de pagamento
                st.subheader("Vendas por Forma de Pagamento")
                if vendas:
                    df_vendas = pd.DataFrame(list(vendas.items()), columns=['Forma de Pagamento', 'Valor Total'])
                    df_vendas['Valor Formatado'] = df_vendas['Valor Total'].apply(format_currency)
                    st.bar_chart(df_vendas.set_index('Forma de Pagamento')['Valor Total'])
                    st.dataframe(df_vendas[['Forma de Pagamento', 'Valor Formatado']], use_container_width=True)

                # ---- Cálculo dos impostos e custos fixos ----
                st.subheader("💰 Resumo de Impostos e Custos Fixos")
                total_vendas = sum(vendas.values())
                st.metric("💵 Faturamento Bruto", format_currency(total_vendas))
                st.caption("Este é o valor total das suas vendas.")

                aliquota_simples = 0.06
                imposto_simples = total_vendas * aliquota_simples
                st.metric(f"📊 Simples Nacional ({aliquota_simples*100:.0f}%)", format_currency(imposto_simples))
                st.caption(f"Calculado como {format_currency(total_vendas)} (Faturamento Bruto) x {aliquota_simples*100:.0f}%.")

                salario_minimo = 1412.00
                fgts = salario_minimo * 0.08
                ferias_mais_terco = salario_minimo / 12 + (salario_minimo / 12) /3
                decimo_terceiro = salario_minimo / 12

                custo_funcionario = salario_minimo + fgts + ferias_mais_terco + decimo_terceiro
                st.metric("👷‍♂️ Custo Mensal com Funcionário CLT (Estimado)", format_currency(custo_funcionario))
                st.caption(f"Inclui Salário Mínimo ({format_currency(salario_minimo)}), FGTS ({format_currency(fgts)}), 1/12 de Férias + 1/3 ({format_currency(ferias_mais_terco):.2f}) e 1/12 de 13º ({format_currency(decimo_terceiro):.2f}).")

                custo_contadora = 316.00
                st.metric("👩‍💼 Custo Mensal com Contadora", format_currency(custo_contadora))
                st.caption(f"Valor fixo mensal de {format_currency(custo_contadora)}.")

                total_custos = imposto_simples + custo_funcionario + custo_contadora
                st.metric("💸 Total de Custos (Estimado)", format_currency(total_custos))
                st.caption(f"Soma de Simples Nacional, Custo com Funcionário e Custo com Contadora.")
                lucro_estimado = total_vendas - total_custos

                st.metric("📈 Lucro Estimado (após custos)", format_currency(lucro_estimado))
                st.caption(f"Calculado como {format_currency(total_vendas)} (Faturamento Bruto) - {format_currency(total_custos)} (Total de Custos).")

            except Exception as e:
                st.error(f"Erro no processamento do arquivo: {str(e)}")
    else:
        st.info("✨ Aguardando o envio do arquivo de transações para iniciar a análise...")

# --- Tab 2: Detalhes das Combinações ---
with tab2:
    st.header("🧩 Detalhes das Combinações Geradas")
    st.caption(f"Alocação: {drink_percentage}% bebidas | {sandwich_percentage}% sanduíches")

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

with tab3:
    st.subheader("💰 Cadastro de Recebimentos Diários")

    with st.form("daily_receipt_form"):
        data_hoje = st.date_input("Data do Recebimento", datetime.now().date())
        col1, col2, col3 = st.columns(3)
        dinheiro = col1.number_input("Dinheiro (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
        cartao = col2.number_input("Cartão (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
        pix = col3.number_input("Pix (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
        submitted = st.form_submit_button("Adicionar Recebimento")

        if submitted:
            new_receipt = pd.DataFrame([{'Data': pd.to_datetime(data_hoje), 'Dinheiro': dinheiro, 'Cartao': cartao, 'Pix': pix}])
            st.session_state['df_receipts'] = pd.concat([st.session_state['df_receipts'], new_receipt], ignore_index=True)
            save_receipts_data(st.session_state['df_receipts'])
            st.success(f"Recebimento de {data_hoje.strftime('%d/%m/%Y')} adicionado e salvo!")
            st.rerun()

    st.subheader("Visualização dos Recebimentos")

    print(f"Verificando 'df_receipts' antes da condição: {'df_receipts' in st.session_state}")
    if not st.session_state['df_receipts'].empty:
        df_receipts = st.session_state['df_receipts'].copy()
        if not pd.api.types.is_datetime64_any_dtype(df_receipts['Data']):
            try:
                df_receipts['Data'] = pd.to_datetime(df_receipts['Data'])
            except Exception as e:
                st.error(f"Erro ao converter a coluna 'Data': {e}")
                st.stop()

        df_receipts['Total'] = df_receipts['Dinheiro'] + df_receipts['Cartao'] + df_receipts['Pix']
        df_receipts['Ano'] = df_receipts['Data'].dt.year
        df_receipts['Mes'] = df_receipts['Data'].dt.month
        df_receipts['Dia'] = df_receipts['Data'].dt.day

        # --- Nova seção para seleção de período ---
        st.subheader("📊 Vendas por Período")
        col_inicio, col_fim = st.columns(2)
        data_inicial = col_inicio.date_input("Data Inicial", df_receipts['Data'].min().date())
        data_final = col_fim.date_input("Data Final", df_receipts['Data'].max().date())

        df_periodo = df_receipts[(df_receipts['Data'].dt.date >= data_inicial) & (df_receipts['Data'].dt.date <= data_final)].copy()

        if not df_periodo.empty:
            df_periodo_agrupado = df_periodo.groupby(df_periodo['Data'].dt.date)['Total'].sum().reset_index()
            df_periodo_agrupado.columns = ['Data', 'Total']

            chart_periodo = alt.Chart(df_periodo_agrupado).mark_line().encode(
                x=alt.X('Data:T', axis=alt.Axis(title='Data')),
                y=alt.Y('Total:Q', axis=alt.Axis(title='Total de Vendas (R$)')),
                tooltip=['Data:T', 'Total:Q']
            ).properties(
                title=f"Total de Vendas de {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}"
            ).interactive()
            st.altair_chart(chart_periodo, use_container_width=True)
        else:
            st.info("Nenhum recebimento encontrado no período selecionado.")

        st.divider()

        st.subheader("Visualização por Ano, Mês e Dia")

        anos_disponiveis = sorted(df_receipts['Ano'].unique(), reverse=True)
        ano_selecionado = st.selectbox("Selecionar Ano", anos_disponiveis, index=0)
        df_ano = df_receipts[df_receipts['Ano'] == ano_selecionado]

        meses_disponiveis = sorted(df_ano['Mes'].unique())
        nomes_meses = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
        meses_nomes_disponiveis = [f"{m} - {nomes_meses[m]}" for m in meses_disponiveis]
        mes_selecionado_index = 0
        if meses_nomes_disponiveis:
            mes_selecionado_str = st.selectbox("Selecionar Mês", meses_nomes_disponiveis, index=0)
            mes_selecionado = int(mes_selecionado_str.split(' - ')[0])
            df_mes = df_ano[df_ano['Mes'] == mes_selecionado]
        else:
            df_mes = df_ano.copy()

        dias_disponiveis = sorted(df_mes['Dia'].unique())
        dia_selecionado = st.selectbox("Selecionar Dia", ['Todos'] + list(dias_disponiveis), index=0)
        if dia_selecionado != 'Todos':
            df_dia = df_mes[df_mes['Dia'] == dia_selecionado]
        else:
            df_dia = df_mes.copy()

        # Gráfico de pizza para formas de pagamento
        st.subheader("🎨 Distribuição por Forma de Pagamento")
        df_pie = df_mes[['Dinheiro', 'Cartao', 'Pix']].sum().reset_index()
        df_pie.columns = ['Forma de Pagamento', 'Valor']

        pie_chart = alt.Chart(df_pie).mark_arc().encode(
            theta=alt.Theta(field="Valor", type="quantitative"),
            color=alt.Color(field="Forma de Pagamento", type="nominal"),
            tooltip=["Forma de Pagamento", "Valor"]
        ).properties(
            title="Distribuição de Recebimentos por Forma de Pagamento"
        )
        st.altair_chart(pie_chart, use_container_width=True)

        st.divider()

        st.subheader("Totais Diários")
        df_dia['Data_Formatada'] = df_dia['Data'].dt.strftime('%d/%m/%Y')
        plot_diario = alt.Chart(df_dia).mark_bar().encode(
            x=alt.X('Data_Formatada:N', axis=alt.Axis(title='Data')),
            y=alt.Y('Total:Q', axis=alt.Axis(title='Valor (R$)')),
            tooltip=['Data_Formatada', 'Total']
        ).properties(
            title=f"Total Recebido em {dia_selecionado if dia_selecionado != 'Todos' else 'Todos os Dias'} de {nomes_meses.get(mes_selecionado, '') if meses_nomes_disponiveis else 'Todos os Meses'} de {ano_selecionado}"
        ).interactive()
        st.altair_chart(plot_diario, use_container_width=True)

        st.subheader("Gráfico de Formas de Pagamento")
        df_melted = df_dia.melt(id_vars=['Data'], value_vars=['Dinheiro', 'Cartao', 'Pix'], var_name='Forma', value_name='Valor')
        df_melted['Data_Formatada'] = df_melted['Data'].dt.strftime('%d/%m/%Y')
        chart_pagamentos = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('Data_Formatada:N', axis=alt.Axis(title='Data')),
            y=alt.Y('Valor:Q', axis=alt.Axis(title='Valor (R$)')),
            color='Forma:N',
            tooltip=['Data_Formatada', 'Forma', 'Valor']
        ).properties(
            title=f"Recebimentos por Forma de Pagamento em {dia_selecionado if dia_selecionado != 'Todos' else 'Todos os Dias'} de {nomes_meses.get(mes_selecionado, '') if meses_nomes_disponiveis else 'Todos os Meses'} de {ano_selecionado}"
        ).interactive() # Tornar o gráfico interativo
        st.altair_chart(chart_pagamentos, use_container_width=True)

        st.subheader("Detalhes dos Recebimentos")
        df_dia['Data_Formatada'] = df_dia['Data'].dt.strftime('%d/%m/%Y')
        display_receipts_table(df_dia[['Data_Formatada', 'Dinheiro', 'Cartao', 'Pix', 'Total']].rename(
            columns={'Data_Formatada': 'Data', 'Dinheiro': 'Dinheiro (R$)', 'Cartao': 'Cartão (R$)', 'Pix': 'Pix (R$)', 'Total': 'Total (R$)'}
        ))
    else:
        st.info("Nenhum dado de recebimento cadastrado.")

if __name__ == '__main__':
    pass
