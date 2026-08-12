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

USER_CREDITS = {}      
LAST_COMMAND_TIME = {} 

LOCAL_BINS = {
    # --- ESPAÑA ---
    "491566": {"brand": "Visa", "type": "Credit", "bank": "BANCO SANTANDER", "country": "Spain", "flag": "🇪🇸"},
    "454812": {"brand": "Visa", "type": "Debit", "bank": "BBVA", "country": "Spain", "flag": "🇪🇸"},
    "540624": {"brand": "Mastercard", "type": "Credit", "bank": "CAIXABANK", "country": "Spain", "flag": "🇪🇸"},
    "522205": {"brand": "Mastercard", "type": "Debit", "bank": "PECUNPAY EDE", "country": "Spain", "flag": "🇪🇸"},
    "450793": {"brand": "Visa", "type": "Debit", "bank": "BANCO SABADELL", "country": "Spain", "flag": "🇪🇸"},
    "514039": {"brand": "Mastercard", "type": "Credit", "bank": "ING DIRECT", "country": "Spain", "flag": "🇪🇸"},
    "406561": {"brand": "Visa", "type": "Debit", "bank": "OPENBANK", "country": "Spain", "flag": "🇪🇸"},
    "552251": {"brand": "Mastercard", "type": "Debit", "bank": "REVOLUT", "country": "Spain", "flag": "🇪🇸"},
    # --- COLOMBIA ---
    "418731": {"brand": "Visa", "type": "Debit", "bank": "BANCOLOMBIA", "country": "Colombia", "flag": "🇨🇴"},
    "530691": {"brand": "Mastercard", "type": "Credit", "bank": "BANCO DE BOGOTA", "country": "Colombia", "flag": "🇨🇴"},
    "421319": {"brand": "Visa", "type": "Debit", "bank": "DAVIVIENDA", "country": "Colombia", "flag": "🇨🇴"},
    # --- MÉXICO ---
    "455655": {"brand": "Visa", "type": "Debit", "bank": "BBVA BANCOMER", "country": "Mexico", "flag": "🇲🇽"},
    "520416": {"brand": "Mastercard", "type": "Credit", "bank": "BANAMEX", "country": "Mexico", "flag": "🇲🇽"},
    # --- ESTADOS UNIDOS ---
    "400022": {"brand": "Visa", "type": "Credit", "bank": "CHASE BANK", "country": "United States", "flag": "🇺🇸"},
    "510510": {"brand": "Mastercard", "type": "Credit", "bank": "CAPITAL ONE", "country": "United States", "flag": "🇺🇸"},
    "541275": {"brand": "Mastercard", "type": "Credit", "bank": "CITIBANK", "country": "United States", "flag": "🇺🇸"},
    # --- ARGENTINA ---
    "400000": {"brand": "Visa", "type": "Debit", "bank": "SANTANDER RIO", "country": "Argentina", "flag": "🇦🇷"}
}

def luhn_check(card_number):
    total = 0
    reverse_digits = card_number[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

def get_user_credits(user_id):
    if user_id not in USER_CREDITS:
        USER_CREDITS[user_id] = 10
    return USER_CREDITS[user_id]

def check_antiflood_and_credits(message, cost=1):
    user_id = message.from_user.id
    current_time = time.time()
    
    if user_id in LAST_COMMAND_TIME:
        time_passed = current_time - LAST_COMMAND_TIME[user_id]
        if time_passed < 5:
            time_left = 5 - int(time_passed)
            bot.reply_to(message, f"⏳ <b>¡Cálmate!</b> Debes esperar <code>{time_left}s</code> antes de usar otro comando.", parse_mode="HTML")
            return False

    credits = get_user_credits(user_id)
    if credits < cost:
        bot.reply_to(message, f"❌ <b>Créditos insuficientes.</b>\nTienes: <code>{credits}</code> créditos.\n<i>Necesitas al menos {cost} crédito para esta acción.</i>", parse_mode="HTML")
        return False
        
    LAST_COMMAND_TIME[user_id] = current_time
    USER_CREDITS[user_id] -= cost
    return True

@bot.message_handler(commands=['add'])
def add_credits_admin(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "✏️ Uso: <code>/add @username_o_id cantidad</code>", parse_mode="HTML")
            return
            
        amount = int(args[-1])
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            USER_CREDITS[target_id] = get_user_credits(target_id) + amount
            bot.reply_to(message, f"🪙 Añadidos <code>{amount}</code> créditos al usuario.", parse_mode="HTML")
        else:
            bot.reply_to(message, "💡 Responde al mensaje de un usuario con este comando para añadirle créditos.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['credits', 'bal'])
def show_credits(message):
    credits = get_user_credits(message.from_user.id)
    bot.reply_to(message, f"🪙 <b>Tus Créditos Disponibles:</b> <code>{credits}</code>\n<i>Cada consulta cuesta 1 crédito.</i>", parse_mode="HTML")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    credits = get_user_credits(message.from_user.id)
    welcome_text = f"""<b>👋 ¡Hola, @{message.from_user.username or 'Usuario'}! Bienvenido a tu CC Checker Premium</b>

Aquí tienes la lista de comandos disponibles:
⚡ <code>/chk CC|MES|AÑO|CVV</code> ⤿ Revisa una tarjeta (Cuesta 1 🪙).
🎲 <code>/gen BIN</code> ⤿ Genera 10 CCs válidas (Cuesta 1 🪙).
🔍 <code>/bin BIN</code> ⤿ Consulta avanzada de banco (Cuesta 1 🪙).
🪙 <code>/credits</code> ⤿ Mira tu saldo de créditos actual.

<b>Tu saldo actual:</b> <code>{credits}</code> créditos gratis. 💎
<i>Ataques de spam protegidos con Antiflood de 5s. 🛡️</i>"""
    bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(regexp=r'(?i)^[!/]gen')
def generate_cards(message):
    if not check_antiflood_and_credits(message, cost=1): return
    try:
        input_data = message.text
        bin_match = re.findall(r'\d+', input_data)
        if not bin_match:
            bot.reply_to(message, "❌ <b>Uso correcto:</b> <code>/gen 400022</code>", parse_mode="HTML")
            return
        
        bin_number = "".join(bin_match)[:6]
        if len(bin_number) < 6:
            bot.reply_to(message, "⚠️ El BIN debe tener al menos 6 dígitos.", parse_mode="HTML")
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
                    generated_list.append(f"<code>{test_cc}|{mes}|{ano}|{cvv}</code>")
                    break

        cards_output = "\n".join(generated_list)
        response = f"""<b>🎲 Tarjetas Generadas (BIN: {bin_number})</b>
─────────────────────
{cards_output}
─────────────────────
<b>Restante:</b> <code>{USER_CREDITS[message.from_user.id]}</code> 🪙"""
        bot.reply_to(message, response, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error al generar: {str(e)}")

@bot.message_handler(regexp=r'(?i)^[!/]bin')
def check_bin_standalone(message):
    if not check_antiflood_and_credits(message, cost=1): return
    try:
        input_data = message.text
        bin_match = re.findall(r'\d+', input_data)
        if not bin_match:
            bot.reply_to(message, "❌ <b>Uso correcto:</b> <code>/bin 400022</code>", parse_mode="HTML")
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
            card_type, bank_name, country_name, flag = "Desconocido", "BANCO GENÉRICO", "Desconocido", "🏳️‍🌈"

        response = f"""<b>🔍 Información del BIN [<code>{bin_number}</code>]</b>
──────────────────
<b>Franquicia:</b> <code>{brand}</code>
<b>Tipo:</b> <code>{card_type}</code>
<b>Banco:</b> <code>{bank_name}</code>
<b>País:</b> {country_name} {flag}
──────────────────
<b>Restante:</b> <code>{USER_CREDITS[message.from_user.id]}</code> 🪙"""
            
        bot.reply_to(message, response, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error BIN: {str(e)}")

@bot.message_handler(regexp=r'(?i)^[!/]chk')
def check_card(message):
    if not check_antiflood_and_credits(message, cost=1): return
    try:
        input_data = message.text
        cards = re.findall(r'\d+', input_data)
        if len(cards) < 4:
            bot.reply_to(message, "❌ <b>Formato incorrecto.</b>\nUsa: <code>/chk CC|MES|AÑO|CVV</code>", parse_mode="HTML")
            return
            
        cc, mes, ano, cvv = cards[0], cards[1], cards[2], cards[3]

        is_luhn_valid = luhn_check(cc)
        status = "🟢 Formato Válido (Luhn Pass)" if is_luhn_valid else "🔴 Formato Inválido (Luhn Fail)"

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
            card_type, bank_name, country_name, flag = "Desconocido", "BANCO GENÉRICO", "Desconocido", "🏳️‍🌈"

        response = f"""<b>💳 CC Checker Bot Premium v3.0</b>
──────────────────
<b>Card:</b> <code>{cc}|{mes}|{ano}|{cvv}</code>
<b>Estado:</b> {status}
<b>Franquicia:</b> {brand}
<b>Tipo:</b> <code>{card_type}</code>
<b>Banco:</b> <code>{bank_name}</code>
<b>País:</b> {country_name} {flag}
──────────────────
<b>Saldo Restante:</b> <code>{USER_CREDITS[message.from_user.id]}</code> 🪙"""
        bot.reply_to(message, response, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

while True:
    try:
        print("Limpiando webhooks y sesiones previas...")
        bot.delete_webhook()
        print("Bot Premium encendido correctamente.")
        bot.infinity_polling(skip_pending=True)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409:
            print("⚠️ Conflicto detectado de procesos. Esperando 10 segundos...")
            time.sleep(10)
        else:
            print(f"Error de Telegram: {e}")
            time.sleep(5)
    except Exception as e:
        print(f"Error general: {e}")
        time.sleep(5)
