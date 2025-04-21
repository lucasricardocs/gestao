import streamlit as st
import pandas as pd
import altair as alt
import itertools
from datetime import datetime
import random
import os

# --- CONFIGURAÇÃO DA PÁGINA (DEVE SER A PRIMEIRA CHAMADA STREAMLIT) ---
st.set_page_config(page_title="Sistema de Gestao - Clips Burger", layout="centered", initial_sidebar_state="expanded")

# Nome do arquivo CSV para armazenar os dados
CSV_FILE = 'recebimentos.csv'

# ----- Funções Auxiliares ----
def exhaustive_combination_search(item_prices, target_value, max_quantity=10):
    """
    Gera combinações exaustivas de quantidades para cada item (0.5 a max_quantity)
    e retorna a melhor combinação que não ultrapasse o target_value.
    """
    step = 0.5
    item_names = list(item_prices.keys())
    quantity_range = [round_to_50_or_00(i * step) for i in range(int(max_quantity / step) + 1)]

    best_combination = None
    best_value = 0

    # Gera todas as combinações possíveis de quantidades
    for quantities in itertools.product(quantity_range, repeat=len(item_names)):
        combination = dict(zip(item_names, quantities))
        total = calculate_combination_value(combination, item_prices)

        if total <= target_value and total > best_value:
            best_combination = combination
            best_value = total

    # Ajusta com cebolas, se quiser
    if best_combination:
        best_combination, best_value = adjust_with_onions(best_combination, item_prices, target_value)

    return best_combination
def format_currency(value):
    """Formats a number as Brazilian Real currency."""
    if pd.isna(value):
        return "R$ -"
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ Inválido"

# Função para carregar os dados do CSV (se existir) ou inicializar um DataFrame vazio
def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            # Converter a coluna 'Data' para datetime se não estiver no formato correto
            if 'Data' in df.columns:
                try:
                    df['Data'] = pd.to_datetime(df['Data'])
                except Exception as e:
                    st.warning(f"Aviso: Erro ao converter a coluna 'Data' do CSV: {e}. Certifique-se de que as datas estejam em um formato reconhecível.")
            return df
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo CSV: {e}")
            return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])
    else:
        return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])

# Função para salvar os dados no CSV
def save_data(df):
    try:
        # Converter a coluna 'Data' para string no formato adequado para salvar no CSV
        df['Data'] = df['Data'].dt.strftime('%Y-%m-%d')
        df.to_csv(CSV_FILE, index=False)
        st.success(f"Dados salvos com sucesso em '{CSV_FILE}'!")
    except Exception as e:
        st.error(f"Erro ao salvar os dados no arquivo CSV: {e}")

# Carregar os dados
df_receipts = load_data()

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
    st.image("logo.png", width=1000)  # Usa a imagem local logo.png
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
                    df = pd.read_excel(arquivo, dtype=str)

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
                    except:
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
                if vendas:  # Verificação correta para dicionário vazio
                    df_vendas = pd.DataFrame(list(vendas.items()), columns=['Forma de Pagamento', 'Valor Total'])
                    df_vendas['Valor Formatado'] = df_vendas['Valor Total'].apply(format_currency)
                    st.bar_chart(df_vendas.set_index('Forma de Pagamento')['Valor Total'])
                    st.dataframe(df_vendas[['Forma de Pagamento', 'Valor Formatado']], use_container_width=True)
                else:
                    st.warning("Nenhum dado de venda para exibir.")

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

# --- Tab 3: Cadastro de Recebimentos ---
with tab3:
    #st.header("💰 Cadastro de Recebimentos Diários")

    #col_cadastro, col_visualizacao = st.columns(2)

    #with col_cadastro:
        st.subheader("💰 Cadastro de Recebimentos Diários")

        with st.form("daily_receipt_form"):
            data_hoje = st.date_input("Data do Recebimento", datetime.now().date())
            dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
            cartao = st.number_input("Cartão (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
            pix = st.number_input("Pix (R$)", min_value=0.0, step=0.50, format="%.2f", label_visibility="visible")
            submitted = st.form_submit_button("Adicionar Recebimento")

            if submitted:
                new_receipt = pd.DataFrame([{'Data': pd.to_datetime(data_hoje), 'Dinheiro': dinheiro, 'Cartao': cartao, 'Pix': pix}])
                df_receipts = pd.concat([df_receipts, new_receipt], ignore_index=True)
                save_data(df_receipts)
                st.success(f"Recebimento de {data_hoje.strftime('%d/%m/%Y')} adicionado e salvo!")
                st.rerun()

    #with col_visualizacao:
        st.subheader("Visualização dos Recebimentos")
        
        if not df_receipts.empty:
            # Converter a coluna 'Data' para datetime se não estiver
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
            display_receipts_table(df_dia[['Data_Formatada', 'Dinheiro', 'Cartao', 'Pix', 'Total']].rename(columns={'Data_Formatada': 'Data'}))


        else:
            st.info("Nenhum recebimento cadastrado ainda.")

if __name__ == '__main__':
    pass
