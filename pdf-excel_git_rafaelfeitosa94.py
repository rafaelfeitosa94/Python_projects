import os
import io
import base64
from pdf2image import convert_from_path
import google.generativeai as genai
import pandas as pd
import json
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import google.generativeai as genai
import datetime
from datetime import datetime, timedelta
import os
import shutil

folder = "{caminho da pasta do arquivo}"
destination_folder = "{pasta de destino do arquivo (pra onde vai ser enviado após a formatação)}"

presentday = datetime.now()
yesterday = presentday - timedelta(1)
last_week = presentday - timedelta(7)

# ======================
# CONFIGURAÇÕES
# ======================
# Caminho do arquivo JSON da service account
SERVICE_ACCOUNT_FILE = r"{json da api key extraido do google is studio}"

# Escopo da API
SCOPES = ["https://www.googleapis.com/auth/generative-language"]

# Autenticação automática
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
credentials.refresh(Request())
# 🔑 Coloque sua chave da API Gemini
genai.configure(credentials=credentials)

pdf_path = r"{caminho completo do arquivo em pdf}"
poppler_path = r"{caminho do seu Poppler}"
restaurante = "{nome do restaurante}"

# Modelo Gemini com visão (1.5 Pro recomendado)
model = genai.GenerativeModel("gemini-2.5-flash")

# ======================
# CONVERTER PDF → IMAGENS
# ======================
print("📄 Convertendo PDF para imagens...")
pages = convert_from_path(pdf_path, dpi=200, poppler_path=poppler_path)

dados = []

# ======================
# PROCESSAR CADA PÁGINA
# ======================
for i, page in enumerate(pages, start=1):
    print(f"🔍 Processando página {i}/{len(pages)}...")

    # Converter imagem para bytes
    img_bytes = io.BytesIO()
    page.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # Enviar imagem para o modelo Gemini
    prompt = f"""
Extraia todos os itens deste cardápio e devolva o resultado em JSON no formato:
[
  {{
    "restaurante": "{restaurante}",
    "categoria": "nome da categoria",
    "produto": "nome do prato",
    "preco": "valor (somente número e vírgula)",
    "descricao": "descrição do prato, se houver"
  }}
]

Regras:
- Use o português exatamente como aparece.
- Se houver dois preços (meia / inteira), use o maior.
- Não adicione texto fora do JSON.
    """

    response = model.generate_content(
        [prompt, {"mime_type": "image/png", "data": img_bytes.getvalue()}]
    )

    # Tentar extrair JSON puro
    try:
        text = response.text.strip()
        # Corrigir respostas com blocos de código
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        json_data = json.loads(text)
        dados.extend(json_data)
    except Exception as e:
        print(f"⚠️ Erro ao converter página {i}: {e}")
        print(response.text[:400])

# ======================
# EXPORTAR PARA EXCEL
# ======================
df = pd.DataFrame(dados)
output_file = "{nome do arquido a ser gerado + .xlsx}"
df.to_excel(output_file, index=False)

print(f"✅ Planilha gerada com sucesso: {output_file}")
print(df.head(10))

filename = max([os.path.join(folder, f) for f in os.listdir(folder)], key=os.path.getctime)
cf = shutil.move(filename,os.path.join(folder, f"cf_{yesterday.strftime('%Y-%m-%d')}.xlsx"))
destination_path = os.path.join(destination_folder, f"cf_{yesterday.strftime('%Y-%m-%d')}.xlsx")

shutil.move(cf, destination_path)
print(cf)
