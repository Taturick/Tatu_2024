import pandas as pd
import os
import time
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")
telegram_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")

cliente_binance = Client(api_key, secret_key)

codigo_operado = "NEIROUSDT"
ativo_operado = "NEIRO"
periodo_candle = Client.KLINE_INTERVAL_1HOUR

def exibir_saldo():
    try:
        conta = cliente_binance.get_account()
        saldo_usdt = next(item for item in conta["balances"] if item["asset"] == "USDT")["free"]
        saldo_neiro = next(item for item in conta["balances"] if item["asset"] == ativo_operado)["free"]
        print(f"Saldo Atual em USDT: {saldo_usdt}")
        print(f"Saldo Atual em {ativo_operado}: {saldo_neiro}")
    except Exception as e:
        print(f"Erro ao obter saldo: {e}")

def pegar_precisao_ativo(symbol):
    symbol_info = cliente_binance.get_symbol_info(symbol)
    for filter in symbol_info['filters']:
        if filter['filterType'] == 'LOT_SIZE':
            min_qty = float(filter['minQty'])
            step_size = float(filter['stepSize'])
            return min_qty, step_size
    return 0, 0

def ajustar_quantidade(saldo_usdt, preco_atual, min_qty, step_size):
    quantidade = saldo_usdt / preco_atual
    # Ajusta a quantidade para o mínimo permitido e arredonda para o múltiplo do step_size
    quantidade = max(min_qty, quantidade)
    quantidade = (quantidade // step_size) * step_size
    return round(quantidade, 8)  # Aqui ajusta a precisão para o número correto de casas decimais

def pegar_preco_atual(codigo_ativo):
    ticker = cliente_binance.get_symbol_ticker(symbol=codigo_ativo)
    return float(ticker['price'])

def pegar_dados(codigo, intervalo):
    candles = cliente_binance.get_klines(symbol=codigo, interval=intervalo, limit=1000)
    precos = pd.DataFrame(candles)
    precos.columns = ["tempo_abertura", "abertura", "maxima", "minima", "fechamento", "volume", "tempo_fechamento", 
                      "moedas_negociadas", "numero_trades", "volume_ativo_base_compra", "volume_ativo_cotacao", "-"]
    precos = precos[["fechamento", "tempo_fechamento"]]
    precos["tempo_fechamento"] = pd.to_datetime(precos["tempo_fechamento"], unit="ms").dt.tz_localize("UTC")
    precos["tempo_fechamento"] = precos["tempo_fechamento"].dt.tz_convert("America/Sao_Paulo")

    return precos

def estrategia_trade(dados, codigo_ativo, ativo_operado, posicao):
    dados["media_rapida"] = dados["fechamento"].rolling(window=7).mean()
    dados["media_devagar"] = dados["fechamento"].rolling(window=40).mean()

    ultima_media_rapida = dados["media_rapida"].iloc[-1]
    ultima_media_devagar = dados["media_devagar"].iloc[-1]

    print(f"Última Média Rápida: {ultima_media_rapida} | Última Média Devagar: {ultima_media_devagar}")

    try:
        conta = cliente_binance.get_account()
        saldo_usdt = float(next(item for item in conta["balances"] if item["asset"] == "USDT")["free"])
        saldo_neiro = float(next(item for item in conta["balances"] if item["asset"] == ativo_operado)["free"])

        preco_atual = pegar_preco_atual(codigo_ativo)

        # Pega as restrições de quantidade mínima e step size
        min_qty, step_size = pegar_precisao_ativo(codigo_ativo)

        if ultima_media_rapida > ultima_media_devagar:
            if not posicao:
                quantidade = ajustar_quantidade(saldo_usdt, preco_atual, min_qty, step_size)
                if quantidade > 0:  # Verifica se a quantidade calculada é válida
                    order = cliente_binance.create_order(
                        symbol=codigo_ativo,
                        side=SIDE_BUY,
                        type=ORDER_TYPE_MARKET,
                        quantity=quantidade
                    )
                    print(f"COMPROU {quantidade} {ativo_operado}")
                    exibir_saldo()  # Atualiza e exibe o saldo após a compra
                    posicao = True

        elif ultima_media_rapida < ultima_media_devagar:
            if posicao and saldo_neiro > 0:
                quantidade = ajustar_quantidade(saldo_neiro, preco_atual, min_qty, step_size)
                if quantidade > 0:  # Verifica se a quantidade calculada é válida
                    order = cliente_binance.create_order(
                        symbol=codigo_ativo,
                        side=SIDE_SELL,
                        type=ORDER_TYPE_MARKET,
                        quantity=quantidade
                    )
                    print(f"VENDEU {quantidade} {ativo_operado}")
                    exibir_saldo()  # Atualiza e exibe o saldo após a venda
                    posicao = False

    except Exception as e:
        print(f"Erro na estratégia: {e}")

    return posicao

posicao_atual = False

# Exibe saldo inicial
print("Obtendo saldo inicial...")
exibir_saldo()

while True:
    dados_atualizados = pegar_dados(codigo=codigo_operado, intervalo=periodo_candle)
    posicao_atual = estrategia_trade(dados_atualizados, codigo_ativo=codigo_operado, 
                                     ativo_operado=ativo_operado, posicao=posicao_atual)
    time.sleep(60)  # Aguarda 1 minuto antes de rodar novamente
