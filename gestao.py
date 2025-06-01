import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Simulador Par ou Ímpar",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-metric {
        border-left-color: #28a745;
    }
    .warning-metric {
        border-left-color: #ffc107;
    }
    .danger-metric {
        border-left-color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

class SimuladorParOuImpar:
    """Classe para simulação do jogo Par ou Ímpar."""
    
    def __init__(self, min_numero=0, max_numero=20):
        self.min_numero = min_numero
        self.max_numero = max_numero
        self.range_numeros = max_numero - min_numero + 1
        self.prob_teorica_par, self.prob_teorica_impar = self._calcular_probabilidades_teoricas()
    
    def _calcular_probabilidades_teoricas(self):
        """Calcula probabilidades teóricas exatas."""
        total_combinacoes = self.range_numeros ** 2
        combinacoes_par = sum(
            1 for i in range(self.min_numero, self.max_numero + 1)
            for j in range(self.min_numero, self.max_numero + 1)
            if (i + j) % 2 == 0
        )
        prob_par = combinacoes_par / total_combinacoes
        return prob_par, 1 - prob_par
    
    def simular(self, n_simulacoes, seed=None):
        """Executa simulação Monte Carlo."""
        if seed:
            np.random.seed(seed)
        
        inicio = time.time()
        
        # Geração vetorizada
        numeros_j1 = np.random.randint(self.min_numero, self.max_numero + 1, n_simulacoes)
        numeros_j2 = np.random.randint(self.min_numero, self.max_numero + 1, n_simulacoes)
        somas = numeros_j1 + numeros_j2
        
        vitorias_par = np.sum(somas % 2 == 0)
        vitorias_impar = n_simulacoes - vitorias_par
        
        tempo_execucao = time.time() - inicio
        
        return {
            'vitorias_par': vitorias_par,
            'vitorias_impar': vitorias_impar,
            'prob_par_obs': vitorias_par / n_simulacoes,
            'prob_impar_obs': vitorias_impar / n_simulacoes,
            'tempo_execucao': tempo_execucao,
            'somas': somas,
            'numeros_j1': numeros_j1,
            'numeros_j2': numeros_j2
        }
    
    def calcular_intervalo_confianca(self, sucessos, n_tentativas, confianca=0.95):
        """Calcula intervalo de confiança usando método de Wilson."""
        z = stats.norm.ppf((1 + confianca) / 2)
        p = sucessos / n_tentativas
        n = n_tentativas
        
        denominador = 1 + z**2 / n
        centro = (p + z**2 / (2*n)) / denominador
        margem = z * np.sqrt((p*(1-p) + z**2/(4*n)) / n) / denominador
        
        return (centro - margem, centro + margem)

def main():
    # Título principal
    st.markdown('<h1 class="main-header">🎲 Simulador Par ou Ímpar (0-20)</h1>', unsafe_allow_html=True)
    st.markdown("### Análise estatística completa com simulação Monte Carlo")
    
    # Sidebar - Configurações
    st.sidebar.header("⚙️ Configurações")
    
    # Parâmetros do jogo
    min_numero = st.sidebar.slider("Número mínimo", 0, 19, 0)
    max_numero = st.sidebar.slider("Número máximo", min_numero + 1, 20, 20)
    
    # Parâmetros da simulação
    n_simulacoes = st.sidebar.selectbox(
        "Número de simulações",
        [1000, 5000, 10000, 50000, 100000, 500000, 1000000],
        index=2
    )
    
    seed = st.sidebar.number_input("Seed (para reprodutibilidade)", min_value=0, value=42)
    confianca = st.sidebar.slider("Nível de confiança", 0.90, 0.99, 0.95, 0.01)
    
    # Botão de simulação
    if st.sidebar.button("🚀 Executar Simulação", type="primary"):
        # Criar simulador
        simulador = SimuladorParOuImpar(min_numero, max_numero)
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔄 Executando simulação...")
        progress_bar.progress(50)
        
        # Executar simulação
        resultado = simulador.simular(n_simulacoes, seed)
        
        progress_bar.progress(100)
        status_text.text("✅ Simulação concluída!")
        
        # Armazenar resultados no session_state
        st.session_state.simulador = simulador
        st.session_state.resultado = resultado
        st.session_state.configuracao = {
            'min_numero': min_numero,
            'max_numero': max_numero,
            'n_simulacoes': n_simulacoes,
            'confianca': confianca
        }
    
    # Exibir resultados se disponíveis
    if 'resultado' in st.session_state:
        exibir_resultados()

def exibir_resultados():
    """Exibe todos os resultados da simulação."""
    simulador = st.session_state.simulador
    resultado = st.session_state.resultado
    config = st.session_state.configuracao
    
    # Métricas principais
    st.header("📊 Resultados da Simulação")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🎯 Configuração",
            f"[{config['min_numero']}-{config['max_numero']}]",
            f"{config['max_numero'] - config['min_numero'] + 1} números"
        )
    
    with col2:
        st.metric(
            "🔢 Simulações",
            f"{config['n_simulacoes']:,}",
            f"{resultado['tempo_execucao']:.3f}s"
        )
    
    with col3:
        st.metric(
            "🟦 Vitórias Par",
            f"{resultado['vitorias_par']:,}",
            f"{resultado['prob_par_obs']*100:.2f}%"
        )
    
    with col4:
        st.metric(
            "🟧 Vitórias Ímpar",
            f"{resultado['vitorias_impar']:,}",
            f"{resultado['prob_impar_obs']*100:.2f}%"
        )
    
    # Análise teórica vs observada
    st.header("🎯 Análise Teórica vs Observada")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Probabilidades Observadas")
        df_obs = pd.DataFrame({
            'Resultado': ['Par', 'Ímpar'],
            'Probabilidade': [resultado['prob_par_obs'], resultado['prob_impar_obs']],
            'Vitórias': [resultado['vitorias_par'], resultado['vitorias_impar']]
        })
        st.dataframe(df_obs, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Probabilidades Teóricas")
        df_teo = pd.DataFrame({
            'Resultado': ['Par', 'Ímpar'],
            'Probabilidade': [simulador.prob_teorica_par, simulador.prob_teorica_impar],
            'Vitórias Esperadas': [
                simulador.prob_teorica_par * config['n_simulacoes'],
                simulador.prob_teorica_impar * config['n_simulacoes']
            ]
        })
        st.dataframe(df_teo, use_container_width=True)
    
    # Análise estatística
    st.header("📊 Análise Estatística")
    
    ic_par = simulador.calcular_intervalo_confianca(
        resultado['vitorias_par'], 
        config['n_simulacoes'], 
        config['confianca']
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        diferenca_par = abs(resultado['prob_par_obs'] - simulador.prob_teorica_par)
        st.markdown(f"""
        <div class="metric-card">
            <h4>📐 Diferença Absoluta (Par)</h4>
            <h2>{diferenca_par*100:.3f}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>📏 Intervalo de Confiança ({config['confianca']*100:.0f}%)</h4>
            <h2>[{ic_par[0]*100:.2f}%, {ic_par[1]*100:.2f}%]</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        vies = (simulador.prob_teorica_par - 0.5) * 100
        vies_class = "success-metric" if abs(vies) < 0.1 else "warning-metric" if abs(vies) < 1 else "danger-metric"
        status_vies = "Equilibrado" if abs(vies) < 0.1 else f"Viés: {vies:+.2f}%"
        st.markdown(f"""
        <div class="metric-card {vies_class}">
            <h4>⚖️ Análise de Viés</h4>
            <h2>{status_vies}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Visualizações
    criar_visualizacoes(simulador, resultado, config)
    
    # Análise de distribuição das somas
    criar_analise_distribuicao(resultado)
    
    # Download dos dados
    criar_secao_download(simulador, resultado, config)

def criar_visualizacoes(simulador, resultado, config):
    """Cria visualizações interativas."""
    st.header("📈 Visualizações")
    
    # Dados para gráficos
    df_comparacao = pd.DataFrame({
        'Tipo': ['Observado', 'Observado', 'Teórico', 'Teórico'],
        'Resultado': ['Par', 'Ímpar', 'Par', 'Ímpar'],
        'Probabilidade': [
            resultado['prob_par_obs'], resultado['prob_impar_obs'],
            simulador.prob_teorica_par, simulador.prob_teorica_impar
        ],
        'Vitórias': [
            resultado['vitorias_par'], resultado['vitorias_impar'],
            simulador.prob_teorica_par * config['n_simulacoes'],
            simulador.prob_teorica_impar * config['n_simulacoes']
        ]
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras comparativo
        fig_barras = px.bar(
            df_comparacao, 
            x='Resultado', 
            y='Probabilidade',
            color='Tipo',
            barmode='group',
            title='Comparação: Observado vs Teórico',
            color_discrete_map={'Observado': '#1f77b4', 'Teórico': '#ff7f0e'}
        )
        fig_barras.update_layout(yaxis_tickformat='.1%')
        st.plotly_chart(fig_barras, use_container_width=True)
    
    with col2:
        # Gráfico de pizza
        df_pizza = df_comparacao[df_comparacao['Tipo'] == 'Observado']
        fig_pizza = px.pie(
            df_pizza,
            values='Vitórias',
            names='Resultado',
            title='Distribuição Observada',
            color_discrete_map={'Par': '#1f77b4', 'Ímpar': '#ff7f0e'}
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

def criar_analise_distribuicao(resultado):
    """Cria análise da distribuição das somas."""
    st.header("🔍 Análise da Distribuição das Somas")
    
    # Histograma das somas
    fig_hist = px.histogram(
        x=resultado['somas'],
        nbins=50,
        title='Distribuição das Somas',
        labels={'x': 'Soma', 'y': 'Frequência'},
        color_discrete_sequence=['#1f77b4']
    )
    
    # Adicionar linha vertical para média
    media_somas = np.mean(resultado['somas'])
    fig_hist.add_vline(x=media_somas, line_dash="dash", line_color="red", 
                       annotation_text=f"Média: {media_somas:.1f}")
    
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # Estatísticas das somas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Média", f"{np.mean(resultado['somas']):.2f}")
    with col2:
        st.metric("📏 Mediana", f"{np.median(resultado['somas']):.1f}")
    with col3:
        st.metric("📈 Desvio Padrão", f"{np.std(resultado['somas']):.2f}")
    with col4:
        st.metric("🎯 Moda", f"{stats.mode(resultado['somas'])[0]:.0f}")

def criar_secao_download(simulador, resultado, config):
    """Cria seção de download dos dados."""
    st.header("💾 Download dos Dados")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # DataFrame dos resultados detalhados
        df_detalhado = pd.DataFrame({
            'Jogador_1': resultado['numeros_j1'],
            'Jogador_2': resultado['numeros_j2'],
            'Soma': resultado['somas'],
            'Resultado': ['Par' if s % 2 == 0 else 'Ímpar' for s in resultado['somas']]
        })
        
        csv_detalhado = df_detalhado.to_csv(index=False)
        st.download_button(
            label="📊 Dados Detalhados (CSV)",
            data=csv_detalhado,
            file_name=f"simulacao_detalhada_{config['n_simulacoes']}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Resumo estatístico
        resumo = {
            'Configuração': f"[{config['min_numero']}-{config['max_numero']}]",
            'Simulações': config['n_simulacoes'],
            'Prob_Par_Observada': resultado['prob_par_obs'],
            'Prob_Par_Teórica': simulador.prob_teorica_par,
            'Prob_Ímpar_Observada': resultado['prob_impar_obs'],
            'Prob_Ímpar_Teórica': simulador.prob_teorica_impar,
            'Tempo_Execução': resultado['tempo_execucao']
        }
        
        df_resumo = pd.DataFrame([resumo])
        csv_resumo = df_resumo.to_csv(index=False)
        st.download_button(
            label="📈 Resumo Estatístico (CSV)",
            data=csv_resumo,
            file_name=f"resumo_simulacao_{config['n_simulacoes']}.csv",
            mime="text/csv"
        )
    
    with col3:
        # Análise de frequência das somas
        valores_unicos, contagens = np.unique(resultado['somas'], return_counts=True)
        df_freq = pd.DataFrame({
            'Soma': valores_unicos,
            'Frequência': contagens,
            'Probabilidade': contagens / len(resultado['somas']),
            'Tipo': ['Par' if s % 2 == 0 else 'Ímpar' for s in valores_unicos]
        })
        
        csv_freq = df_freq.to_csv(index=False)
        st.download_button(
            label="🔢 Frequência das Somas (CSV)",
            data=csv_freq,
            file_name=f"frequencia_somas_{config['n_simulacoes']}.csv",
            mime="text/csv"
        )

# Seção de informações
def criar_secao_info():
    """Cria seção informativa sobre o simulador."""
    with st.expander("ℹ️ Sobre o Simulador"):
        st.markdown("""
        ### 🎲 Como funciona
        
        Este simulador implementa o jogo tradicional "Par ou Ímpar" onde:
        - Dois jogadores escolhem números simultaneamente
        - A soma dos números determina o resultado (par ou ímpar)
        - Utilizamos simulação Monte Carlo para analisar as probabilidades
        
        ### 📊 Análise Estatística
        
        - **Probabilidades Teóricas**: Calculadas matematicamente
        - **Probabilidades Observadas**: Obtidas através da simulação
        - **Intervalo de Confiança**: Usando método de Wilson
        - **Análise de Viés**: Detecta se o jogo é equilibrado
        
        ### 🔧 Configurações
        
        - **Intervalo [0-20]**: Permite análise com 21 números (441 combinações)
        - **Simulações**: De 1.000 a 1.000.000 repetições
        - **Seed**: Para reprodutibilidade dos resultados
        - **Nível de Confiança**: Para intervalos estatísticos
        """)

if __name__ == "__main__":
    main()
    criar_secao_info()
