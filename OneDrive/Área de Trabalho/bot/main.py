import os
import time
import requests
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração da API Binance
api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")
cliente_binance = Client(api_key, secret_key)

SYMBOL = "NEIROUSDT"
ATIVO = "NEIRO"
INTERVALO = Client.KLINE_INTERVAL_1HOUR

# Configuração do Telegram
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Função para enviar mensagens ao Telegram
def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem ao Telegram: {e}")

# Função para exibir saldo
def exibir_saldo():
    try:
        conta = cliente_binance.get_account()
        saldo_usdt = next(item for item in conta["balances"] if item["asset"] == "USDT")["free"]
        saldo_ativo = next(item for item in conta["balances"] if item["asset"] == ATIVO)["free"]
        mensagem = (
            f"💰 **Saldo Atual**:\n"
            f"🔹 USDT: {saldo_usdt}\n"
            f"🔹 {ATIVO}: {saldo_ativo}"
        )
        print(mensagem)
        enviar_telegram(mensagem)
    except Exception as e:
        log_message = f"❌ Erro ao obter saldo: {e}"
        print(log_message)
        enviar_telegram(log_message)

# Função para pegar os dados históricos de candles
def pegar_dados(symbol, intervalo):
    candles = cliente_binance.get_klines(symbol=symbol, interval=intervalo, limit=1000)
    precos = pd.DataFrame(candles)
    precos.columns = ["tempo_abertura", "abertura", "maxima", "minima", "fechamento", "volume", "tempo_fechamento", 
                      "moedas_negociadas", "numero_trades", "volume_ativo_base_compra", "volume_ativo_cotacao", "-"]
    precos = precos[["fechamento", "tempo_fechamento"]]
    precos["fechamento"] = precos["fechamento"].astype(float)
    precos["tempo_fechamento"] = pd.to_datetime(precos["tempo_fechamento"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("America/Sao_Paulo")
    return precos

# Função para calcular as médias móveis
def calcular_medias(dados, periodo_rapido=7, periodo_lento=40):
    dados["media_rapida"] = dados["fechamento"].rolling(window=periodo_rapido).mean()
    dados["media_lenta"] = dados["fechamento"].rolling(window=periodo_lento).mean()
    return dados["media_rapida"].iloc[-1], dados["media_lenta"].iloc[-1]

# Estratégia de trade baseada nas médias móveis
def estrategia_trade(dados, posicao):
    media_rapida, media_lenta = calcular_medias(dados)
    mensagem = (
        f"📉 **Bot Ativo**\n"
        f"───────────────\n"
        f"🔹 **Média Rápida**: {media_rapida:.7f}\n"
        f"🔹 **Média Lenta**: {media_lenta:.7f}\n"
        f"───────────────\n"
        f"⏳ **Aguardando sinal de entrada...**"
    )
    print(mensagem)
    enviar_telegram(mensagem)

    try:
        preco_atual = dados["fechamento"].iloc[-1]
        if media_rapida > media_lenta and not posicao:
            # Simulação de compra
            log_message = f"✅ **Sinal de COMPRA identificado no preço {preco_atual:.2f}.**"
            posicao = True

        elif media_rapida < media_lenta and posicao:
            # Simulação de venda
            log_message = f"✅ **Sinal de VENDA identificado no preço {preco_atual:.2f}.**"
            posicao = False

        print(log_message)
        enviar_telegram(log_message)
    except Exception as e:
        log_message = f"❌ Erro na estratégia: {e}"
        print(log_message)
        enviar_telegram(log_message)

    return posicao

# Inicialização
posicao_aberta = False

# Exibir saldo inicial
exibir_saldo()

# Loop principal do bot
while True:
    try:
        dados = pegar_dados(SYMBOL, INTERVALO)
        posicao_aberta = estrategia_trade(dados, posicao_aberta)
        time.sleep(3600)  # Aguarda 1 hora antes da próxima verificação
    except BinanceAPIException as e:
        log_message = f"❌ Erro na API da Binance: {e}"
        print(log_message)
        enviar_telegram(log_message)
    except Exception as e:
        log_message = f"❌ Erro inesperado: {e}"
        print(log_message)
        enviar_telegram(log_message)
