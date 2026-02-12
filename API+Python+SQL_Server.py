import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# Configuração de datas
presentday = datetime.now()
last_week = presentday - timedelta(5)
yesterday = presentday - timedelta(1)



yesterday_str = yesterday.strftime("%Y-%m-%d")
last_week_str = last_week.strftime("%Y-%m-%d")

# Autenticação na API
codfranqueador = {suas credenciais}
credenciais = {
    "usuario": "{suas credenciais}",
    "senha": "{suas credenciais}",
    "codigoFranqueador": {suas credenciais}
}

response = requests.post(
    "https://lx-degust-api-integracao-prd.azurewebsites.net/api/usuario/autenticar",
    json=credenciais
)

if response.status_code == 200:
    token_automatico = response.json()["acesso"]["token"]
    print("🔑 Token obtido com sucesso")
else:
    raise Exception(f"❌ Erro ao autenticar: {response.status_code} - {response.text}")

# Obter lista de lojas
headers = {
    "Authorization": f"Bearer {token_automatico}",
    "Content-Type": "application/json"
}
res_lojas = requests.get(
    f"https://lx-degust-api-integracao-prd.azurewebsites.net/api/loja/listarLojasFranquia?codigoFranquia={codfranqueador}",
    headers=headers
)

if res_lojas.status_code == 200:
    codigos_lojas = [loja['codigoLoja'] for loja in res_lojas.json() if 'codigoLoja' in loja]
    loja_inicial = min(codigos_lojas)
    loja_final = max(codigos_lojas)
else:
    raise Exception(f"Erro ao buscar lojas: {res_lojas.status_code} - {res_lojas.text}")

# Configuração do banco de dados
engine = create_engine(
    "mssql+pyodbc://{usuario sql server}:{senha sql server}\\{servidor}/{banco de dados}?driver=ODBC+Driver+17+for+SQL+Server"
)

# Função para deletar dados antigos
def delete_old_data(table_name, date_column):
    with engine.begin() as connection:
        delete_query = f"""
        DELETE FROM {table_name} 
        WHERE {date_column} BETWEEN '{last_week_str}' AND '{yesterday_str}'
        """
        connection.execute(text(delete_query))
        print(f"🧹 Dados antigos deletados de {table_name}")

# -------------------------------
# 1. PROCESSAMENTO BD_PAGAMENTOS_V2
# -------------------------------
print("\n" + "="*50)
print("PROCESSANDO tabela")
print("="*50)

url = "https://lx-degust-api-integracao-prd.azurewebsites.net/api/venda/relatorio-vendas-periodo-sincronizado?"
body = {
    "codFranqueador": codfranqueador,
    "dataInicial": last_week_str,
    "dataFinal": yesterday_str,
    "tipo": "intervalo",
    "listaDeLojas": "string",
    "lojaInicial": loja_inicial,
    "lojaFinal": loja_final,
    "tipoData": "v",
    "combinarDatas": 0,
    "dataVenda": "string"
}

response = requests.post(url, json=body, headers=headers)
df = pd.DataFrame()

if response.status_code == 200:
    data = response.json().get('vendas', []) if isinstance(response.json(), dict) else response.json()
    if data:
        df = pd.DataFrame(data)

if not df.empty:
    # Processamento dos dados (mantido igual)
    df = df[["codLoja", "datSincronizada", "datMovimento", "dataVenda", "controle", "cancelada", 
             "tipoVenda", "valorPago", "formaPagamento"]]
    
    df_exploded = df.explode("formaPagamento")
    df_itens = pd.json_normalize(df_exploded["formaPagamento"]).drop(["codLoja", "controle"], axis=1, errors="ignore")
    
    df_final = pd.concat([df_exploded.drop("formaPagamento", axis=1).reset_index(drop=True), df_itens], axis=1)
    df_final = df_final[["codLoja", "datSincronizada", "datMovimento", "dataVenda", "cancelada", "controle",
                         "tipoVenda", "valorPago", "sequencia", "codFormaPagamento", "valor", "receita"]]
    
    # Conversões de tipo (mantido igual)
    df_final["codFormaPagamento"] = df_final["codFormaPagamento"].fillna(0).astype(float).astype(int).astype(str)
    df_final[["codLoja", "controle", "tipoVenda"]] = df_final[["codLoja", "controle", "tipoVenda"]].astype(str)
    df_final['valor'] = df_final['valor'].astype(str).str.replace(',', '.').astype(float)
    df_final['sequencia'] = df_final['sequencia'].fillna(0)
    df_final['receita'] = df_final['receita'].fillna('DINHEIRO')
    df_final.loc[df_final['tipoVenda'] == '0', 'tipoVenda'] = '3'
    
    # Agregação (mantido igual)
    df_final = df_final.groupby(["codLoja", "controle", "sequencia", "codFormaPagamento", "valor"], as_index=False).agg({
        "datSincronizada": "max",
        "datMovimento": "max",
        "dataVenda": "max",
        "tipoVenda": "first",
        "valorPago": "sum",
        "receita": "first",
        "cancelada": "first"
    })
    
    # Converter datas
    for col in ["datSincronizada", "datMovimento", "dataVenda"]:
        df_final[col] = pd.to_datetime(df_final[col], errors='coerce')

    # 1. Deletar dados antigos
    delete_old_data("{tabela}", "{coluna de data referencia}")
    
    # 2. Carregar novos dados (MERGE original)
    temp_table = "temp_"
    df_final.to_sql(temp_table, con=engine, if_exists='replace', index=False)
    
    with engine.begin() as connection:
        merge_PG = """
        MERGE INTO {tabela} AS target
        USING temp_pagamentos AS source
        ON target.codLoja = source.codLoja
        AND target.controle = source.controle
        AND target.sequencia = source.sequencia
        AND target.codFormaPagamento = source.codFormaPagamento

        WHEN MATCHED THEN
            UPDATE SET
                target.datSincronizada = source.datSincronizada,
                target.datMovimento = source.datMovimento,
                target.dataVenda = source.dataVenda,
                target.valorPago = source.valorPago,
                target.valor = source.valor,
                target.receita = source.receita,
                target.cancelada = source.cancelada

        WHEN NOT MATCHED THEN
            INSERT (codLoja, datSincronizada, datMovimento, dataVenda, controle, tipoVenda, valorPago,
                    sequencia, codFormaPagamento, valor, receita, cancelada)
            VALUES (source.codLoja, source.datSincronizada, source.datMovimento, source.dataVenda, source.controle,
                    source.tipoVenda, source.valorPago, source.sequencia, source.codFormaPagamento, source.valor, source.receita, source.cancelada);
        """
        connection.execute(text(merge_PG))
        connection.execute(text(f"DROP TABLE {temp_table}"))
