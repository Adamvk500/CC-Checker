import os
import re
import random
import sys
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN", "8661836260:AAF7ZO_uupFJW-wPOv_5P_vVPrggzfE7ySc")
bot = telebot.TeleBot(TOKEN)

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

# --- COMANDO: /start (BIENVENIDA) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = f"""<b>👋 ¡Hola, @{message.from_user.username or 'Usuario'}! Bienvenido a tu CC Checker Bot</b>

Aquí tienes la lista de comandos disponibles:
⚡ <code>/chk CC|MES|AÑO|CVV</code> ⤿ Revisa el formato y banco de una tarjeta.
🎲 <code>/gen BIN</code> ⤿ Genera 10 tarjetas válidas con un número base (BIN).

<i>Bot alojado con éxito las 24/7 en la nube. 🚀</i>"""
    bot.reply_to(message, welcome_text, parse_mode="HTML")

# --- COMANDO: /gen (GENERADOR DE TARJETAS) ---
@bot.message_handler(regexp=r'(?i)^[!/]gen')
def generate_cards(message):
    try:
        input_data = message.text
        bin_match = re.findall(r'\d+', input_data)
        
        if not bin_match:
            bot.reply_to(message, "❌ <b>Uso correcto:</b> <code>/gen 400022</code>", parse_mode="HTML")
            return
            
        bin_number = bin_match[0]
        if len(bin_number) < 6:
            bot.reply_to(message, "⚠️ El BIN debe tener al menos 6 dígitos.", parse_mode="HTML")
            return

        bin_base = bin_number[:12]
        generated_list = []

        while len(generated_list) < 10:
            cc = bin_base
            while len(cc) < 15:
                cc += str(random.randint(0, 9))
            
            for last_digit in range(10):
                test_cc = cc + str(last_digit)
                if luhn_check(test_cc) and test_cc not in generated_list:
                    mes = str(random.randint(1, 12)).zfill(2)
                    ano = str(random.randint(2026, 2031))
                    cvv = str(random.randint(100, 999))
                    generated_list.append(f"<code>{test_cc}|{mes}|{ano}|{cvv}</code>")
                    break

        cards_output = "\n".join(generated_list)
        response = f"""<b>🎲 Tarjetas Generadas (BIN: {bin_number[:6]})</b>
─────────────────────
{cards_output}
─────────────────────
<b>Generadas por:</b> @{message.from_user.username or 'Usuario'}"""
        
        bot.reply_to(message, response, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error al generar: {str(e)}")

# --- COMANDO PRINCIPAL: /chk (VERIFICADOR) ---
@bot.message_handler(regexp=r'(?i)^[!/]chk')
def check_card(message):
    try:
        input_data = message.text
        cards = re.findall(r'\d+', input_data)
        if len(cards) < 4:
            bot.reply_to(message, "❌ <b>Formato incorrecto.</b>\nUsa: <code>/chk CC|MES|AÑO|CVV</code>", parse_mode="HTML")
            return
        cc, mes, ano, cvv = cards[0], cards[1], cards[2], cards[3]
        if len(cc) < 15 or len(cc) > 16 or len(mes) != 2 or len(cvv) < 3:
            bot.reply_to(message, "❌ <b>Error:</b> Componentes de tarjeta inválidos.", parse_mode="HTML")
            return

        is_luhn_valid = luhn_check(cc)
        status = "🟢 Formato Válido (Luhn Pass)" if is_luhn_valid else "🔴 Formato Inválido (Luhn Fail)"

        bin_number = cc[:6]
        bank_name, country_name, card_type, brand = "Desconocido", "Desconocido", "Desconocido", "Desconocida"

        try:
            # API de BINS corregida con su ruta completa estable
            response_api = requests.get(f"https://payout.com{bin_number}")
            if response_api.status_code == 200:
                data = response_api.json()
                brand = data.get("brand", "Desconocida").capitalize()
                card_type = data.get("type", "Desconocido").capitalize()
                bank_name = data.get("bank", "Desconocido").upper()
                country_name = data.get("country_name", "Desconocido")
        except:
            if cc.startswith('4'): brand = "Visa"
            elif cc.startswith(('51', '52', '53', '54', '55')): brand = "Mastercard"
            elif cc.startswith(('34', '37')): brand = "American Express"

        response = f"""<b>💳 CC Checker Bot v2.5</b>
──────────────────
<b>Card:</b> <code>{cc}|{mes}|{ano}|{cvv}</code>
<b>Estado:</b> {status}
<b>Franquicia:</b> {brand}
<b>Tipo:</b> {card_type}
<b>Banco:</b> {bank_name}
<b>País:</b> {country_name}
──────────────────
<b>Checked by:</b> @{message.from_user.username or 'Usuario'}"""
        bot.reply_to(message, response, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# --- BLOQUE FINAL DE ARRANQUE PARA PLAN GRATUITO EN RENDER ---
try:
    print("Limpiando webhooks y sesiones previas...")
    bot.delete_webhook()
    print("Bot encendido correctamente en el plan gratuito.")
    bot.infinity_polling(skip_pending=True)
except telebot.apihelper.ApiTelegramException as e:
    if e.error_code == 409:
        print("⚠️ Conflicto 409 detectado. Apagando proceso antiguo automáticamente...")
        sys.exit(1)
    else:
        print(f"Error de Telegram: {e}")
except Exception as e:
    print(f"Error general: {e}")
