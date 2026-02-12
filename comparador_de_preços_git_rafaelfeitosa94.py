import streamlit as st 
import pandas as pd 
import google.generativeai as genai 
import json 
import re 
import os 
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import locale
import numpy as np

# =====================================================
# 🔐 CONFIGURAÇÃO DO GEMINI (API KEY)
# =====================================================
try:
    genai.configure(api_key="{sua chave gemini}")
    model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    st.error(f"❌ Erro na configuração: {e}")
    st.stop()

# =====================================================
# 💰 FUNÇÕES DE CONVERSÃO E FORMATAÇÃO DE MOEDA
# =====================================================

def limpar_valor_monetario(valor):
    """Converte string de moeda para float, lidando com diferentes formatos"""
    if pd.isna(valor) or valor == '' or valor is None:
        return np.nan
    
    try:
        # Se já for número, retorna como float
        if isinstance(valor, (int, float)):
            return float(valor)
        
        # Converte para string e limpa
        valor_str = str(valor).strip()
        
        # Remove 'R$' e espaços
        valor_str = valor_str.replace('R$', '').replace('$', '').strip()
        
        # Lida com formato brasileiro (1.234,56) e americano (1234.5)
        if ',' in valor_str and '.' in valor_str:
            # Formato 1.234,56
            if valor_str.rindex(',') > valor_str.rindex('.'):
                valor_str = valor_str.replace('.', '').replace(',', '.')
        elif ',' in valor_str and '.' not in valor_str:
            # Formato 1234,56
            valor_str = valor_str.replace(',', '.')
        elif '.' in valor_str and ',' not in valor_str:
            # Formato 1234.56 - já está ok
            pass
        
        # Remove quaisquer caracteres não numéricos exceto ponto
        valor_str = re.sub(r'[^\d.-]', '', valor_str)
        
        # Remove pontos extras (exceto o último que é separador decimal)
        partes = valor_str.split('.')
        if len(partes) > 2:
            valor_str = ''.join(partes[:-1]) + '.' + partes[-1]
        
        return float(valor_str) if valor_str else np.nan
        
    except Exception as e:
        print(f"Erro ao converter valor '{valor}': {e}")
        return np.nan

def formatar_moeda(valor):
    """Converte valor numérico para formato monetário brasileiro"""
    if pd.isna(valor) or valor == '' or valor == 0:
        return "R$ 0,00"
    try:
        valor_float = float(valor)
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def converter_para_moeda(df, coluna_preco='preco'):
    """Converte coluna de preço para float primeiro, depois formata como moeda"""
    if coluna_preco not in df.columns:
        df[coluna_preco] = np.nan
        df['preco_original'] = np.nan
        df['preco_formatado'] = "R$ 0,00"
        return df
    
    # Preservar valor original
    df['preco_original'] = df[coluna_preco].copy()
    
    # PASSO 1: Converter para float primeiro
    df[coluna_preco] = df[coluna_preco].apply(limpar_valor_monetario)
    
    # PASSO 2: Depois de ter os floats, formatar como moeda para exibição
    df['preco_formatado'] = df[coluna_preco].apply(formatar_moeda)
    
    return df

def testar_conversao_precos(df_rede, df_concorrencia):
    """Função de diagnóstico para testar a conversão de preços"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧪 Diagnóstico de Preços")
    
    with st.sidebar.expander("Ver diagnóstico de conversão"):
        if not df_rede.empty:
            st.write("**Rede - Amostra de preços originais:**")
            st.write(df_rede['preco_original'].head(10).tolist())
            st.write("**Rede - Preços convertidos:**")
            st.write(df_rede['preco'].head(10).tolist())
            st.write("**Rede - Preços formatados:**")
            st.write(df_rede['preco_formatado'].head(10).tolist())
        
        if not df_concorrencia.empty:
            st.write("**Concorrência - Amostra de preços originais:**")
            st.write(df_concorrencia['preco_original'].head(10).tolist())
            st.write("**Concorrência - Preços convertidos:**")
            st.write(df_concorrencia['preco'].head(10).tolist())
            st.write("**Concorrência - Preços formatados:**")
            st.write(df_concorrencia['preco_formatado'].head(10).tolist())

# =====================================================
# 🧠 BUSCA FLEXÍVEL (FOCO EM PROPOSTA E COMPOSIÇÃO)
# =====================================================

def buscar_similaridade_flexivel(produto_alvo, df_concorrencia, temperatura):
    if df_concorrencia.empty:
        return pd.DataFrame()

    # Criar uma cópia para não modificar o DataFrame original
    df_conc_copia = df_concorrencia.copy()
    
    # --------------------------------------------------
    # 🔎 FILTRO INTELIGENTE ANTES DE CHAMAR A IA
    # --------------------------------------------------
    palavras = str(produto_alvo["produto"]).lower().split()

    df_conc_copia["_match"] = 0
    for p in palavras:
        if len(p) > 2:  # Ignora palavras muito curtas
            df_conc_copia["_match"] += df_conc_copia["produto"].str.lower().str.contains(p, na=False, regex=False).astype(int)

    candidatos = (
        df_conc_copia
        .sort_values("_match", ascending=False)
        .head(200)
        .copy()
        .reset_index(drop=True)
    )
    candidatos = candidatos.reset_index().rename(columns={'index': 'idx_original'})

    if candidatos.empty:
        return pd.DataFrame()

    # --------------------------------------------------
    # 📦 MONTAR CONTEXTO
    # --------------------------------------------------
    contexto_itens = ""
    for _, row in candidatos.iterrows():
        preco_val = row.get('preco', np.nan)
        preco_str = row.get('preco_formatado', 'R$ 0,00') if pd.notna(preco_val) else 'R$ 0,00'

        contexto_itens += (
            f"ID: {row['idx_original']} | "
            f"Nome: {row['produto']} | "
            f"Descrição: {row['descricao']} | "
            f"Categoria: {row['categoria']} | "
            f"Restaurante: {row['restaurante']} | "
            f"Preço: {preco_str}\n"
        )

    descricao_alvo = str(produto_alvo.get('descricao', '')).strip()
    if not descricao_alvo or descricao_alvo == 'nan' or len(descricao_alvo) < 3:
        descricao_alvo = "Produto alimentar vendido em restaurante"

    preco_alvo = (
        produto_alvo.get('preco_formatado', 'R$ 0,00')
        if pd.notna(produto_alvo.get('preco'))
        else 'R$ 0,00'
    )

    prompt = f"""
Você é um especialista em concorrência de cardápios e análise de mercado gastronômico.

PRODUTO DA REDE:
Nome: {produto_alvo['produto']}
Descrição: {descricao_alvo}
Categoria: {produto_alvo['categoria']}
Restaurante: {produto_alvo['restaurante']}
Preço: {preco_alvo}

LISTA DE PRODUTOS DA CONCORRÊNCIA:
{contexto_itens}

Analise cuidadosamente e retorne APENAS um JSON válido no formato exato abaixo:

[
  {{"id": 12, "score": 0.85, "motivo": "texto explicando a similaridade"}}
]

REGRAS IMPORTANTES:
- Score deve ser entre 0 e 1 (use 0.5 como mínimo para similaridade moderada)
- Considere similaridade de ingredientes, preparo, experiência e proposta
- Não inclua produtos com score abaixo de 0.4
- Retorne SOMENTE o JSON, sem texto adicional
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": temperatura}
        )

        texto = response.text.strip()

        # --------------------------------------------------
        # 🧠 EXTRAIR JSON COM SEGURANÇA
        # --------------------------------------------------
        match = re.search(r'\[.*\]', texto, re.DOTALL)
        if not match:
            return pd.DataFrame()

        json_text = match.group()

        try:
            dados = json.loads(json_text)
        except:
            return pd.DataFrame()

        resultados_validos = {}

        for item in dados:
            try:
                idx = int(item["id"])
                score = float(item["score"])
                motivo = item.get("motivo", "Similaridade identificada pela IA")

                if idx in candidatos["idx_original"].values and score >= 0.4:
                    resultados_validos[idx] = {
                        "score": score,
                        "motivo": motivo
                    }
            except:
                continue

        if not resultados_validos:
            return pd.DataFrame()

        final_df = candidatos[
            candidatos["idx_original"].isin(resultados_validos.keys())
        ].copy()

        final_df["_score"] = final_df["idx_original"].map(
            lambda x: resultados_validos[x]["score"]
        )

        final_df["analise"] = final_df["idx_original"].map(
            lambda x: resultados_validos[x]["motivo"]
        )

        return final_df.sort_values("_score", ascending=False).drop(columns=['idx_original', '_match'], errors='ignore')

    except Exception as e:
        print(f"❌ Erro na busca de similaridade: {e}")
        return pd.DataFrame()

# =====================================================
# 🎯 FUNÇÃO PARA ENCONTRAR TOP SIMILARES POR CONCORRENTE
# =====================================================

def encontrar_top_similares_por_produto(df_rede, df_concorrencia, temperatura=0.3):
    """
    Para cada produto da rede, encontra os 3 produtos mais similares da concorrência
    Retorna DataFrame com comparação completa
    """
    
    resultados = []
    total_produtos = len(df_rede)
    
    if total_produtos == 0:
        return pd.DataFrame()
    
    # Barra de progresso
    progress_bar = st.progress(0, text="🔄 Analisando produtos da rede...")
    status_text = st.empty()
    
    for idx, produto in df_rede.iterrows():
        status_text.text(f"Analisando: {produto['produto'][:50]}... ({idx+1}/{total_produtos})")
        
        try:
            # Passar cópia do df_concorrencia para não modificar o original
            similares = buscar_similaridade_flexivel(produto, df_concorrencia.copy(), temperatura)
            
            if not similares.empty:
                # Pega top 3 por restaurante concorrente
                top_por_restaurante = []
                restaurantes_usados = set()
                
                for _, conc in similares.sort_values('_score', ascending=False).iterrows():
                    if conc['restaurante'] not in restaurantes_usados:
                        top_por_restaurante.append(conc)
                        restaurantes_usados.add(conc['restaurante'])
                    if len(top_por_restaurante) >= 3:
                        break
                
                # Organiza dados por coluna de preço, produto e descrição
                precos = []
                produtos_lista = []
                descricoes = []
                restaurantes_lista = []
                scores = []
                
                for conc in top_por_restaurante:
                    precos.append(conc.get('preco_formatado', 'R$ 0,00'))
                    produtos_lista.append(conc['produto'])
                    descricao = str(conc.get('descricao', ''))
                    if len(descricao) > 100:
                        descricao = descricao[:100] + '...'
                    descricoes.append(descricao)
                    restaurantes_lista.append(conc['restaurante'])
                    scores.append(f"{conc['_score']:.0%}")
                
                # Preenche com vazio se tiver menos de 3
                while len(precos) < 3:
                    precos.append('')
                    produtos_lista.append('')
                    descricoes.append('')
                    restaurantes_lista.append('')
                    scores.append('')
                
                descricao_rede = str(produto.get('descricao', ''))
                if len(descricao_rede) > 100:
                    descricao_rede = descricao_rede[:100] + '...'
                
                resultados.append({
                    'restaurante_rede': produto['restaurante'],
                    'produto_rede': produto['produto'],
                    'categoria_rede': produto.get('categoria', ''),
                    'preco_rede': produto.get('preco_formatado', 'R$ 0,00'),
                    'descricao_rede': descricao_rede,
                    
                    # Concorrente 1
                    'concorrente_1_restaurante': restaurantes_lista[0],
                    'concorrente_1_preco': precos[0],
                    'concorrente_1_produto': produtos_lista[0],
                    'concorrente_1_descricao': descricoes[0],
                    'concorrente_1_score': scores[0],
                    
                    # Concorrente 2
                    'concorrente_2_restaurante': restaurantes_lista[1],
                    'concorrente_2_preco': precos[1],
                    'concorrente_2_produto': produtos_lista[1],
                    'concorrente_2_descricao': descricoes[1],
                    'concorrente_2_score': scores[1],
                    
                    # Concorrente 3
                    'concorrente_3_restaurante': restaurantes_lista[2],
                    'concorrente_3_preco': precos[2],
                    'concorrente_3_produto': produtos_lista[2],
                    'concorrente_3_descricao': descricoes[2],
                    'concorrente_3_score': scores[2],
                })
            
        except Exception as e:
            print(f"Erro ao processar produto {produto['produto']}: {e}")
            continue
        
        # Atualiza barra de progresso
        progress_bar.progress((idx + 1) / total_produtos)
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(resultados)

# =====================================================
# 🔧 FUNÇÕES DE FILTRO PARA DASHBOARD
# =====================================================

def aplicar_filtros_sidebar(df_rede, df_concorrencia):
    """Aplica filtros na sidebar e retorna DataFrames filtrados"""
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔍 Filtros Globais")
        
        # Filtros para Rede
        if not df_rede.empty:
            st.markdown("**🏪 Filtros - Rede**")
            
            restaurantes_rede = sorted([str(r) for r in df_rede['restaurante'].unique() if pd.notna(r) and str(r).strip()])
            categorias_rede = sorted([str(c) for c in df_rede['categoria'].unique() if pd.notna(c) and str(c).strip()])
            
            filtro_restaurante_rede = st.multiselect(
                "Restaurantes da Rede",
                options=["Todos"] + restaurantes_rede,
                default=["Todos"]
            )
            
            filtro_categoria_rede = st.multiselect(
                "Categorias da Rede",
                options=["Todas"] + categorias_rede,
                default=["Todas"]
            )
        else:
            filtro_restaurante_rede = ["Todos"]
            filtro_categoria_rede = ["Todas"]
        
        # Filtros para Concorrência
        if not df_concorrencia.empty:
            st.markdown("**🏭 Filtros - Concorrência**")
            
            restaurantes_conc = sorted([str(r) for r in df_concorrencia['restaurante'].unique() if pd.notna(r) and str(r).strip()])
            categorias_conc = sorted([str(c) for c in df_concorrencia['categoria'].unique() if pd.notna(c) and str(c).strip()])
            
            filtro_restaurante_conc = st.multiselect(
                "Restaurantes Concorrentes",
                options=["Todos"] + restaurantes_conc,
                default=["Todos"]
            )
            
            filtro_categoria_conc = st.multiselect(
                "Categorias da Concorrência",
                options=["Todas"] + categorias_conc,
                default=["Todas"]
            )
        else:
            filtro_restaurante_conc = ["Todos"]
            filtro_categoria_conc = ["Todas"]
        
        st.markdown("---")
    
    # Aplica os filtros (sempre em cópias dos dados originais)
    df_rede_filtrado = df_rede.copy()
    df_concorrencia_filtrado = df_concorrencia.copy()
    
    # Filtro restaurante rede
    if filtro_restaurante_rede and "Todos" not in filtro_restaurante_rede:
        df_rede_filtrado = df_rede_filtrado[df_rede_filtrado['restaurante'].astype(str).isin(filtro_restaurante_rede)]
    
    # Filtro categoria rede
    if filtro_categoria_rede and "Todas" not in filtro_categoria_rede:
        df_rede_filtrado = df_rede_filtrado[df_rede_filtrado['categoria'].astype(str).isin(filtro_categoria_rede)]
    
    # Filtro restaurante concorrência
    if filtro_restaurante_conc and "Todos" not in filtro_restaurante_conc:
        df_concorrencia_filtrado = df_concorrencia_filtrado[df_concorrencia_filtrado['restaurante'].astype(str).isin(filtro_restaurante_conc)]
    
    # Filtro categoria concorrência
    if filtro_categoria_conc and "Todas" not in filtro_categoria_conc:
        df_concorrencia_filtrado = df_concorrencia_filtrado[df_concorrencia_filtrado['categoria'].astype(str).isin(filtro_categoria_conc)]
    
    return df_rede_filtrado, df_concorrencia_filtrado

# =====================================================
# 📊 FUNÇÕES DE VISUALIZAÇÃO E ANÁLISE
# =====================================================

def criar_metricas_dashboard(df_rede, df_concorrencia, similares=None, produto_alvo=None):
    """Cria métricas para o dashboard"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🏪 Total Produtos Rede",
            value=len(df_rede),
            delta=None
        )
    
    with col2:
        st.metric(
            label="🏭 Total Produtos Concorrência",
            value=len(df_concorrencia),
            delta=None
        )
    
    with col3:
        categorias_rede = df_rede['categoria'].nunique() if 'categoria' in df_rede.columns else 0
        st.metric(
            label="📋 Categorias (Rede)",
            value=categorias_rede,
            delta=None
        )
    
    with col4:
        if similares is not None and not similares.empty:
            st.metric(
                label="🎯 Concorrentes Encontrados",
                value=len(similares),
                delta=f"Média: {similares['_score'].mean():.0%}" if '_score' in similares.columns else "0%"
            )
        else:
            st.metric(label="🎯 Concorrentes Encontrados", value=0)

def grafico_distribuicao_categorias(df, titulo):
    """Gráfico de distribuição de categorias"""
    if 'categoria' not in df.columns or df.empty:
        return None
    
    df_cat = df.copy()
    df_cat['categoria'] = df_cat['categoria'].fillna('Sem Categoria').astype(str)
    
    cat_count = df_cat['categoria'].value_counts().head(10).reset_index()
    cat_count.columns = ['Categoria', 'Quantidade']
    
    fig = px.bar(
        cat_count, 
        x='Quantidade', 
        y='Categoria',
        orientation='h',
        title=titulo,
        color='Quantidade',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(height=400)
    return fig

def grafico_comparativo_precos(df_rede, df_concorrencia):
    """Comparação de preços entre rede e concorrência com valores em reais"""
    if 'preco' not in df_rede.columns or 'preco' not in df_concorrencia.columns:
        return None
    
    df_rede_preco = df_rede[df_rede['preco'].notna() & (df_rede['preco'] > 0)].copy()
    df_conc_preco = df_concorrencia[df_concorrencia['preco'].notna() & (df_concorrencia['preco'] > 0)].copy()
    
    if df_rede_preco.empty or df_conc_preco.empty:
        return None
    
    df_rede_preco['Tipo'] = 'Rede'
    df_conc_preco['Tipo'] = 'Concorrência'
    
    df_combinado = pd.concat([
        df_rede_preco[['preco', 'Tipo']],
        df_conc_preco[['preco', 'Tipo']]
    ])
    
    fig = px.box(
        df_combinado, 
        x='Tipo', 
        y='preco',
        title='📊 Distribuição de Preços: Rede vs Concorrência',
        color='Tipo',
        points='all',
        labels={'preco': 'Preço (R$)', 'Tipo': ''}
    )
    
    # Formatar eixo Y como moeda
    fig.update_yaxes(
        tickprefix='R$ ',
        tickformat=',.2f',
        separatethousands=True
    )
    
    return fig

def tabela_comparativa_restaurantes(df_concorrencia, similares):
    """Tabela com análise de concorrentes por restaurante"""
    if similares is None or similares.empty:
        return None
    
    # Usar apenas preços válidos (> 0)
    similares_validos = similares[similares['preco'].notna() & (similares['preco'] > 0)].copy()
    
    resumo = similares.groupby('restaurante').agg({
        'produto': 'count',
        '_score': 'mean',
        'analise': lambda x: ' | '.join(x.head(3))
    }).reset_index()
    
    # Calcular preço médio separadamente
    if not similares_validos.empty:
        preco_medio = similares_validos.groupby('restaurante')['preco'].mean().reset_index()
        preco_medio.columns = ['restaurante', 'Preço Médio']
        resumo = resumo.merge(preco_medio, on='restaurante', how='left')
        resumo['Preço Médio'] = resumo['Preço Médio'].apply(formatar_moeda)
    else:
        resumo['Preço Médio'] = 'R$ 0,00'
    
    resumo.columns = ['Restaurante', 'Produtos Similares', 'Score Médio', 'Exemplos de Análise', 'Preço Médio']
    resumo['Score Médio'] = resumo['Score Médio'].apply(lambda x: f"{x:.0%}")
    
    return resumo

def limpar_coluna_categorias(df):
    """Função para limpar e padronizar a coluna de categorias"""
    if 'categoria' in df.columns:
        df['categoria'] = df['categoria'].fillna('Sem Categoria').astype(str).str.strip()
        df.loc[df['categoria'] == '', 'categoria'] = 'Sem Categoria'
        df.loc[df['categoria'].str.len() < 2, 'categoria'] = 'Sem Categoria'
    return df

def gerar_relatorio_comparativo(df_comparacao):
    """Gera relatório textual da análise comparativa"""
    
    relatorio = []
    relatorio.append("=" * 80)
    relatorio.append("RELATÓRIO DE ANÁLISE COMPARATIVA - REDE vs CONCORRÊNCIA")
    relatorio.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    relatorio.append("=" * 80)
    relatorio.append("")
    
    # Resumo geral
    relatorio.append("📊 RESUMO GERAL")
    relatorio.append("-" * 40)
    relatorio.append(f"Total de produtos analisados: {len(df_comparacao)}")
    total_match = df_comparacao['concorrente_1_preco'].notna().sum() if 'concorrente_1_preco' in df_comparacao.columns else 0
    relatorio.append(f"Produtos com correspondência: {total_match}")
    if len(df_comparacao) > 0:
        relatorio.append(f"Percentual de cobertura: {total_match/len(df_comparacao)*100:.1f}%")
    relatorio.append(f"Concorrentes únicos identificados: {df_comparacao['concorrente_1_restaurante'].nunique() if 'concorrente_1_restaurante' in df_comparacao.columns else 0}")
    relatorio.append("")
    
    return "\n".join(relatorio)

# =====================================================
# 📁 CARREGAMENTO DE DADOS
# =====================================================
@st.cache_data(ttl=3600)
def carregar_dados(caminho):
    if not os.path.exists(caminho): 
        return pd.DataFrame()

    try:
        df = pd.read_excel(caminho)
        df.columns = [c.strip().lower() for c in df.columns]

        for c in ["categoria", "preco", "descricao", "restaurante", "produto"]:
            if c not in df.columns: 
                df[c] = ""

        # PASSO 1: Primeiro converter para float
        df = converter_para_moeda(df, 'preco')

        # PASSO 2: Limpar categorias
        df = limpar_coluna_categorias(df)

        # PASSO 3: Campo inteligente para busca
        df["texto_busca"] = (
            df["produto"].fillna('').astype(str) + " " +
            df["categoria"].fillna('').astype(str) + " " +
            df["restaurante"].fillna('').astype(str)
        ).str.lower()

        return df
    except Exception as e:
        st.error(f"Erro ao carregar {caminho}: {e}")
        return pd.DataFrame()

# =====================================================
# 🎨 CONFIGURAÇÃO DO DASHBOARD
# =====================================================
st.set_page_config(
    page_title="🍽️ IA Gastronômica - Dashboard Comparativo",
    page_icon="⚡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .stButton button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
    }
    .stProgress .st-bo {
        background-color: #FF4B4B;
    }
    .money-value {
        color: #00ff00;
        font-weight: bold;
        font-size: 1.2em;
    }
    .money-positive {
        color: #00ff00;
    }
    .money-negative {
        color: #ff4b4b;
    }
    .dataframe {
        font-size: 12px;
    }
    .dataframe td {
        max-width: 200px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .dataframe td:hover {
        white-space: normal;
        overflow: visible;
        background-color: #333;
        position: relative;
        z-index: 1000;
    }
    div[data-testid="stMetricValue"] {
        color: #FF4B4B;
    }
    div[data-testid="stMetricDelta"] {
        color: #00ff00;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        padding-left: 16px;
        padding-right: 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B20;
        border-bottom-color: #FF4B4B;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 📌 SIDEBAR - CONFIGURAÇÕES E FILTROS
# =====================================================
with st.sidebar:
    st.markdown("""
    <div style='text-align: center;'>
        <div style='font-size: 80px; line-height: 1;'>⚡</div>
        <div style='font-size: 25px; font-weight: bold;'>I M P E T T U S</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📁 Fontes de Dados")
    
    CAMINHO_CONCORRENCIA = r"{caminho dos dados da concorrencia em "xlsx"}"
    CAMINHO_REDE = r"{caminho dos dados da rede em "xlsx"}"
    
    with st.spinner("Carregando dados..."):
        df_concorrencia_original = carregar_dados(CAMINHO_CONCORRENCIA)
        df_rede_original = carregar_dados(CAMINHO_REDE)
    
    st.success(f"✅ Rede: {len(df_rede_original)} produtos")
    st.success(f"✅ Concorrência: {len(df_concorrencia_original)} produtos")
    
    # Aplica filtros globais SEMPRE nos dados originais
    df_rede_filtrado, df_concorrencia_filtrado = aplicar_filtros_sidebar(df_rede_original, df_concorrencia_original)
    
    st.markdown(f"**📊 Dados após filtros:**")
    st.info(f"🏪 Rede: {len(df_rede_filtrado)} produtos\n🏭 Concorrência: {len(df_concorrencia_filtrado)} produtos")
    
    # Configurações da IA
    st.markdown("---")
    st.markdown("### ⚙️ Configurações da IA")
    
    temperatura = st.slider(
        "Temperatura (criatividade)",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.1,
        help="Valores mais altos = mais criativo, valores mais baixos = mais conservador"
    )
    
    limite_resultados = st.slider(
        "Limite de resultados",
        min_value=5,
        max_value=30,
        value=10,
        step=5
    )
    
    # Diagnóstico de conversão
    testar_conversao_precos(df_rede_filtrado, df_concorrencia_filtrado)
    
    st.markdown("---")
    st.markdown("### ℹ️ Sobre")
    st.info(
        "Dashboard IA Gastronômica - Análise de Concorrência "
        "e Preços em Tempo Real"
    )

# =====================================================
# 🏠 MAIN - DASHBOARD PRINCIPAL
# =====================================================
st.title("💰 Comparador de Cardápios com IA - Análise de Preços")
st.markdown("*Busca focada na **experiência do cliente** e **análise competitiva de preços***")

# Tabs para organização
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🔍 Análise de Concorrência", 
        "📊 Visão Geral", 
        "📈 Comparativo de Preços",
        "🔄 Comparador Completo",
        "📋 Dados Detalhados"
    ]
)

# =====================================================
# 🔍 TAB 1 - ANÁLISE DE CONCORRÊNCIA
# =====================================================

with tab1:
    st.header("🔍 Análise de Concorrência por Produto")
    
    # Área de busca
    col1, col2 = st.columns([3, 1])
    
    with col1:
        busca = st.text_input(
            "🔎 Buscar produto da rede:",
            placeholder="Ex: picanha espetto, risoto camarão, hambúrguer artesanal...",
            help="Digite nome do produto, restaurante ou categoria",
            key="busca_produto"
        )
    
    with col2:
        busca_avancada = st.checkbox("Busca avançada", key="busca_avancada")
    
    if busca_avancada:
        with st.expander("🔧 Filtros avançados", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            
            with col_f1:
                categorias_rede = []
                if not df_rede_filtrado.empty and 'categoria' in df_rede_filtrado.columns:
                    categorias_rede = sorted([str(cat) for cat in df_rede_filtrado['categoria'].unique() if pd.notna(cat) and str(cat).strip()])
                
                categoria_filtro = st.selectbox(
                    "Categoria",
                    ["Todas"] + categorias_rede,
                    key="categoria_busca"
                )
            
            with col_f2:
                restaurantes_rede = []
                if not df_rede_filtrado.empty and 'restaurante' in df_rede_filtrado.columns:
                    restaurantes_rede = sorted([str(rest) for rest in df_rede_filtrado['restaurante'].unique() if pd.notna(rest) and str(rest).strip()])
                
                restaurante_filtro = st.selectbox(
                    "Restaurante",
                    ["Todos"] + restaurantes_rede,
                    key="restaurante_busca"
                )
            
            with col_f3:
                preco_max = st.number_input("Preço máximo (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="preco_max_busca")
    
    if busca:
        palavras_busca = [p for p in busca.lower().strip().split() if len(p) > 2]
        
        if not palavras_busca:
            st.warning("Digite termos mais específicos para busca (mínimo 3 caracteres)")
        else:
            df_busca = df_rede_filtrado.copy()
            df_busca["_score_busca"] = 0
            
            for palavra in palavras_busca:
                df_busca["_score_busca"] += df_busca["texto_busca"].str.contains(palavra, na=False, regex=False).astype(int)
            
            # Aplicar filtros avançados
            if busca_avancada:
                if categoria_filtro != "Todas":
                    df_busca = df_busca[df_busca['categoria'].astype(str) == categoria_filtro]
                if restaurante_filtro != "Todos":
                    df_busca = df_busca[df_busca['restaurante'].astype(str) == restaurante_filtro]
                if preco_max > 0:
                    df_busca = df_busca[df_busca['preco'] <= preco_max]
            
            match_rede = df_busca[df_busca["_score_busca"] > 0].sort_values("_score_busca", ascending=False)
            
            if not match_rede.empty:
                alvo = match_rede.iloc[0]
                
                # Card do produto alvo
                st.markdown("""
                <div style="background: linear-gradient(90deg, #2b2b2b 0%, #1e1e1e 100%); 
                            padding: 20px; border-radius: 10px; margin-bottom: 20px;
                            border-left: 5px solid #FF4B4B;">
                """, unsafe_allow_html=True)
                
                col_prod1, col_prod2, col_prod3 = st.columns([2, 1, 1])
                
                with col_prod1:
                    st.markdown(f"### 🎯 {alvo['produto']}")
                    st.markdown(f"**🏪 Restaurante:** {alvo['restaurante']}")
                    st.markdown(f"**📂 Categoria:** {alvo['categoria']}")
                
                with col_prod2:
                    st.markdown("### 💰 Preço")
                    if pd.notna(alvo.get('preco')) and alvo['preco'] > 0:
                        st.markdown(f"<p class='money-value'>{alvo['preco_formatado']}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("**Preço não informado**")
                
                with col_prod3:
                    st.markdown("### 📝 Descrição")
                    descricao = str(alvo.get('descricao', ''))
                    st.markdown(f"*{descricao[:100]}...*" if len(descricao) > 100 else f"*{descricao}*")
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Buscar similares
                with st.spinner("🤖 IA analisando concorrentes e preços..."):
                    similares = buscar_similaridade_flexivel(alvo, df_concorrencia_filtrado, temperatura)
                    if not similares.empty:
                        similares = similares.head(limite_resultados)
                
                # Métricas do dashboard
                criar_metricas_dashboard(df_rede_filtrado, df_concorrencia_filtrado, similares, alvo)
                
                if not similares.empty:
                    # Gráfico de scores
                    col_graf1, col_graf2 = st.columns(2)
                    
                    with col_graf1:
                        fig_scores = px.bar(
                            similares.head(10),
                            x='produto',
                            y='_score',
                            color='_score',
                            color_continuous_scale='RdYlGn',
                            title='🎯 Top 10 Concorrentes - Score de Similaridade',
                            labels={'_score': 'Score', 'produto': 'Produto'}
                        )
                        fig_scores.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig_scores, use_container_width=True)
                    
                    with col_graf2:
                        # Gráfico de comparação de preços
                        similares_preco = similares[similares['preco'].notna() & (similares['preco'] > 0)].head(10)
                        if not similares_preco.empty:
                            fig_preco_comp = px.scatter(
                                similares_preco,
                                x='_score',
                                y='preco',
                                size='preco',
                                color='restaurante',
                                hover_data=['produto'],
                                title='💰 Relação Score vs Preço',
                                labels={'_score': 'Score de Similaridade', 'preco': 'Preço (R$)'}
                            )
                            fig_preco_comp.update_yaxes(tickprefix='R$ ', tickformat=',.2f')
                            fig_preco_comp.update_layout(height=400)
                            st.plotly_chart(fig_preco_comp, use_container_width=True)
                        else:
                            st.info("Sem dados de preço válidos para o gráfico de dispersão")
                    
                    # Tabela de resultados
                    st.markdown("### 📋 Análise Detalhada dos Concorrentes")
                    
                    for idx, row in similares.iterrows():
                        cor_score = "#00ff00" if row['_score'] > 0.7 else "#ffff00" if row['_score'] > 0.5 else "#ff9900"
                        
                        with st.container():
                            col_res1, col_res2 = st.columns([3, 1])
                            
                            with col_res1:
                                st.markdown(f"""
                                <div style="border-left: 5px solid {cor_score}; padding: 10px; 
                                          background: #1e1e1e; margin-bottom: 10px; border-radius: 5px;">
                                    <h4 style="margin:0; color: white;">{row['produto']}</h4>
                                    <p style="color: #ccc; margin:5px 0;"><b>🏪 {row['restaurante']}</b></p>
                                    <p style="color: #ddd;"><i>"{row['analise'][:200]}..."</i></p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with col_res2:
                                preco_formatado = row.get('preco_formatado', 'R$ 0,00')
                                st.markdown(f"""
                                <div style="text-align: center; padding: 10px;">
                                    <h2 style="color: {cor_score};">{int(row['_score']*100)}%</h2>
                                    <p style="color: #aaa;">Match</p>
                                    <p style="color: #00ff00; font-size: 1.2em; font-weight: bold;">{preco_formatado}</p>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    # Tabela comparativa de restaurantes
                    resumo_restaurantes = tabela_comparativa_restaurantes(df_concorrencia_filtrado, similares)
                    if resumo_restaurantes is not None:
                        st.markdown("### 🏢 Análise por Restaurante Concorrente")
                        st.dataframe(
                            resumo_restaurantes,
                            width='stretch',
                            hide_index=True
                        )
                    
                    # Comparação de preços
                    st.markdown("### 💰 Análise de Preços vs Concorrência")
                    
                    preco_alvo = alvo.get('preco', 0)
                    if pd.notna(preco_alvo) and preco_alvo > 0:
                        precos_validos = similares['preco'][similares['preco'].notna() & (similares['preco'] > 0)]
                        
                        if not precos_validos.empty:
                            preco_medio_conc = precos_validos.mean()
                            diferenca = preco_alvo - preco_medio_conc
                            perc_diferenca = (diferenca / preco_alvo) * 100 if preco_alvo != 0 else 0
                            
                            col_comp1, col_comp2, col_comp3 = st.columns(3)
                            
                            with col_comp1:
                                st.metric(
                                    "Preço do Produto Alvo",
                                    formatar_moeda(preco_alvo)
                                )
                            
                            with col_comp2:
                                st.metric(
                                    "Preço Médio Concorrência",
                                    formatar_moeda(preco_medio_conc),
                                    delta=f"{formatar_moeda(abs(diferenca))} {'mais caro' if diferenca > 0 else 'mais barato'}",
                                    delta_color="inverse" if diferenca > 0 else "normal"
                                )
                            
                            with col_comp3:
                                st.metric(
                                    "Posicionamento",
                                    f"{perc_diferenca:.1f}% {'acima' if diferenca > 0 else 'abaixo'} da média"
                                )
                        else:
                            st.warning("Não há dados de preço válidos da concorrência para comparação")
                    else:
                        st.info("Produto alvo não possui preço válido para comparação")
                    
                else:
                    st.warning("""
                    😕 **Nenhum concorrente similar foi encontrado.**
                    
                    **Sugestões:**
                    - Tente uma busca com termos mais genéricos
                    - Aumente a temperatura da IA para resultados mais criativos
                    - Verifique se o produto é muito específico
                    """)
            else:
                st.warning("🔍 Nenhum produto encontrado. Tente outros termos de busca.")
    else:
        st.info("""
        👆 **Digite no campo de busca acima para começar**
        
        **Exemplos de busca:**
        - 🥩 "picanha"
        - 🍝 "risoto"
        - 🍔 "hambúrguer"
        - 🥗 "salada"
        """)

# =====================================================
# 📊 TAB 2 - VISÃO GERAL COM FILTROS
# =====================================================

with tab2:
    st.header("📊 Visão Geral do Mercado")
    
    # Filtros manuais específicos para Visão Geral
    col_filtro1, col_filtro2 = st.columns(2)
    col_filtro3, col_filtro4 = st.columns(2)
    
    with col_filtro1:
        categorias_rede_filtro = sorted([str(c) for c in df_rede_filtrado['categoria'].unique() if pd.notna(c) and str(c).strip()])
        categoria_selecionada = st.selectbox(
            "Filtrar Categoria - Rede",
            ["Todas"] + categorias_rede_filtro,
            key="categoria_rede_visao"
        )
    
    with col_filtro2:
        restaurantes_rede_filtro = sorted([str(r) for r in df_rede_filtrado['restaurante'].unique() if pd.notna(r) and str(r).strip()])
        restaurante_selecionado = st.selectbox(
            "Filtrar Restaurante - Rede",
            ["Todos"] + restaurantes_rede_filtro,
            key="restaurante_rede_visao"
        )
    
    with col_filtro3:
        categorias_conc_filtro = sorted([str(c) for c in df_concorrencia_filtrado['categoria'].unique() if pd.notna(c) and str(c).strip()])
        categoria_conc_selecionada = st.selectbox(
            "Filtrar Categoria - Concorrência",
            ["Todas"] + categorias_conc_filtro,
            key="categoria_conc_visao"
        )
    
    with col_filtro4:
        restaurantes_conc_filtro = sorted([str(r) for r in df_concorrencia_filtrado['restaurante'].unique() if pd.notna(r) and str(r).strip()])
        restaurante_conc_selecionado = st.selectbox(
            "Filtrar Restaurante - Concorrência",
            ["Todos"] + restaurantes_conc_filtro,
            key="restaurante_conc_visao"
        )
    
    # Aplica filtros adicionais da Visão Geral
    df_rede_visao = df_rede_filtrado.copy()
    df_conc_visao = df_concorrencia_filtrado.copy()
    
    if categoria_selecionada != "Todas":
        df_rede_visao = df_rede_visao[df_rede_visao['categoria'].astype(str) == categoria_selecionada]
    
    if restaurante_selecionado != "Todos":
        df_rede_visao = df_rede_visao[df_rede_visao['restaurante'].astype(str) == restaurante_selecionado]
    
    if categoria_conc_selecionada != "Todas":
        df_conc_visao = df_conc_visao[df_conc_visao['categoria'].astype(str) == categoria_conc_selecionada]
    
    if restaurante_conc_selecionado != "Todos":
        df_conc_visao = df_conc_visao[df_conc_visao['restaurante'].astype(str) == restaurante_conc_selecionado]
    
    # Gráficos com dados filtrados
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        fig_cat_rede = grafico_distribuicao_categorias(df_rede_visao, f"📊 Distribuição - Rede ({len(df_rede_visao)} produtos)")
        if fig_cat_rede:
            st.plotly_chart(fig_cat_rede, use_container_width=True)
        else:
            st.info("Sem dados de categoria para a Rede com os filtros selecionados")
    
    with col_graf2:
        fig_cat_conc = grafico_distribuicao_categorias(df_conc_visao, f"📊 Distribuição - Concorrência ({len(df_conc_visao)} produtos)")
        if fig_cat_conc:
            st.plotly_chart(fig_cat_conc, use_container_width=True)
        else:
            st.info("Sem dados de categoria para a Concorrência com os filtros selecionados")
    
    # Top produtos por categoria
    st.markdown("---")
    st.subheader("🏆 Top Produtos por Categoria")
    
    if not df_rede_visao.empty and 'categoria' in df_rede_visao.columns:
        df_temp = df_rede_visao.copy()
        df_temp['categoria'] = df_temp['categoria'].astype(str)
        categorias = df_temp['categoria'].value_counts().head(5).index.tolist()
        
        if categorias:
            tabs_cat = st.tabs(categorias)
            
            for i, cat in enumerate(categorias):
                with tabs_cat[i]:
                    produtos_cat = df_rede_visao[df_rede_visao['categoria'].astype(str) == cat].head(10).copy()
                    if not produtos_cat.empty:
                        if 'preco_formatado' in produtos_cat.columns:
                            produtos_cat['preco'] = produtos_cat['preco_formatado']
                        
                        cols_to_show = []
                        for col in ['produto', 'restaurante', 'preco', 'descricao']:
                            if col in produtos_cat.columns:
                                cols_to_show.append(col)
                        
                        st.dataframe(
                            produtos_cat[cols_to_show],
                            width='stretch',
                            hide_index=True
                        )

# =====================================================
# 📈 TAB 3 - COMPARATIVO DE PREÇOS COM FILTROS
# =====================================================

with tab3:
    st.header("📈 Análise Comparativa de Preços")
    
    # Filtros específicos para análise de preços
    col_filtro_preco1, col_filtro_preco2, col_filtro_preco3 = st.columns(3)
    
    with col_filtro_preco1:
        faixa_preco = st.selectbox(
            "Faixa de Preço",
            ["Todas", "Até R$30", "R$30-60", "R$60-100", "R$100-150", "Acima R$150"],
            key="faixa_preco_filtro"
        )
    
    with col_filtro_preco2:
        categorias_rede_preco = sorted([str(c) for c in df_rede_filtrado['categoria'].unique() if pd.notna(c) and str(c).strip()])
        cat_rede_preco = st.selectbox(
            "Categoria (Rede)",
            ["Todas"] + categorias_rede_preco,
            key="categoria_rede_preco"
        )
    
    with col_filtro_preco3:
        categorias_conc_preco = sorted([str(c) for c in df_concorrencia_filtrado['categoria'].unique() if pd.notna(c) and str(c).strip()])
        cat_conc_preco = st.selectbox(
            "Categoria (Concorrência)",
            ["Todas"] + categorias_conc_preco,
            key="categoria_conc_preco"
        )
    
    # Aplica filtros aos dados de preço
    df_rede_preco_filtrado = df_rede_filtrado.copy()
    df_conc_preco_filtrado = df_concorrencia_filtrado.copy()
    
    if cat_rede_preco != "Todas":
        df_rede_preco_filtrado = df_rede_preco_filtrado[df_rede_preco_filtrado['categoria'].astype(str) == cat_rede_preco]
    
    if cat_conc_preco != "Todas":
        df_conc_preco_filtrado = df_conc_preco_filtrado[df_conc_preco_filtrado['categoria'].astype(str) == cat_conc_preco]
    
    # Aplica filtro de faixa de preço
    if faixa_preco != "Todas":
        limites = {
            "Até R$30": (0, 30),
            "R$30-60": (30, 60),
            "R$60-100": (60, 100),
            "R$100-150": (100, 150),
            "Acima R$150": (150, float('inf'))
        }
        min_val, max_val = limites[faixa_preco]
        
        df_rede_preco_filtrado = df_rede_preco_filtrado[
            df_rede_preco_filtrado['preco'].notna() & 
            df_rede_preco_filtrado['preco'].between(min_val, max_val)
        ]
        df_conc_preco_filtrado = df_conc_preco_filtrado[
            df_conc_preco_filtrado['preco'].notna() & 
            df_conc_preco_filtrado['preco'].between(min_val, max_val)
        ]
    
    # Gráfico com dados filtrados
    fig_precos = grafico_comparativo_precos(df_rede_preco_filtrado, df_conc_preco_filtrado)
    if fig_precos:
        st.plotly_chart(fig_precos, use_container_width=True)
    else:
        st.warning("Dados de preço não disponíveis para comparação com os filtros selecionados")
    
    # Estatísticas detalhadas
    st.markdown("---")
    st.subheader("📊 Estatísticas Detalhadas de Preços")
    
    col_est1, col_est2 = st.columns(2)
    
    with col_est1:
        st.markdown("### 🏪 Rede")
        if not df_rede_preco_filtrado.empty:
            precos_rede = df_rede_preco_filtrado['preco'][df_rede_preco_filtrado['preco'].notna() & (df_rede_preco_filtrado['preco'] > 0)]
            if not precos_rede.empty:
                stats_rede = pd.DataFrame({
                    'Métrica': ['Média', 'Mediana', 'Mínimo', 'Máximo', 'Desvio Padrão', 'Total'],
                    'Valor': [
                        formatar_moeda(precos_rede.mean()),
                        formatar_moeda(precos_rede.median()),
                        formatar_moeda(precos_rede.min()),
                        formatar_moeda(precos_rede.max()),
                        formatar_moeda(precos_rede.std()),
                        formatar_moeda(precos_rede.sum())
                    ]
                })
                st.dataframe(stats_rede, hide_index=True, width='stretch')
            else:
                st.warning("Nenhum preço válido encontrado na Rede")
    
    with col_est2:
        st.markdown("### 🏭 Concorrência")
        if not df_conc_preco_filtrado.empty:
            precos_conc = df_conc_preco_filtrado['preco'][df_conc_preco_filtrado['preco'].notna() & (df_conc_preco_filtrado['preco'] > 0)]
            if not precos_conc.empty:
                stats_conc = pd.DataFrame({
                    'Métrica': ['Média', 'Mediana', 'Mínimo', 'Máximo', 'Desvio Padrão', 'Total'],
                    'Valor': [
                        formatar_moeda(precos_conc.mean()),
                        formatar_moeda(precos_conc.median()),
                        formatar_moeda(precos_conc.min()),
                        formatar_moeda(precos_conc.max()),
                        formatar_moeda(precos_conc.std()),
                        formatar_moeda(precos_conc.sum())
                    ]
                })
                st.dataframe(stats_conc, hide_index=True, width='stretch')
            else:
                st.warning("Nenhum preço válido encontrado na Concorrência")

# =====================================================
# 🔄 TAB 4 - COMPARADOR COMPLETO
# =====================================================

with tab4:
    st.header("🔄 Comparador Completo: Rede vs Concorrência")
    
    # Botão para iniciar análise completa
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    
    with col_btn2:
        iniciar_analise = st.button(
            "🚀 INICIAR ANÁLISE COMPLETA",
            use_container_width=True,
            type="primary",
            key="botao_analise_completa"
        )
    
    if iniciar_analise:
        # Usar cópia dos DataFrames filtrados para não afetar o estado global
        df_rede_analise = df_rede_filtrado.copy()
        df_conc_analise = df_concorrencia_filtrado.copy()
        
        if len(df_rede_analise) > 50:
            st.warning(f"⚠️ Você está analisando {len(df_rede_analise)} produtos. Isso pode levar alguns minutos.")
        
        with st.spinner("🔍 Analisando todos os produtos da rede contra a concorrência..."):
            df_comparacao_completa = encontrar_top_similares_por_produto(
                df_rede_analise, 
                df_conc_analise, 
                temperatura
            )
        
        if not df_comparacao_completa.empty:
            # Salva no session state
            st.session_state['df_comparacao'] = df_comparacao_completa
            
            # Métricas da análise
            col_met1, col_met2, col_met3 = st.columns(3)
            
            with col_met1:
                st.metric("📦 Produtos Analisados", len(df_comparacao_completa))
            
            with col_met2:
                total_similaridades = df_comparacao_completa['concorrente_1_preco'].notna().sum()
                st.metric("🎯 Correspondências Encontradas", total_similaridades)
            
            with col_met3:
                st.metric("🏢 Concorrentes Únicos", 
                         df_comparacao_completa['concorrente_1_restaurante'].nunique())
            
            # Informação do formato
            st.info("""
            **📋 Formato da tabela:**
            - **Rede:** Restaurante, Produto, Preço, Descrição, Categoria
            - **Preços:** Preço (Conc 1), Preço (Conc 2), Preço (Conc 3)
            - **Produtos:** Produto (Conc 1), Produto (Conc 2), Produto (Conc 3)
            - **Descrições:** Descrição (Conc 1), Descrição (Conc 2), Descrição (Conc 3)
            - **Informações:** Restaurante (Conc 1-3), Score (Conc 1-3)
            """)
            
            # Organiza colunas
            colunas_ordenadas = [
                'restaurante_rede', 'produto_rede', 'preco_rede', 'descricao_rede', 'categoria_rede',
                'concorrente_1_preco', 'concorrente_2_preco', 'concorrente_3_preco',
                'concorrente_1_produto', 'concorrente_2_produto', 'concorrente_3_produto',
                'concorrente_1_descricao', 'concorrente_2_descricao', 'concorrente_3_descricao',
                'concorrente_1_restaurante', 'concorrente_2_restaurante', 'concorrente_3_restaurante',
                'concorrente_1_score', 'concorrente_2_score', 'concorrente_3_score'
            ]
            
            # Renomeia colunas
            df_exibicao = df_comparacao_completa[colunas_ordenadas].copy()
            
            df_exibicao.columns = [
                '🏪 Restaurante (Rede)', '🍽️ Produto (Rede)', '💰 Preço (Rede)', '📝 Descrição (Rede)', '📂 Categoria',
                '💰 Preço (Conc 1)', '💰 Preço (Conc 2)', '💰 Preço (Conc 3)',
                '🍽️ Produto (Conc 1)', '🍽️ Produto (Conc 2)', '🍽️ Produto (Conc 3)',
                '📝 Descrição (Conc 1)', '📝 Descrição (Conc 2)', '📝 Descrição (Conc 3)',
                '🏭 Restaurante (Conc 1)', '🏭 Restaurante (Conc 2)', '🏭 Restaurante (Conc 3)',
                '🎯 Score (Conc 1)', '🎯 Score (Conc 2)', '🎯 Score (Conc 3)'
            ]
            
            # Exibe a tabela
            st.dataframe(
                df_exibicao,
                width='stretch',
                hide_index=True,
                height=600
            )
            
            # Downloads
            st.markdown("---")
            col_down1, col_down2, col_down3 = st.columns([1, 1, 1])
            
            with col_down1:
                csv_completo = df_exibicao.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV - Completo",
                    data=csv_completo,
                    file_name=f"comparacao_completa_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_down2:
                colunas_simplificadas = [
                    '🏪 Restaurante (Rede)', '🍽️ Produto (Rede)', '💰 Preço (Rede)',
                    '💰 Preço (Conc 1)', '💰 Preço (Conc 2)', '💰 Preço (Conc 3)',
                    '🍽️ Produto (Conc 1)', '🍽️ Produto (Conc 2)', '🍽️ Produto (Conc 3)',
                    '🏭 Restaurante (Conc 1)', '🏭 Restaurante (Conc 2)', '🏭 Restaurante (Conc 3)',
                    '🎯 Score (Conc 1)', '🎯 Score (Conc 2)', '🎯 Score (Conc 3)'
                ]
                df_simplificado = df_exibicao[colunas_simplificadas]
                csv_simplificado = df_simplificado.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Download CSV - Simplificado",
                    data=csv_simplificado,
                    file_name=f"comparacao_simplificada_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_down3:
                relatorio = gerar_relatorio_comparativo(df_comparacao_completa)
                st.download_button(
                    label="📊 Download Relatório",
                    data=relatorio.encode('utf-8'),
                    file_name=f"relatorio_comparativo_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
        else:
            st.warning("""
            ❌ **Não foi possível gerar a análise completa.**
            
            **Possíveis causas:**
            - Dados insuficientes na rede ou concorrência
            - Erro na comunicação com a IA
            - Filtros muito restritivos
            
            Tente ajustar os filtros ou reduzir o número de produtos.
            """)
    
    elif 'df_comparacao' in st.session_state:
        st.success("✅ Análise completa carregada da sessão!")
        
        if st.button("🔄 Refazer análise", use_container_width=True, key="refazer_analise"):
            st.session_state.pop('df_comparacao', None)
            st.rerun()
    
    else:
        st.info("""
        👆 **Clique em 'INICIAR ANÁLISE COMPLETA' para comparar todos os produtos da rede com a concorrência.**
        
        **A análise irá:**
        1. Processar cada produto da rede individualmente
        2. Encontrar os 3 produtos mais similares em restaurantes concorrentes
        3. Organizar os resultados em uma tabela completa
        4. Gerar arquivos para download (CSV e relatório)
        
        *⚠️ Este processo pode levar alguns minutos dependendo da quantidade de produtos.*
        """)

# =====================================================
# 📋 TAB 5 - DADOS DETALHADOS
# =====================================================

with tab5:
    st.header("📋 Dados Detalhados")
    
    tab_data1, tab_data2 = st.tabs(["📦 Produtos Rede", "🏭 Produtos Concorrência"])
    
    with tab_data1:
        if not df_rede_filtrado.empty:
            # Filtros
            col_filtro1, col_filtro2 = st.columns(2)
            
            with col_filtro1:
                categorias_rede = []
                if 'categoria' in df_rede_filtrado.columns:
                    categorias_rede = sorted([str(cat) for cat in df_rede_filtrado['categoria'].unique() if pd.notna(cat) and str(cat).strip()])
                
                filtro_cat_rede = st.multiselect(
                    "Filtrar por categoria",
                    options=categorias_rede,
                    default=[],
                    key="filtro_cat_rede_detalhes"
                )
            
            with col_filtro2:
                restaurantes_rede = []
                if 'restaurante' in df_rede_filtrado.columns:
                    restaurantes_rede = sorted([str(rest) for rest in df_rede_filtrado['restaurante'].unique() if pd.notna(rest) and str(rest).strip()])
                
                filtro_rest_rede = st.multiselect(
                    "Filtrar por restaurante",
                    options=restaurantes_rede,
                    default=[],
                    key="filtro_rest_rede_detalhes"
                )
            
            df_rede_detalhes = df_rede_filtrado.copy()
            
            if filtro_cat_rede:
                df_rede_detalhes = df_rede_detalhes[df_rede_detalhes['categoria'].astype(str).isin(filtro_cat_rede)]
            
            if filtro_rest_rede:
                df_rede_detalhes = df_rede_detalhes[df_rede_detalhes['restaurante'].astype(str).isin(filtro_rest_rede)]
            
            # Prepara exibição
            df_exibicao = df_rede_detalhes.copy()
            if 'preco_formatado' in df_exibicao.columns:
                df_exibicao['preco'] = df_exibicao['preco_formatado']
            
            cols_to_display = []
            for col in ['produto', 'restaurante', 'categoria', 'preco', 'descricao']:
                if col in df_exibicao.columns:
                    cols_to_display.append(col)
            
            st.dataframe(
                df_exibicao[cols_to_display],
                width='stretch',
                hide_index=True,
                height=500
            )
            
            # Download
            df_download = df_rede_detalhes.copy()
            if 'preco_formatado' in df_download.columns:
                df_download['preco'] = df_download['preco_formatado']
            
            csv = df_download.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV da Rede",
                data=csv,
                file_name=f"produtos_rede_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with tab_data2:
        if not df_concorrencia_filtrado.empty:
            # Filtros
            col_filtro1, col_filtro2 = st.columns(2)
            
            with col_filtro1:
                categorias_conc = []
                if 'categoria' in df_concorrencia_filtrado.columns:
                    categorias_conc = sorted([str(cat) for cat in df_concorrencia_filtrado['categoria'].unique() if pd.notna(cat) and str(cat).strip()])
                
                filtro_cat_conc = st.multiselect(
                    "Filtrar por categoria",
                    options=categorias_conc,
                    default=[],
                    key="filtro_cat_conc_detalhes"
                )
            
            with col_filtro2:
                restaurantes_conc = []
                if 'restaurante' in df_concorrencia_filtrado.columns:
                    restaurantes_conc = sorted([str(rest) for rest in df_concorrencia_filtrado['restaurante'].unique() if pd.notna(rest) and str(rest).strip()])
                
                filtro_rest_conc = st.multiselect(
                    "Filtrar por restaurante",
                    options=restaurantes_conc,
                    default=[],
                    key="filtro_rest_conc_detalhes"
                )
            
            df_conc_detalhes = df_concorrencia_filtrado.copy()
            
            if filtro_cat_conc:
                df_conc_detalhes = df_conc_detalhes[df_conc_detalhes['categoria'].astype(str).isin(filtro_cat_conc)]
            
            if filtro_rest_conc:
                df_conc_detalhes = df_conc_detalhes[df_conc_detalhes['restaurante'].astype(str).isin(filtro_rest_conc)]
            
            # Prepara exibição
            df_exibicao_conc = df_conc_detalhes.copy()
            if 'preco_formatado' in df_exibicao_conc.columns:
                df_exibicao_conc['preco'] = df_exibicao_conc['preco_formatado']
            
            cols_to_display = []
            for col in ['produto', 'restaurante', 'categoria', 'preco', 'descricao']:
                if col in df_exibicao_conc.columns:
                    cols_to_display.append(col)
            
            st.dataframe(
                df_exibicao_conc[cols_to_display].head(500),
                width='stretch',
                hide_index=True,
                height=500
            )
            
            # Download
            df_download_conc = df_conc_detalhes.copy()
            if 'preco_formatado' in df_download_conc.columns:
                df_download_conc['preco'] = df_download_conc['preco_formatado']
            
            csv = df_download_conc.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV da Concorrência",
                data=csv,
                file_name=f"produtos_concorrencia_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

# =====================================================
# 📌 FOOTER
# =====================================================
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns([1, 2, 1])

with col_footer2:
    st.markdown(
        f"""
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p>⚡️ Dashboard IA Gastronômica - Análise de Preços v3.1 | Desenvolvido com Streamlit + Google Gemini</p>
            <p style='font-size: 0.8em;'>© 2026 - Análise de Concorrência Inteligente com Preços em Tempo Real</p>
            <p style='font-size: 0.8em; color: #ff8c00;'>Powered By Rafael Feitosa</p>
        </div>
        """,
        unsafe_allow_html=True
    )