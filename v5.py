import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
from io import BytesIO
import base64

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(
    page_title="Dashboard de Vendas - Dark Style",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== ESTILOS GLOBAIS (Inspirado no dark dashboard) ====================
DARK_STYLES = """
<style>

/* ===== RESET & BASE ===== */
[data-testid="stAppViewContainer"] {
    background-color: #0F1117 !important;
}

[data-testid="stHeader"] {
    background-color: #0F1117 !important;
}

section[data-testid="stSidebar"] {
    background-color: #161B27 !important;
}

/* ===== TIPOGRAFIA ===== */
h1, h2, h3, h4, h5, h6, p, label, span {
    color: #F0F0F0 !important;
    font-family: 'Montserrat', sans-serif !important;
}

/* ===== CARDS DE MÉTRICAS (inspirado nos boxes do index.html) ===== */
.metric-card {
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 8px;
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.06);
    transition: all 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.3);
}

.metric-card .label {
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    opacity: 0.75;
    margin-bottom: 10px;
    color: #F0F0F0;
}

.metric-card .value {
    font-size: 32px;
    font-weight: 700;
    color: #FFFFFF;
}

.metric-card .icon {
    position: absolute;
    right: 20px;
    top: 50%;
    transform: translateY(-40%);
    font-size: 48px;
    opacity: 0.25;
}

/* Cores dos cards */
.metric-card.red-1 { background: linear-gradient(135deg, #B91C1C 0%, #7F1D1D 100%); }
.metric-card.red-2 { background: linear-gradient(135deg, #991B1B 0%, #6B1616 100%); }
.metric-card.red-3 { background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%); }
.metric-card.red-4 { background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%); }

/* ===== BOX SHADOW (igual ao index) ===== */
.box {
    background-color: #1C2130;
    border-radius: 20px;
    padding: 16px;
    margin-bottom: 20px;
    border: 1px solid #2E3650;
    transition: all 0.2s ease;
}

.box.shadow {
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}

/* ===== ABAS ===== */
[data-testid="stTabs"] [data-testid="stTab"] {
    background-color: #1C2130 !important;
    color: #9CA3AF !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 10px 18px !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 500 !important;
}

[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    background-color: #DC2626 !important;
    color: #FFFFFF !important;
}

/* ===== INPUTS ===== */
[data-testid="stSelectbox"] > div > div,
[data-testid="stDateInput"] input,
[data-testid="stMultiSelect"] > div {
    background-color: #1C2130 !important;
    border: 1px solid #2E3650 !important;
    color: #F0F0F0 !important;
    border-radius: 10px !important;
}

/* ===== BOTÃO ===== */
.stButton button {
    background: linear-gradient(135deg, #DC2626, #991B1B) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}

/* ===== DATAFRAME ===== */
[data-testid="stDataFrame"] {
    background-color: #0F1117 !important;
    border-radius: 10px !important;
    border: 1px solid #1C2130 !important;
}

[data-testid="stDataFrame"] div {
    color: #FFFFFF !important;
}

[data-testid="stDataFrame"] thead tr th {
    background-color: #1C2130 !important;
    color: #FFFFFF !important;
    font-weight: bold !important;
}

[data-testid="stDataFrame"] tbody tr {
    background-color: #0F1117 !important;
    color: #FFFFFF !important;
}

[data-testid="stDataFrame"] tbody tr:hover {
    background-color: #1C2130 !important;
}

/* ===== EXPANDER ===== */
[data-testid="stExpander"] {
    background-color: #161B27 !important;
    border: 1px solid #2E3650 !important;
    border-radius: 12px !important;
}

/* ===== SEPARADOR ===== */
hr {
    border-color: #2E3650 !important;
}

/* ===== TÍTULOS ===== */
.section-header {
    margin-bottom: 20px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2E3650;
}

.section-header h4 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
}

.section-header p {
    font-size: 12px;
    color: #9CA3AF !important;
}

/* ===== SPARKLINE PLACEHOLDER ===== */
.spark-placeholder {
    background: linear-gradient(90deg, #DC2626 0%, #EF4444 100%);
    height: 4px;
    border-radius: 2px;
    margin-top: 12px;
}

</style>
"""

# ==================== PALETA PLOTLY DARK ====================
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(28,33,48,0)",
    plot_bgcolor="rgba(28,33,48,0.6)",
    font=dict(color="#E2E8F0", family="Montserrat, sans-serif"),
    xaxis=dict(gridcolor="#2E3650", linecolor="#2E3650", tickcolor="#6B7280"),
    yaxis=dict(gridcolor="#2E3650", linecolor="#2E3650", tickcolor="#6B7280"),
    legend=dict(bgcolor="rgba(28,33,48,0.9)", bordercolor="#2E3650", borderwidth=1),
    margin=dict(l=20, r=20, t=60, b=40),
)

RED_SCALE = ["#7F1D1D", "#991B1B", "#B91C1C", "#DC2626", "#EF4444", "#F87171", "#FCA5A5"]
RED_CONTINUOUS = [[0.0, "#7F1D1D"], [0.5, "#DC2626"], [1.0, "#FCA5A5"]]


def aplicar_layout_dark(fig, title="", height=420):
    layout = dict(**PLOTLY_LAYOUT)
    layout["height"] = height
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(size=16, color="#F0F0F0"),
            x=0.02,
            xanchor="left"
        )
    fig.update_layout(**layout)
    return fig


# ==================== FUNÇÕES DE PROCESSAMENTO ====================
def normalizar_codigo(codigo):
    try:
        return str(int(float(str(codigo).strip())))
    except (ValueError, TypeError):
        return str(codigo).strip()


def process_produtos(response_data):
    if isinstance(response_data, dict) and 'vendas' in response_data:
        vendas = response_data['vendas']
    elif isinstance(response_data, list):
        vendas = response_data
    else:
        st.error("Estrutura de dados não reconhecida")
        return pd.DataFrame()

    todos_itens = []
    for venda in vendas:
        dados_venda = {
            'codLoja': venda.get('codLoja'),
            'datSincronizada': venda.get('datSincronizada'),
            'datMovimento': venda.get('datMovimento'),
            'dataVenda': venda.get('dataVenda'),
            'controle': venda.get('controle'),
            'tipoVenda': venda.get('tipoVenda'),
            'cancelada': venda.get('cancelada'),
            'valorTotal': venda.get('valorTotal'),
            'valorPago': venda.get('valorPago')
        }
        for item in venda.get('itens', []):
            todos_itens.append({**dados_venda, **item})

    df = pd.DataFrame(todos_itens)

    if df.empty:
        return pd.DataFrame()

    colunas_importantes = [
        'codLoja', 'datSincronizada', 'datMovimento', 'dataVenda', 'controle',
        'tipoVenda', 'cancelada', 'codProduto', 'descricaoProduto', 'quantidade',
        'valUnitario', 'valTotal', 'datHoraLancamento', 'valorTotal', 'valorPago'
    ]
    df = df[[col for col in colunas_importantes if col in df.columns]]

    if 'codProduto' in df.columns:
        df['codProduto'] = df['codProduto'].fillna(0).astype(float).astype(int).astype(str)
    if 'codLoja' in df.columns:
        df['codLoja'] = df['codLoja'].apply(normalizar_codigo)
    for col in ['controle', 'tipoVenda']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)
    for col in ['quantidade', 'valUnitario', 'valTotal']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for col in ["datSincronizada", "datMovimento", "dataVenda", "datHoraLancamento"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    if 'cancelada' in df.columns:
        df = df[df['cancelada'] == 'N']

    return df


def fetch_and_process_data(url, body, headers):
    try:
        response = requests.post(url, json=body, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return process_produtos(data)
        else:
            st.error(f"Erro na API: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return pd.DataFrame()


def get_lojas(token, codfranqueador):
    url_lojas = f"https://lx-degust-api-integracao-prd.azurewebsites.net/api/loja/listarLojasFranquia?codigoFranquia={codfranqueador}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = requests.get(url_lojas, headers=headers)
        if response.status_code == 200:
            return {
                normalizar_codigo(l.get('codigoLoja')): l.get('nomeLoja', f"Loja {l.get('codigoLoja')}")
                for l in response.json()
            }
    except Exception as e:
        st.error(f"Erro ao buscar lojas: {e}")
    return {}


@st.cache_data(ttl=300)
def load_all_data():
    codfranqueador = 1428
    credenciais = {
        "usuario": "06266555794",
        "senha": "250913",
        "codigoFranqueador": codfranqueador
    }
    url_auth = "https://lx-degust-api-integracao-prd.azurewebsites.net/api/usuario/autenticar"

    with st.spinner("🔐 Autenticando na API..."):
        response = requests.post(url_auth, json=credenciais)

    if response.status_code != 200:
        st.error("❌ Falha na autenticação")
        return pd.DataFrame()

    token = response.json()["acesso"]["token"]
    st.success("✅ Autenticado com sucesso!")

    dict_nomes_lojas = get_lojas(token, codfranqueador)

    presentday = datetime.now()
    last_week = presentday - timedelta(31)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url_lojas = f"https://lx-degust-api-integracao-prd.azurewebsites.net/api/loja/listarLojasFranquia?codigoFranquia={codfranqueador}"
    res_lojas = requests.get(url_lojas, headers=headers)

    if res_lojas.status_code == 200:
        codigos = [int(l.get('codigoLoja')) for l in res_lojas.json() if l.get('codigoLoja') is not None]
        loja_inicial = min(codigos) if codigos else 0
        loja_final = max(codigos) if codigos else 0
    else:
        st.error("Erro ao buscar lojas")
        return pd.DataFrame()

    body_api = {
        "codFranqueador": codfranqueador,
        "dataInicial": last_week.strftime("%Y-%m-%d"),
        "dataFinal": presentday.strftime("%Y-%m-%d"),
        "tipo": "intervalo",
        "listaDeLojas": "",
        "lojaInicial": loja_inicial,
        "lojaFinal": loja_final,
        "tipoData": "v",
        "combinarDatas": 0,
        "dataVenda": ""
    }

    with st.spinner("📊 Carregando dados de produtos vendidos..."):
        df = fetch_and_process_data(
            "https://lx-degust-api-integracao-prd.azurewebsites.net/api/venda/relatorio-vendas-periodo-sincronizado",
            body_api, headers
        )

    if df.empty:
        st.warning("⚠️ Nenhum dado retornado da API")
        return pd.DataFrame()

    if 'codLoja' in df.columns:
        df.insert(0, 'nomeFantasia', df['codLoja'].map(dict_nomes_lojas).fillna('Desconhecido'))

    if 'dataVenda' in df.columns:
        df = df.dropna(subset=['dataVenda'])
        st.success(f"✅ Dados carregados: {len(df)} registros")
    else:
        st.error("❌ Coluna 'dataVenda' não encontrada")
        return pd.DataFrame()

    return df


# ==================== HELPERS DE CARD (Estilo dashboard dark) ====================
def render_metric_card(label, value, icon, variant="red-1"):
    st.markdown(f"""
    <div class="metric-card {variant}">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        <div class="icon">{icon}</div>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title, subtitle=""):
    sub = f'<p>{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <div class="section-header">
        <h4>{title}</h4>
        {sub}
    </div>
    """, unsafe_allow_html=True)


def render_spark_placeholder():
    st.markdown('<div class="spark-placeholder"></div>', unsafe_allow_html=True)


# ==================== GRÁFICOS ====================
def create_line_chart_all_stores(df, produto_selecionado, data_inicio, data_fim, nomeFantasia):
    mask = (df['dataVenda'].dt.date >= data_inicio) & (df['dataVenda'].dt.date <= data_fim)
    if produto_selecionado != "Todos":
        mask &= df['descricaoProduto'] == produto_selecionado
    if nomeFantasia != "Todas":
        mask &= df['nomeFantasia'] == nomeFantasia

    df_filtrado = df[mask].copy()
    if df_filtrado.empty:
        return None

    vendas_diarias = df_filtrado.groupby(df_filtrado['dataVenda'].dt.date).agg(
        valor_total_vendido=('valTotal', 'sum'),
        quantidade_total=('quantidade', 'sum')
    ).reset_index().rename(columns={'dataVenda': 'data'})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=vendas_diarias['data'], y=vendas_diarias['valor_total_vendido'],
        name='Valor Total (R$)', line=dict(color='#EF4444', width=2.5),
        mode='lines+markers', marker=dict(size=7, color='#EF4444', line=dict(color='#FFFFFF', width=1.5)),
        fill='tozeroy', fillcolor='rgba(239,68,68,0.08)'
    ))
    fig.add_trace(go.Scatter(
        x=vendas_diarias['data'], y=vendas_diarias['quantidade_total'],
        name='Quantidade', line=dict(color='#60A5FA', width=2, dash='dot'),
        mode='lines+markers', marker=dict(size=6, color='#60A5FA'),
        yaxis='y2'
    ))
    
    fig.update_layout(
        yaxis=dict(title='Valor (R$)', title_font=dict(color='#EF4444')),
        yaxis2=dict(overlaying='y', side='right', title='Quantidade', title_font=dict(color='#60A5FA')),
    )
    return aplicar_layout_dark(fig, title="Evolução de Vendas por Dia")


def create_radial_bar_chart(df, data_inicio, data_fim):
    """Cria gráfico radial similar ao do index.html"""
    mask = (df['dataVenda'].dt.date >= data_inicio) & (df['dataVenda'].dt.date <= data_fim)
    df_filtrado = df[mask]
    
    if df_filtrado.empty:
        return None
    
    # Métricas para o radial
    total_vendas = df_filtrado['valTotal'].sum()
    total_qtd = df_filtrado['quantidade'].sum()
    total_transacoes = len(pd.unique(df_filtrado['controle'])) if 'controle' in df_filtrado.columns else len(df_filtrado)
    ticket_medio = total_vendas / total_transacoes if total_transacoes > 0 else 0
    
    # Calcular meta (exemplo: meta de 200k)
    meta = 200000
    percentual_meta = min(100, (total_vendas / meta) * 100)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=total_vendas,
        number={"prefix": "R$", "font": {"size": 24, "color": "#F0F0F0"}},
        delta={"reference": meta, "valueformat": ".0f"},
        gauge={
            "axis": {"range": [0, meta], "tickwidth": 1, "tickcolor": "#6B7280", "tickfont": {"color": "#9CA3AF"}},
            "bar": {"color": "#DC2626", "thickness": 0.7},
            "bgcolor": "#2E3650",
            "borderwidth": 0,
            "steps": [
                {"range": [0, meta * 0.5], "color": "#1C2130"},
                {"range": [meta * 0.5, meta], "color": "#161B27"}
            ],
            "threshold": {
                "line": {"color": "#EF4444", "width": 4},
                "thickness": 0.75,
                "value": meta
            }
        },
        title={"text": "Meta Diária de Faturamento da Rede", "font": {"size": 14, "color": "#9CA3AF"}}
    ))
    
    fig.update_layout(height=320)
    return aplicar_layout_dark(fig, title="")


def create_hourly_sales_chart(df, produto_selecionado, data_inicio, data_fim, nomeFantasia):
    mask = (df['dataVenda'].dt.date >= data_inicio) & (df['dataVenda'].dt.date <= data_fim)
    if produto_selecionado != "Todos":
        mask &= df['descricaoProduto'] == produto_selecionado
    if nomeFantasia != "Todas":
        mask &= df['nomeFantasia'] == nomeFantasia
    
    df_filtrado = df[mask].copy()
    if df_filtrado.empty:
        return None
    
    if 'datHoraLancamento' in df_filtrado.columns:
        df_filtrado['datHoraLancamento'] = pd.to_datetime(df_filtrado['datHoraLancamento'], errors='coerce')
        df_filtrado['hora'] = df_filtrado['datHoraLancamento'].dt.hour
        df_filtrado = df_filtrado.dropna(subset=['hora'])
        
        if df_filtrado.empty:
            return None
        
        vendas_por_hora = df_filtrado.groupby('hora').agg(
            valor_total_vendido=('valTotal', 'sum'),
            quantidade_total=('quantidade', 'sum'),
        ).reset_index()
        
        horas_completas = pd.DataFrame({'hora': range(24)})
        vendas_por_hora = horas_completas.merge(vendas_por_hora, on='hora', how='left').fillna(0)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=vendas_por_hora['hora'], 
            y=vendas_por_hora['valor_total_vendido'],
            name='Valor Total (R$)',
            marker_color='#EF4444',
            opacity=0.7,
        ))
        fig.add_trace(go.Scatter(
            x=vendas_por_hora['hora'], 
            y=vendas_por_hora['quantidade_total'],
            name='Quantidade',
            line=dict(color='#60A5FA', width=2.5),
            mode='lines+markers',
            marker=dict(size=8, color='#60A5FA', line=dict(color='#FFFFFF', width=1.5)),
            yaxis='y2'
        ))
        
        fig.update_layout(
            yaxis=dict(title='Valor (R$)', title_font=dict(color='#EF4444')),
            yaxis2=dict(overlaying='y', side='right', title='Quantidade', title_font=dict(color='#60A5FA')),
            xaxis=dict(title='Hora do Dia', tickmode='linear', tick0=0, dtick=2),
            bargap=0.1
        )
        
        return aplicar_layout_dark(fig, title="Vendas por Hora do Dia", height=400)
    
    return None


def create_multi_store_chart(df, produto, data_inicio, data_fim):
    mask = (df['dataVenda'].dt.date >= data_inicio) & (df['dataVenda'].dt.date <= data_fim)
    if produto != "Todos":
        mask &= df['descricaoProduto'] == produto
    df_filtrado = df[mask]
    if df_filtrado.empty:
        return None

    df_group = df_filtrado.groupby(
        [df_filtrado['dataVenda'].dt.date, 'nomeFantasia']
    )['valTotal'].sum().reset_index()

    fig = px.line(
        df_group, x='dataVenda', y='valTotal', color='nomeFantasia',
        markers=True, color_discrete_sequence=RED_SCALE
    )
    fig.update_traces(line=dict(width=2), marker=dict(size=6))
    fig.update_layout(xaxis_title="Data", yaxis_title="Valor Total (R$)", legend_title="Lojas")
    return aplicar_layout_dark(fig, title="Comparativo de Vendas por Loja")


def create_barchart_products(df, data_inicio, data_fim, nome_fantasia="Todas"):
    """Gráfico de barras dos top produtos - estilo index.html"""
    mask = (df['dataVenda'].dt.date >= data_inicio) & (df['dataVenda'].dt.date <= data_fim)
    if nome_fantasia != "Todas":
        mask &= df['nomeFantasia'] == nome_fantasia
    
    df_filtrado = df[mask]
    if df_filtrado.empty:
        return None
    
    top_produtos = df_filtrado.groupby('descricaoProduto')['valTotal'].sum().nlargest(8).reset_index()
    
    fig = px.bar(
        top_produtos, x='descricaoProduto', y='valTotal',
        color='valTotal', color_continuous_scale=RED_CONTINUOUS,
        text='valTotal'
    )
    fig.update_traces(
        texttemplate='R$ %{text:,.0f}', textposition='outside',
        marker_line_color='rgba(0,0,0,0)'
    )
    fig.update_layout(xaxis_title="Produto", yaxis_title="Faturamento (R$)", coloraxis_showscale=False)
    return aplicar_layout_dark(fig, title="Top 8 Produtos por Faturamento")


def create_areachart_trend(df, data_inicio, data_fim, nome_fantasia="Todas"):
    """Gráfico de área - estilo index.html"""
    mask = (df['dataVenda'].dt.date >= data_inicio) & (df['dataVenda'].dt.date <= data_fim)
    if nome_fantasia != "Todas":
        mask &= df['nomeFantasia'] == nome_fantasia
    
    df_filtrado = df[mask]
    if df_filtrado.empty:
        return None
    
    vendas_diarias = df_filtrado.groupby(df_filtrado['dataVenda'].dt.date)['valTotal'].sum().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=vendas_diarias['dataVenda'], y=vendas_diarias['valTotal'],
        fill='tozeroy', line=dict(color='#EF4444', width=2),
        name='Faturamento', mode='lines',
        fillcolor='rgba(239,68,68,0.15)'
    ))
    return aplicar_layout_dark(fig, title="Tendência de Faturamento Diário", height=400)


def create_ranking_chart(ranking_df, top_n):
    fig = px.bar(
        ranking_df, x='descricaoProduto', y='valTotal',
        color='valTotal', color_continuous_scale=RED_CONTINUOUS, text='valTotal'
    )
    fig.update_traces(
        texttemplate='R$ %{text:,.0f}', textposition='outside',
        marker_line_color='rgba(0,0,0,0)', textfont=dict(size=11)
    )
    fig.update_layout(xaxis_title="Produto", yaxis_title="Faturamento (R$)", coloraxis_showscale=False)
    return aplicar_layout_dark(fig, title=f"Top {top_n} Produtos por Faturamento")


def create_bar_lojas(metricas_loja):
    fig = px.bar(
        metricas_loja.head(10), x='nomeFantasia', y='valTotal',
        color='valTotal', color_continuous_scale=RED_CONTINUOUS, text='valTotal'
    )
    fig.update_traces(
        texttemplate='R$ %{text:,.0f}', textposition='outside',
        marker_line_color='rgba(0,0,0,0)'
    )
    fig.update_layout(xaxis_title="Loja", yaxis_title="Faturamento (R$)", coloraxis_showscale=False)
    return aplicar_layout_dark(fig, title="Top 10 Lojas por Faturamento")


def plot_curva_abc(curva_df):
    colors = curva_df['Classe ABC'].head(20).map({'A': '#EF4444', 'B': '#F97316', 'C': '#FBBF24'})
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=curva_df['Produto'].head(20), y=curva_df['Valor Total'].head(20),
        name='Valor', marker_color=colors,
        marker_line_color='rgba(0,0,0,0)'
    ))
    fig.add_trace(go.Scatter(
        x=curva_df['Produto'].head(20),
        y=curva_df['% Acumulado'].head(20).str.rstrip('%').astype(float),
        name='% Acumulado', yaxis='y2',
        line=dict(color='#60A5FA', width=2.5, dash='dot'),
        marker=dict(size=7, color='#60A5FA', line=dict(color='#FFFFFF', width=1))
    ))
    fig.update_layout(
        yaxis=dict(title='Valor Total (R$)'),
        yaxis2=dict(overlaying='y', side='right', title='% Acumulado', range=[0, 105]),
        bargap=0.25
    )
    return aplicar_layout_dark(fig, title="Curva ABC — Top 20 Produtos")


def create_pie(df_col, values_col, names_col, title):
    fig = px.pie(
        df_col, values=values_col, names=names_col,
        hole=0.38, color_discrete_sequence=RED_SCALE
    )
    fig.update_traces(
        textposition='inside', textinfo='percent+label',
        marker=dict(line=dict(color='#0F1117', width=2))
    )
    return aplicar_layout_dark(fig, title=title, height=400)


def create_heatmap(df_filtrado):
    top_produtos = df_filtrado.groupby('descricaoProduto')['valTotal'].sum().nlargest(10).index
    df_hm = df_filtrado[df_filtrado['descricaoProduto'].isin(top_produtos)]
    heatmap_data = df_hm.groupby(['nomeFantasia', 'descricaoProduto'])['valTotal'].sum().unstack(fill_value=0)
    if heatmap_data.empty:
        return None
    fig = px.imshow(
        heatmap_data, aspect="auto",
        color_continuous_scale=RED_CONTINUOUS,
        labels=dict(x="Produto", y="Loja", color="Faturamento (R$)")
    )
    return aplicar_layout_dark(fig, title="Heatmap — Produtos × Lojas (Top 10)")


# ==================== HELPERS DE DADOS ====================
def get_produtos_list(df):
    return sorted(df['descricaoProduto'].dropna().unique()) if 'descricaoProduto' in df.columns else []


def get_nome_fantasia_list(df):
    return sorted(df['nomeFantasia'].dropna().unique()) if 'nomeFantasia' in df.columns else []


def filtrar_df(df, produto, nome, data_inicio, data_fim):
    mask = (df['dataVenda'].dt.date >= data_inicio) & (df['dataVenda'].dt.date <= data_fim)
    if produto != "Todos":
        mask &= df['descricaoProduto'] == produto
    if nome not in ("Todas", "Todos"):
        mask &= df['nomeFantasia'] == nome
    return df[mask]


def prepare_table_data(df, produto_selecionado, data_inicio, data_fim, nome_selecionado):
    df_f = filtrar_df(df, produto_selecionado, nome_selecionado, data_inicio, data_fim)
    if df_f.empty:
        return pd.DataFrame()
    tabela = df_f[['nomeFantasia', 'dataVenda', 'quantidade', 'valTotal']].copy()
    tabela['dataVenda'] = tabela['dataVenda'].dt.strftime('%d/%m/%Y')
    tabela['valTotal'] = tabela['valTotal'].apply(lambda x: f"R$ {x:,.2f}")
    tabela.columns = ['Nome Fantasia', 'Data da Venda', 'Quantidade', 'Valor']
    tabela['_ord'] = pd.to_datetime(tabela['Data da Venda'], format='%d/%m/%Y')
    tabela = tabela.sort_values('_ord', ascending=False).drop('_ord', axis=1)
    return tabela


def curva_abc(df, data_inicio, data_fim, nome_fantasia="Todas"):
    df_f = filtrar_df(df, "Todos", nome_fantasia, data_inicio, data_fim)
    curva = df_f.groupby('descricaoProduto')['valTotal'].sum().reset_index().sort_values('valTotal', ascending=False)
    curva['acumulado'] = curva['valTotal'].cumsum()
    curva['percentual'] = curva['acumulado'] / curva['valTotal'].sum()
    curva['classe'] = curva['percentual'].apply(lambda p: 'A' if p <= 0.8 else ('B' if p <= 0.95 else 'C'))
    curva['percentual_acumulado'] = curva['percentual'].apply(lambda x: f"{x:.1%}")
    curva['valor_percentual'] = (curva['valTotal'] / curva['valTotal'].sum() * 100).round(1)
    curva = curva[['descricaoProduto', 'valTotal', 'valor_percentual', 'percentual_acumulado', 'classe']]
    curva.columns = ['Produto', 'Valor Total', '% do Total', '% Acumulado', 'Classe ABC']
    return curva


# ==================== ABAS ====================
def aba_analise_vendas(df):
    render_section_header("Filtros de Análise")
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        produtos = ["Todos"] + get_produtos_list(df)
        produto_selecionado = st.selectbox("Produto", produtos, key="produto_main")

    with col2:
        data_inicio = st.date_input(
            "Data Inicial",
            value=df['dataVenda'].max().date() - timedelta(days=5),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="data_inicio_main"
        )
        data_fim = st.date_input(
            "Data Final",
            value=df['dataVenda'].max().date(),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="data_fim_main"
        )

    with col3:
        lojas = ["Todas"] + get_nome_fantasia_list(df)
        nome_selecionado = st.selectbox("Loja", lojas, key="loja_main")

    if data_inicio > data_fim:
        st.error("⚠️ Data inicial não pode ser maior que data final!")
        return

    df_filtrado = filtrar_df(df, produto_selecionado, nome_selecionado, data_inicio, data_fim)

    if df_filtrado.empty:
        st.warning(f"⚠️ Nenhum dado encontrado para os filtros selecionados.")
        return

    total_vendas = df_filtrado['valTotal'].sum()
    total_qtd = df_filtrado['quantidade'].sum()
    total_transacoes = len(pd.unique(df_filtrado['controle'])) if 'controle' in df_filtrado.columns else len(df_filtrado)
    ticket_medio = total_vendas / total_transacoes if total_transacoes > 0 else 0

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Valor", f"R$ {total_vendas:,.0f}", "💰", "red-1")
    with c2:
        render_metric_card("Quantidade", f"{total_qtd:,.0f}", "📦", "red-2")
    with c3:
        render_metric_card("Ticket Médio P/ Cupom", f"R$ {ticket_medio:,.0f}", "🎫", "red-3")
    with c4:
        render_metric_card("Transações", f"{total_transacoes:,}", "📊", "red-4")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Layout em duas colunas para os gráficos principais
    col_left, col_right = st.columns([5, 7])
    
    with col_left:
        with st.container():
            st.markdown('<div class="box shadow">', unsafe_allow_html=True)
            fig_radial = create_radial_bar_chart(df, data_inicio, data_fim)
            if fig_radial:
                st.plotly_chart(fig_radial, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col_right:
        with st.container():
            st.markdown('<div class="box shadow">', unsafe_allow_html=True)
            fig_line = create_line_chart_all_stores(df, produto_selecionado, data_inicio, data_fim, nome_selecionado)
            if fig_line:
                st.plotly_chart(fig_line, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Segunda linha de gráficos
    col_left2, col_right2 = st.columns([5, 7])
    
    with col_left2:
        with st.container():
            st.markdown('<div class="box shadow">', unsafe_allow_html=True)
            fig_barchart = create_barchart_products(df, data_inicio, data_fim, nome_selecionado)
            if fig_barchart:
                st.plotly_chart(fig_barchart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col_right2:
        with st.container():
            st.markdown('<div class="box shadow">', unsafe_allow_html=True)
            fig_areachart = create_areachart_trend(df, data_inicio, data_fim, nome_selecionado)
            if fig_areachart:
                st.plotly_chart(fig_areachart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Gráfico de vendas por hora
    if 'datHoraLancamento' in df.columns:
        st.markdown('<div class="box shadow mt-4">', unsafe_allow_html=True)
        fig_hourly = create_hourly_sales_chart(df, produto_selecionado, data_inicio, data_fim, nome_selecionado)
        if fig_hourly:
            st.plotly_chart(fig_hourly, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabela de detalhamento
    st.markdown('<div class="box mt-4">', unsafe_allow_html=True)
    render_section_header("Detalhamento das Vendas", "Tabela completa de transações no período")
    tabela = prepare_table_data(df, produto_selecionado, data_inicio, data_fim, nome_selecionado)
    if not tabela.empty:
        st.caption(f"Exibindo {len(tabela)} registros")
        st.dataframe(tabela, use_container_width=True, hide_index=True)
        csv = tabela.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button("📥 Exportar CSV", data=csv,
            file_name=f"vendas_{data_inicio}_{data_fim}.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)


def aba_comparacao_lojas(df):
    render_section_header("Comparação entre Lojas", "Análise comparativa de performance")

    c1, c2 = st.columns([2, 1])
    with c1:
        data_inicio = st.date_input(
            "Data Inicial",
            value=df['dataVenda'].max().date() - timedelta(days=5),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="comp_inicio"
        )
        data_fim = st.date_input(
            "Data Final",
            value=df['dataVenda'].max().date(),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="comp_fim"
        )
    with c2:
        produtos = ["Todos"] + get_produtos_list(df)
        produto_selecionado = st.selectbox("Produto", produtos, key="comp_produto")

    if data_inicio > data_fim:
        st.error("⚠️ Data inicial não pode ser maior que data final!")
        return

    st.markdown('<div class="box shadow">', unsafe_allow_html=True)
    fig_comp = create_multi_store_chart(df, produto_selecionado, data_inicio, data_fim)
    if fig_comp:
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("⚠️ Nenhum dado disponível para o período selecionado.")
    st.markdown('</div>', unsafe_allow_html=True)

    df_filtrado = filtrar_df(df, produto_selecionado, "Todas", data_inicio, data_fim)
    if df_filtrado.empty:
        return

    metricas_loja = df_filtrado.groupby('nomeFantasia').agg(
        valTotal=('valTotal', 'sum'), quantidade=('quantidade', 'sum')
    ).reset_index().sort_values('valTotal', ascending=False)
    metricas_loja['ticket_medio'] = metricas_loja['valTotal'] / metricas_loja['quantidade']

    st.markdown('<div class="box">', unsafe_allow_html=True)
    render_section_header("Métricas Comparativas")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Ranking por Faturamento**")
        st.dataframe(metricas_loja[['nomeFantasia', 'valTotal']].style.format({'valTotal': 'R$ {:,.2f}'}),
            use_container_width=True)
    with c2:
        st.markdown("**Ranking por Quantidade**")
        st.dataframe(metricas_loja[['nomeFantasia', 'quantidade']].style.format({'quantidade': '{:,.0f}'}),
            use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="box shadow">', unsafe_allow_html=True)
    st.plotly_chart(create_bar_lojas(metricas_loja), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="box shadow">', unsafe_allow_html=True)
    fig_hm = create_heatmap(df_filtrado)
    if fig_hm:
        st.plotly_chart(fig_hm, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


def aba_ranking_produtos(df):
    render_section_header("Ranking de Produtos", "Performance e distribuição de faturamento")

    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        data_inicio = st.date_input(
            "Data Inicial",
            value=df['dataVenda'].max().date() - timedelta(days=5),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="rank_inicio"
        )
        data_fim = st.date_input(
            "Data Final",
            value=df['dataVenda'].max().date(),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="rank_fim"
        )
    
    with col2:
        lojas = ["Todas"] + get_nome_fantasia_list(df)
        nome_selecionado = st.selectbox("Loja", lojas, key="rank_loja")
    
    with col3:
        top_n = st.slider("Quantidade de produtos no ranking", 5, 30, 10, 5, key="rank_top_n")

    if data_inicio > data_fim:
        st.error("⚠️ Data inicial não pode ser maior que data final!")
        return

    df_filtrado = filtrar_df(df, "Todos", nome_selecionado, data_inicio, data_fim)
    if df_filtrado.empty:
        st.warning("⚠️ Nenhum dado disponível para os filtros selecionados.")
        return

    ranking = df_filtrado.groupby('descricaoProduto').agg(
        valTotal=('valTotal', 'sum'), quantidade=('quantidade', 'sum')
    ).reset_index().sort_values('valTotal', ascending=False).head(top_n)
    ranking['ranking'] = range(1, len(ranking) + 1)
    ranking['ticket_medio'] = ranking['valTotal'] / ranking['quantidade']

    st.markdown('<div class="box shadow">', unsafe_allow_html=True)
    st.plotly_chart(create_ranking_chart(ranking, top_n), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="box">', unsafe_allow_html=True)
    render_section_header("Detalhamento do Ranking")
    tabela_rank = ranking[['ranking', 'descricaoProduto', 'valTotal', 'quantidade', 'ticket_medio']].copy()
    tabela_rank.columns = ['Ranking', 'Produto', 'Faturamento Total', 'Quantidade Vendida', 'Ticket Médio']
    st.dataframe(
        tabela_rank.style.format({
            'Faturamento Total': 'R$ {:,.2f}',
            'Quantidade Vendida': '{:,.0f}',
            'Ticket Médio': 'R$ {:,.2f}'
        }),
        use_container_width=True, height=380
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="box shadow">', unsafe_allow_html=True)
    st.plotly_chart(create_pie(ranking, 'valTotal', 'descricaoProduto',
        f"Distribuição do Faturamento — Top {top_n} Produtos"), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    csv_rank = tabela_rank.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button("📥 Exportar Ranking CSV", data=csv_rank,
        file_name=f"ranking_{nome_selecionado}_{data_inicio}_{data_fim}.csv", mime="text/csv")


def aba_curva_abc(df):
    render_section_header("Análise de Curva ABC", "Classificação estratégica de produtos")

    st.info("""
    **Classe A (80%)** — Produtos responsáveis por 80% do faturamento (alta prioridade)  
    **Classe B (15%)** — Próximos 15% do faturamento (média prioridade)  
    **Classe C (5%)** — Últimos 5% do faturamento (baixa prioridade)
    """)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        data_inicio = st.date_input(
            "Data Inicial",
            value=df['dataVenda'].max().date() - timedelta(days=5),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="abc_inicio"
        )
        data_fim = st.date_input(
            "Data Final",
            value=df['dataVenda'].max().date(),
            min_value=df['dataVenda'].min().date(),
            max_value=df['dataVenda'].max().date(),
            key="abc_fim"
        )
    
    with col2:
        lojas = ["Todas"] + get_nome_fantasia_list(df)
        nome_selecionado = st.selectbox("Loja", lojas, key="abc_loja")

    if data_inicio > data_fim:
        st.error("⚠️ Data inicial não pode ser maior que data final!")
        return

    curva_df = curva_abc(df, data_inicio, data_fim, nome_selecionado)
    if curva_df.empty:
        st.warning("⚠️ Nenhum dado disponível para os filtros selecionados.")
        return

    qtd_a = len(curva_df[curva_df['Classe ABC'] == 'A'])
    qtd_b = len(curva_df[curva_df['Classe ABC'] == 'B'])
    qtd_c = len(curva_df[curva_df['Classe ABC'] == 'C'])

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Classe A", f"{qtd_a} produtos", "⭐", "red-1")
    with c2:
        render_metric_card("Classe B", f"{qtd_b} produtos", "🟡", "red-2")
    with c3:
        render_metric_card("Classe C", f"{qtd_c} produtos", "🟢", "red-3")

    st.markdown('<div class="box shadow">', unsafe_allow_html=True)
    st.plotly_chart(plot_curva_abc(curva_df), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="box">', unsafe_allow_html=True)
    render_section_header("Classificação Detalhada dos Produtos")

    classe_filtro = st.multiselect("Filtrar por Classe ABC", ['A', 'B', 'C'], default=['A', 'B', 'C'], key="abc_classe")
    curva_filtrada = curva_df[curva_df['Classe ABC'].isin(classe_filtro)]

    st.dataframe(
        curva_filtrada.style.format({'Valor Total': 'R$ {:,.2f}', '% do Total': '{:.1f}%'}),
        use_container_width=True, height=380
    )
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    dist = curva_df.groupby('Classe ABC').agg(valor=('Valor Total', 'sum'), qtd=('Produto', 'count')).reset_index()

    with c1:
        fig_pie = px.pie(dist, values='valor', names='Classe ABC',
            title="Faturamento por Classe",
            color='Classe ABC', color_discrete_map={'A': '#EF4444', 'B': '#F97316', 'C': '#FBBF24'},
            hole=0.38)
        fig_pie.update_traces(
            textposition='inside', textinfo='percent+label',
            marker=dict(line=dict(color='#0F1117', width=2))
        )
        st.plotly_chart(aplicar_layout_dark(fig_pie, height=380), use_container_width=True)

    with c2:
        fig_bar = px.bar(dist, x='Classe ABC', y='qtd',
            color='Classe ABC', color_discrete_map={'A': '#EF4444', 'B': '#F97316', 'C': '#FBBF24'},
            text='qtd', title="Quantidade de Produtos por Classe")
        fig_bar.update_traces(textposition='outside', marker_line_color='rgba(0,0,0,0)')
        st.plotly_chart(aplicar_layout_dark(fig_bar, height=380), use_container_width=True)

    csv_abc = curva_df.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button("📥 Exportar Curva ABC CSV", data=csv_abc,
        file_name=f"curva_abc_{nome_selecionado}_{data_inicio}_{data_fim}.csv", mime="text/csv")


# ==================== MAIN ====================
def main():
    st.markdown(DARK_STYLES, unsafe_allow_html=True)

    st.markdown("""
    <div style="padding: 8px 0 24px 0;">
        <h1 style="margin:0; font-size:28px; font-weight:700; color:#F0F0F0;">
            🍽️ Dashboard de Performance de Vendas
        </h1>
        <p style="margin:4px 0 0 0; color:#6B7280; font-size:14px;">
            Análise detalhada de produtos e lojas
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_all_data()

    if df.empty:
        st.warning("⚠️ Nenhum dado disponível para exibição.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊  Análise de Vendas",
        "🔥  Comparação entre Lojas",
        "📈  Ranking de Produtos",
        "🎯  Curva ABC"
    ])

    with tab1:
        aba_analise_vendas(df)
    with tab2:
        aba_comparacao_lojas(df)
    with tab3:
        aba_ranking_produtos(df)
    with tab4:
        aba_curva_abc(df)


if __name__ == "__main__":
    main()