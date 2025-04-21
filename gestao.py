import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import os
from itertools import product

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestão - Clips Burger", layout="centered", initial_sidebar_state="expanded")

CSV_FILE = 'recebimentos.csv'

# ----- Funções Auxiliares -----
def parse_menu_string(menu_data_string):
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
    return sum(item_prices.get(name, 0) * quantity for name, quantity in combination.items())

def format_currency(value):
    if pd.isna(value):
        return "R$ -"
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ Inválido"

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'Data' in df.columns:
                try:
                    df['Data'] = pd.to_datetime(df['Data'])
                except Exception as e:
                    st.warning(f"Aviso: Erro ao converter a coluna 'Data' do CSV: {e}")
            return df
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo CSV: {e}")
            return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])
    else:
        return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])

def save_data(df):
    try:
        df['Data'] = df['Data'].dt.strftime('%Y-%m-%d')
        df.to_csv(CSV_FILE, index=False)
        st.success(f"Dados salvos com sucesso em '{CSV_FILE}'!")
    except Exception as e:
        st.error(f"Erro ao salvar os dados no arquivo CSV: {e}")

def exhaustive_combination_search(item_prices, target_value, max_quantity):
    best_combination = {}
    best_diff = float('inf')

    items = list(item_prices.keys())
    ranges = [range(max_quantity + 1) for _ in items]

    for quantities in product(*ranges):
        combination = {item: qty for item, qty in zip(items, quantities)}
        total_value = calculate_combination_value(combination, item_prices)
        if total_value > target_value:
            continue
        diff = target_value - total_value
        if diff < best_diff:
            best_diff = diff
            best_combination = combination
            if diff == 0:
                break
    return best_combination

def format_combo(combo):
    return ", ".join([f"{v}x {k}" for k, v in combo.items() if v > 0]) or "Nenhum item encontrado"

# -------------------------------
def main():
    df_receipts = load_data()

    # Colunas para Título e Logo
    col_title1, col_title2 = st.columns([0.30, 0.70])
    with col_title1:
        st.image("logo.png", width=1000)
    with col_title2:
        st.title("Sistema de Gestão")
        st.markdown("**Clip's Burger**") 

    st.markdown("""
    Bem-vindo(a)! Esta ferramenta ajuda a visualizar suas vendas por forma de pagamento
    e tenta encontrar combinações *hipotéticas* de produtos que poderiam corresponder a esses totais.
    """)
    st.divider()

    with st.sidebar:
        st.header("⚙️ Configurações")
        drink_percentage = st.slider("Percentual para Bebidas (%) 🍹", min_value=0, max_value=100, value=20, step=5)
        sandwich_percentage = 100 - drink_percentage
        st.caption(f"({sandwich_percentage}% será alocado para Sanduíches 🍔)")

        max_quantity_sanduiches = st.slider("Quantidade máxima por Sanduíche", 1, 20, 10)
        max_quantity_bebidas = st.slider("Quantidade máxima por Bebida", 1, 20, 10)
        st.info("As combinações são calculadas exaustivamente com limites separados para sanduíches e bebidas.")

    tab1, tab2, tab3 = st.tabs(["📈 Resumo das Vendas", "🧩 Detalhes das Combinações", "💰 Cadastro de Recebimentos"])

    with tab1:
        st.header("📈 Resumo das Vendas")
        arquivo = st.file_uploader("📤 Envie o arquivo de transações (.csv ou .xlsx)", type=["csv", "xlsx"])

        vendas = {}
        if arquivo:
            with st.spinner(f'Processando "{arquivo.name}"...'):
                try:
                    if arquivo.name.endswith(".csv"):
                        df = pd.read_csv(arquivo, sep=';', encoding='utf-8', dtype=str)
                    else:
                        df = pd.read_excel(arquivo, dtype=str)

                    st.success(f"Arquivo '{arquivo.name}' carregado com sucesso!")
                    required_columns = ['Tipo', 'Bandeira', 'Valor']
                    if not all(col in df.columns for col in required_columns):
                        st.error(f"Erro: O arquivo precisa conter as colunas: {', '.join(required_columns)}")
                        st.stop()

                    df['Valor_Numeric'] = pd.to_numeric(
                        df['Valor'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                        errors='coerce'
                    )
                    vendas = df.groupby('Tipo')['Valor_Numeric'].sum().to_dict()

                    st.markdown("### 💳 Total por Tipo de Pagamento")
                    for tipo, valor in vendas.items():
                        st.markdown(f"- **{tipo}**: {format_currency(valor)}")
                except Exception as e:
                    st.error(f"Erro no processamento do arquivo: {str(e)}")
        else:
            st.info("Nenhum arquivo enviado ainda.")

    with tab2:
        st.header("🧩 Detalhes das Combinações Geradas")
        if vendas:
            dados_sanduiches = """
                X Salada Simples R$ 18,00
                X Salada Especial R$ 20,00
                X Bacon Simples R$ 22,00
                X Bacon Especial R$ 24,00
                X Bacon Duplo R$ 28,00
                X Frango Simples R$ 22,00
                X Frango Especial R$ 24,00
                Cebola R$ 0.50
            """
            dados_bebidas = """
                Suco R$ 10,00
                Creme R$ 15,00
                Refri Lata R$ 7,00
                Refri 600ml R$ 8,00
                Refri 2L R$ 15,00
                Água R$ 3,00
                Água com Gás R$ 4,00
            """
            sanduiches_precos = parse_menu_string(dados_sanduiches)
            bebidas_precos = parse_menu_string(dados_bebidas)

            for forma, total_pagamento in vendas.items():
                st.subheader(f"💳 Forma de Pagamento: {forma}")
                st.markdown(f"**Total recebido:** {format_currency(total_pagamento)}")

                target_bebidas = round(total_pagamento * (drink_percentage / 100.0), 2)
                target_sanduiches = round(total_pagamento - target_bebidas, 2)

                st.markdown(f"- **Alvo para Bebidas:** {format_currency(target_bebidas)}")
                st.markdown(f"- **Alvo para Sanduíches:** {format_currency(target_sanduiches)}")

                comb_bebidas = exhaustive_combination_search(bebidas_precos, target_bebidas, max_quantity_bebidas)
                comb_sanduiches = exhaustive_combination_search(sanduiches_precos, target_sanduiches, max_quantity_sanduiches)

                st.markdown("🍹 **Combinação sugerida de Bebidas:**")
                st.success(format_combo(comb_bebidas))

                st.markdown("🍔 **Combinação sugerida de Sanduíches:**")
                st.success(format_combo(comb_sanduiches))
        else:
            st.info("Nenhuma venda processada na aba anterior.")

    with tab3:
        st.header("💰 Cadastro de Recebimentos")
        st.caption("Cadastre e visualize os recebimentos diários de forma prática.")

        with st.form("daily_receipt_form"):
            data_hoje = st.date_input("Data do Recebimento", datetime.now().date())
            dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, step=0.50, format="%.2f")
            cartao = st.number_input("Cartão (R$)", min_value=0.0, step=0.50, format="%.2f")
            pix = st.number_input("Pix (R$)", min_value=0.0, step=0.50, format="%.2f")
            submitted = st.form_submit_button("Adicionar Recebimento")

            if submitted:
                new_receipt = pd.DataFrame([{'Data': data_hoje, 'Dinheiro': dinheiro, 'Cartao': cartao, 'Pix': pix}])
                df_receipts = pd.concat([df_receipts, new_receipt], ignore_index=True)
                save_data(df_receipts)
                st.balloons()
                st.success(f"🎉 Recebimento de {data_hoje.strftime('%d/%m/%Y')} adicionado com sucesso!")
                st.experimental_rerun()

        if not df_receipts.empty:
            st.subheader("📋 Recebimentos Cadastrados")
            df_receipts['Total'] = df_receipts['Dinheiro'] + df_receipts['Cartao'] + df_receipts['Pix']
            st.dataframe(df_receipts)

            st.subheader("📊 Totais Acumulados")
            total_geral = df_receipts[['Dinheiro', 'Cartao', 'Pix', 'Total']].sum()
            st.markdown(f"- Dinheiro: **{format_currency(total_geral['Dinheiro'])}**")
            st.markdown(f"- Cartão: **{format_currency(total_geral['Cartao'])}**")
            st.markdown(f"- Pix: **{format_currency(total_geral['Pix'])}**")
            st.markdown(f"➡️ **Total Geral: {format_currency(total_geral['Total'])}**")

            st.subheader("📊 Gráfico de Recebimentos por Forma de Pagamento")
            df_melted = df_receipts.melt(id_vars=["Data"], value_vars=["Dinheiro", "Cartao", "Pix"], var_name="Forma", value_name="Valor")
            chart = alt.Chart(df_melted).mark_bar().encode(
                x="Data:T",
                y="Valor:Q",
                color="Forma:N",
                tooltip=["Data:T", "Forma:N", "Valor:Q"]
            ).properties(title="Recebimentos por Forma de Pagamento")
            st.altair_chart(chart, use_container_width=True)

if __name__ == "__main__":
    main()
