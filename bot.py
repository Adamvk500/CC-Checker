import os
import re
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

        # --- CONSULTA DE BIN MEJORADA ---
        bin_number = cc[:6]
        bank_name = "Desconocido"
        country_name = "Desconocido"
        card_type = "Desconocido"
        brand = "Desconocida"

        try:
            # Consultamos una API alternativa y más rápida
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

        response = f"""<b>💳 CC Checker Bot v2.1</b>
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

print("Bot encendido correctamente...")
bot.infinity_polling()
