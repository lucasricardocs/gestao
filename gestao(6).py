import streamlit as st
import sqlite3
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Gestão de Recebimentos", layout="centered")

# Conexão com o banco de dados
conn = sqlite3.connect('recebimentos.db')

# Carrega os dados
df = pd.read_sql("SELECT * FROM recebimentos", conn)
df['data'] = pd.to_datetime(df['data'])

# Interface
st.title("📊 Dashboard de Recebimentos")

# Gráfico de linhas
st.line_chart(df.set_index('data'))

# Tabela com dados
st.dataframe(df)

conn.close()
