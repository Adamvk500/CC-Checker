import os
import re
import random
import sys
import time
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN", "8661836260:AAF7ZO_uupFJW-wPOv_5P_vVPrggzfE7ySc")
bot = telebot.TeleBot(TOKEN)

def run_fake_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHTTPRequestHandler)
    server.serve_forever()

Thread(target=run_fake_server, daemon=True).start()

# --- BASE DE DATOS EN LA NUBE ---
ADMIN_DB_ID = 5203992513  

USER_ALIAS = {}    
USER_CREDITS = {}  
USER_RANK = {}     
KEYS_DATABASE = {} 

LAST_COMMAND_TIME = {} 

LOCAL_BINS = {
    "522205": {"brand": "Mastercard", "type": "Debit", "bank": "IMAGIN", "country": "Spain", "flag": "🇪🇸"},
    "491566": {"brand": "Visa", "type": "Credit", "bank": "BANCO SANTANDER", "country": "Spain", "flag": "🇪🇸"},
    "454812": {"brand": "Visa", "type": "Debit", "bank": "BBVA", "country": "Spain", "flag": "🇪🇸"},
    "540624": {"brand": "Mastercard", "type": "Credit", "bank": "CAIXABANK", "country": "Spain", "flag": "🇪🇸"},
    "400022": {"brand": "Visa", "type": "Credit", "bank": "CHASE BANK", "country": "United States", "flag": "🇺🇸"},
    "510510": {"brand": "Mastercard", "type": "Credit", "bank": "CAPITAL ONE", "country": "United States", "flag": "🇺🇸"},
    "418731": {"brand": "Visa", "type": "Debit", "bank": "BANCOLOMBIA", "country": "Colombia", "flag": "🇨🇴"}
}

def sincronizar_desde_telegram():
    print("Sincronizando base de datos desde Telegram...")
    try:
        updates = bot.get_chat_history(ADMIN_DB_ID, limit=5000)
        for msg in reversed(list(updates)):
            if msg.text:
                if msg.text.startswith("REGISTRO"):
                    partes = msg.text.split("|")
                    uid = int(partes[1])
                    alias = partes[2]
                    USER_ALIAS[uid] = alias
                    if uid not in USER_CREDITS: USER_CREDITS[uid] = 10
                    if uid not in USER_RANK: USER_RANK[uid] = "Gratis"
                
                elif msg.text.startswith("CREDITOS"):
                    partes = msg.text.split("|")
                    uid = int(partes[1])
                    creditos = int(partes[2])
                    USER_CREDITS[uid] = creditos
                
                elif msg.text.startswith("KEYCREADA"):
                    partes = msg.text.split("|")
                    key = partes[1]
                    valor = int(partes[2])
                    KEYS_DATABASE[key] = valor
                
                elif msg.text.startswith("KEYUSADA"):
                    partes = msg.text.split("|")
                    key = partes[1]
                    if key in KEYS_DATABASE:
                        del KEYS_DATABASE[key]
        print("Sincronizacion completada con exito.")
    except Exception as e:
        print(f"Aviso en sincronizacion: {e}")

def respaldar_registro(user_id, alias):
    USER_ALIAS[user_id] = alias
    USER_CREDITS[user_id] = 10
    USER_RANK[user_id] = "Gratis"
    try:
        bot.send_message(ADMIN_DB_ID, f"REGISTRO|{user_id}|{alias.lower()}")
    except: pass

def respaldar_creditos(user_id, creditos):
    USER_CREDITS[user_id] = creditos
    try:
        bot.send_message(ADMIN_DB_ID, f"CREDITOS|{user_id}|{creditos}")
    except: pass

def respaldar_nueva_key(key_code, cantidad):
    KEYS_DATABASE[key_code] = cantidad
    try:
        bot.send_message(ADMIN_DB_ID, f"KEYCREADA|{key_code}|{cantidad}")
    except: pass

def respaldar_key_usada(key_code):
    if key_code in KEYS_DATABASE:
        del KEYS_DATABASE[key_code]
    try:
        bot.send_message(ADMIN_DB_ID, f"KEYUSADA|{key_code}")
    except: pass

def check_user_access(message, cost=1):
    user_id = message.from_user.id
    current_time = time.time()
    
    if user_id in LAST_COMMAND_TIME:
        time_passed = current_time - LAST_COMMAND_TIME[user_id]
        if time_passed < 5:
            time_left = 5 - int(time_passed)
            bot.reply_to(message, f"⏳ Calmate! Espera {time_left}s.")
            return False

    if user_id not in USER_ALIAS:
        bot.reply_to(message, "⚠️ Acceso Denegado. Registrate con /register tu_nombre para obtener 10 creditos.")
        return False
        
    creditos = USER_CREDITS.get(user_id, 0)
    if creditos < cost:
        bot.reply_to(message, f"❌ Creditos insuficientes. Tienes: {creditos} monedas.")
        return False
        
    LAST_COMMAND_TIME[user_id] = current_time
    respaldar_creditos(user_id, creditos - cost)
    return True

def luhn_check(card_number):
    total = 0
    reverse_digits = card_number[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9: n -= 9
        total += n
    return total % 10 == 0
@bot.message_handler(commands=['register'])
def register_user(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if user_id in USER_ALIAS:
        bot.reply_to(message, "❌ Ya estas registrado.")
        return
        
    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: /register tu_nombre")
        return
        
    # Corregido: Indexacion correcta [1] para leer strings
    alias_deseado = args[1].lower()
    
    if not re.match(r'^[\w\d]+$', alias_deseado):
        bot.reply_to(message, "❌ Solo letras y numeros sin espacios.")
        return

    if alias_deseado in USER_ALIAS.values():
        bot.reply_to(message, "⚠️ Ese nombre ya esta ocupado.")
        return
        
    respaldar_registro(user_id, alias_deseado)
    bot.reply_to(message, f"🎉 Registro Exitoso! Bienvenido {alias_deseado}. Recibiste 10 creditos.")

@bot.message_handler(commands=['keygen'])
def generate_key_admin(message):
    args = message.text.split()
    
    if message.from_user.username != "Adam_vk_500" and message.from_user.id != ADMIN_DB_ID:
        bot.reply_to(message, "❌ No tienes permisos de administrador.")
        return

    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: /keygen cantidad_de_creditos")
        return

    try:
        # Corregido: Indexacion correcta [1] para leer enteros
        cantidad = int(args[1])
        import string
        chars = string.ascii_uppercase + string.digits
        codigo_random = "ADAM-" + "".join(random.choice(chars) for _ in range(12))
        
        respaldar_nueva_key(codigo_random, cantidad)
        
        texto_admin = f"🔑 <b>KEY GENERADA CON ÉXITO</b>\n─────────────────────\n<b>Código:</b> <code>{codigo_random}</code>\n<b>Valor:</b> <code>{cantidad}</code> créditos 🪙\n─────────────────────\n<i>Puedes poner este código a la venta.</i>"
        bot.reply_to(message, texto_admin, parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "❌ Introduce un numero valido.")

@bot.message_handler(commands=['claim'])
def claim_key_user(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if user_id not in USER_ALIAS:
        bot.reply_to(message, "⚠️ Debes registrarte primero usando /register tu_nombre")
        return

    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: /claim ADAM-CODIGO")
        return

    # Corregido: Indexacion correcta [1] para leer codigos
    key_solicitada = args[1].upper()
    
    if key_solicitada in KEYS_DATABASE:
        creditos_ganados = KEYS_DATABASE[key_solicitada]
        respaldar_key_usada(key_solicitada)
        
        creditos_viejos = USER_CREDITS.get(user_id, 0)
        nuevos_creditos = creditos_viejos + credited_ganados if 'credited_ganados' in locals() else creditos_viejos + creditos_ganados
        respaldar_creditos(user_id, nuevos_creditos)
        
        alias = USER_ALIAS[user_id]
        texto_exito = f"🎉 <b>¡Código Reclamado!</b>\n\n👤 Usuario: <code>{alias}</code>\n Recargados: +<code>{creditos_ganados}</code> créditos.\n🪙 Total actual: <code>{nuevos_creditos}</code> monedas."
        bot.reply_to(message, texto_exito, parse_mode="HTML")
    else:
        bot.reply_to(message, "❌ Código inválido o ya utilizado.")

@bot.message_handler(commands=['credits', 'bal'])
def show_credits(message):
    user_id = message.from_user.id
    if user_id not in USER_ALIAS:
        bot.reply_to(message, "⚠️ Registrate con /register tu_nombre primero.")
        return
    alias = USER_ALIAS[user_id]
    creditos = USER_CREDITS.get(user_id, 0)
    rango = USER_RANK.get(user_id, "Gratis")
    bot.reply_to(message, f"👤 Usuario: {alias} | 🪙 Creditos: {creditos} | 🔰 Rango: {rango}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id in USER_ALIAS:
        alias = USER_ALIAS[user_id]
        creditos = USER_CREDITS.get(user_id, 0)
        rango = USER_RANK.get(user_id, "Gratis")
        welcome_text = f"👋 Hola de nuevo, {alias}!\n\nSaldo: {creditos} creditos | Rango: {rango}\n\n⚡ /chk CARD\n🎲 /gen BIN\n🔍 /bin BIN\n🔑 Recargar: /claim CODIGO"
    else:
        welcome_text = "👋 Bienvenido!\n\n🔑 Registrate de forma manual para usar el bot.\n\n✏️ Escribe: /register tu_nombre"
    bot.reply_to(message, welcome_text)

@bot.message_handler(regexp=r'(?i)^[!/]gen')
def generate_cards(message):
    if not check_user_access(message, cost=1): return
    try:
        input_data = message.text
        bin_match = re.findall(r'\d+', input_data)
        if not bin_match:
            bot.reply_to(message, "❌ Uso correcto: /gen 400022")
            return
        bin_number = "".join(bin_match)[:6]
        if len(bin_number) < 6:
            bot.reply_to(message, "⚠️ El BIN debe tener al menos 6 digitos.")
            return
        bin_base = bin_number
        generated_list = []
        while len(generated_list) < 10:
            cc = bin_base
            while len(cc) < 15: cc += str(random.randint(0, 9))
            for last_digit in range(10):
                test_cc = cc + str(last_digit)
                if luhn_check(test_cc) and test_cc not in generated_list:
                    mes = str(random.randint(1, 12)).zfill(2)
                    ano = str(random.randint(2026, 2031))
                    cvv = str(random.randint(100, 999))
                    generated_list.append(f"{test_cc}|{mes}|{ano}|{cvv}")
                    break
        cards_output = "\n".join(generated_list)
        response = f"🎲 Tarjetas Generadas (BIN: {bin_number})\n\n{cards_output}\n\nSaldo: {USER_CREDITS.get(message.from_user.id, 0)} creditos."
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error al generar: {str(e)}")

@bot.message_handler(regexp=r'(?i)^[!/]bin')
def check_bin_standalone(message):
    if not check_user_access(message, cost=1): return
    try:
        input_data = message.text
        bin_match = re.findall(r'\d+', input_data)
        if not bin_match:
            bot.reply_to(message, "❌ Uso correcto: /bin 400022")
            return
        bin_number = "".join(bin_match)[:6]
        bot.send_chat_action(message.chat.id, 'typing')
        if bin_number in LOCAL_BINS:
            bin_data = LOCAL_BINS[bin_number]
            brand = bin_data["brand"]
            card_type = bin_data["type"]
            bank_name = bin_data["bank"]
            country_name = bin_data["country"]
            flag = bin_data["flag"]
        else:
            brand = "Visa" if bin_number.startswith('4') else "Mastercard" if bin_number.startswith('5') else "Desconocida"
            card_type, bank_name, country_name, flag = "Desconocido", "BANCO GENERICO", "Desconocido", "🏳️‍🌈"
        response = f"🔍 BIN: {bin_number}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}\nSaldo: {USER_CREDITS.get(message.from_user.id, 0)}."
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(regexp=r'(?i)^[!/]chk')
def check_card(message):
    if not check_user_access(message, cost=1): return
    try:
        input_data = message.text
        cards = re.findall(r'\d+', input_data)
        if len(cards) < 4:
            bot.reply_to(message, "❌ Uso correcto: /chk CARD")
            return
        cc, mes, ano, cvv = cards[0], cards[1], cards[2], cards[3]
        is_luhn_valid = luhn_check(cc)
        status = "🟢 Valida" if is_luhn_valid else "🔴 Invalida"
        bin_number = cc[:6]
        if bin_number in LOCAL_BINS:
            bin_data = LOCAL_BINS[bin_number]
            brand = bin_data["brand"]
            card_type = bin_data["type"]
            bank_name = bin_data["bank"]
            country_name = bin_data["country"]
            flag = bin_data["flag"]
        else:
            brand = "Visa" if bin_number.startswith('4') else "Mastercard" if bin_number.startswith('5') else "Desconocida"
            card_type, bank_name, country_name, flag = "Desconocido", "BANCO GENERICO", "Desconocido", "🏳️‍🌈"
        response = f"💳 Card: {cc}|{mes}|{ano}|{cvv}\nEstado: {status}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}\nSaldo: {USER_CREDITS.get(message.from_user.id, 0)}"
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

while True:
    try:
        print("Limpiando webhooks...")
        bot.delete_webhook()
        sincronizar_desde_telegram()
        print("Bot Premium Nube encendido correctamente.")
        bot.infinity_polling(skip_pending=True)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409:
            print("⚠️ Conflicto de procesos. Esperando 10 segundos...")
            time.sleep(10)
        else:
            print(f"Error de Telegram: {e}")
            time.sleep(5)
    except Exception as e:
        print(f"Error general: {e}")
        time.sleep(5)
