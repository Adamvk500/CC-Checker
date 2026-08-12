import os
import re
import random
import sys
import time
import ssl  
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
import telebot
import pg8000

TOKEN = os.getenv("TELEGRAM_TOKEN", "8661836260:AAF7ZO_uupFJW-wPOv_5P_vVPrggzfE7ySc")
bot = telebot.TeleBot(TOKEN)

def run_fake_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHTTPRequestHandler)
    server.serve_forever()

Thread(target=run_fake_server, daemon=True).start()

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

# 👑 TU NUEVA CONFIGURACIÓN ACTUALIZADA (100% Funcional sin bloqueos)
def get_db_connection():
    contexto_ssl = ssl._create_unverified_context()
    return pg8000.connect(
        host="aws-1-eu-west-1.pooler.supabase.com",
        port=5432,
        database="postgres",
        user="postgres.csagfnnecsfilqlftkfa",
        password="AdamFadlaneLara2021*",
        ssl_context=contexto_ssl  
    )

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id BIGINT PRIMARY KEY,
            alias_elegido TEXT UNIQUE,
            telegram_username TEXT,
            creditos INTEGER DEFAULT 0,
            rango TEXT DEFAULT 'Gratis'
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def verificar_registro(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT alias_elegido, creditos, rango FROM usuarios WHERE id = %s', (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def comprobar_alias_existe(alias):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE alias_elegido = %s', (alias.lower(),))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

def registrar_usuario_manual(user_id, alias, tg_username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO usuarios (id, alias_elegido, telegram_username, creditos) VALUES (%s, %s, %s, 10) ON CONFLICT (id) DO NOTHING', 
                   (user_id, alias.lower(), tg_username))
    conn.commit()
    cursor.close()
    conn.close()

def eliminar_usuario_db(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM usuarios WHERE id = %s', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

def update_user_rank(user_id, nuevo_rango):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET rango = %s WHERE id = %s', (nuevo_rango, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_credits(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT creditos FROM usuarios WHERE id = %s', (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else 0

def update_user_credits(user_id, nuevos_creditos):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET creditos = %s WHERE id = %s', (nuevos_creditos, user_id))
    conn.commit()
    cursor.close()
    conn.close()

# 🛡️ CORREGIDO: Indexación exacta por corchetes del rango para el bypass VIP definitivo
def check_user_access(message, cost=1):
    user_id = message.from_user.id
    current_time = time.time()
    if user_id in LAST_COMMAND_TIME:
        time_passed = current_time - LAST_COMMAND_TIME[user_id]
        if time_passed < 5:
            time_left = 5 - int(time_passed)
            bot.reply_to(message, f"⏳ Calmate! Espera {time_left}s.")
            return False
            
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario:
        bot.reply_to(message, "⚠️ Acceso Denegado. Registrate con /register tu_nombre.")
        return False
    
    creditos = datos_usuario[1]
    rango = datos_usuario[2]  # Extrae la palabra limpia del rango (índice 2)
    
    # 💎 Compara la cadena de texto limpia
    if rango == "VIP":
        LAST_COMMAND_TIME[user_id] = current_time
        return True
        
    if creditos < cost:
        bot.reply_to(message, f"❌ Creditos insuficientes. Tienes: {creditos} monedas.")
        return False
        
    LAST_COMMAND_TIME[user_id] = current_time
    update_user_credits(user_id, creditos - cost)
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

# 👑 NUEVO COMANDO: /setvip (Cambia el rango de un usuario a VIP en Reply)
@bot.message_handler(commands=['setvip'])
def set_user_vip_admin(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513:
        bot.reply_to(message, "❌ No tienes permisos de dueño para otorgar rangos.")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "✏️ <b>Uso correcto:</b> Responde al mensaje del usuario y escribe: <code>/setvip</code>", parse_mode="HTML")
        return

    target_id = message.reply_to_message.from_user.id
    datos_cliente = verificar_registro(target_id)
    if not datos_cliente:
        bot.reply_to(message, "❌ Este usuario no está registrado en el bot.")
        return
        
    alias = datos_cliente[0]
    update_user_rank(target_id, "VIP")
    
    bot.reply_to(message, f"💎 <b>RANGO ACTUALIZADO</b>\n─────────────────────\n👤 Usuario: <code>{alias}</code>\n🔰 Nuevo Rango: <b>🌟 VIP Premium</b>\n⚡ Beneficio: <i>¡Consultas infinitas gratis activadas!</i>", parse_mode="HTML")

# 👑 NUEVO COMANDO: /setgratis (Para quitar el VIP si es necesario en Reply)
@bot.message_handler(commands=['setgratis'])
def remove_user_vip_admin(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if not message.reply_to_message: return
    
    target_id = message.reply_to_message.from_user.id
    datos_cliente = verificar_registro(target_id)
    if datos_cliente:
        update_user_rank(target_id, "Gratis")
        bot.reply_to(message, f"🔰 Rango de <code>{datos_cliente[0]}</code> cambiado de nuevo a <b>Gratis</b>.", parse_mode="HTML")

@bot.message_handler(commands=['delete', 'unregister'])
def delete_user_admin(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513:
        bot.reply_to(message, "❌ No tienes permisos de dueño para eliminar registros.")
        return

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        datos_cliente = verificar_registro(target_id)
        if not datos_cliente:
            bot.reply_to(message, "❌ Este usuario ni siquiera está registrado.")
            return
        eliminar_usuario_db(target_id)
        bot.reply_to(message, f"🗑️ Cuenta de <code>{datos_cliente[0]}</code> eliminada de la base de datos.", parse_mode="HTML")
    else:
        if verificar_registro(user_id):
            eliminar_usuario_db(user_id)
            bot.reply_to(message, "🗑️ Tu cuenta ha sido eliminada con éxito. Ya puedes volver a usar /register.")
        else:
            bot.reply_to(message, "❌ No estás registrado en el sistema.")

@bot.message_handler(commands=['add'])
def add_credits_admin(message):
    user_id = message.from_user.id
    args = message.text.split()
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513:
        bot.reply_to(message, "❌ No tienes permisos para usar este comando.")
        return
        
    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: <code>/add cantidad</code> o respondiendo a un mensaje.", parse_mode="HTML")
        return
        
    try:
        cantidad = int(args[-1])
        target_id = message.reply_to_message.from_user.id if message.reply_to_message else user_id
        
        datos_cliente = verificar_registro(target_id)
        if not datos_cliente:
            bot.reply_to(message, "❌ El usuario objetivo no está registrado.")
            return
            
        alias = datos_cliente[0]
        creditos_viejos = datos_cliente[1]
        nuevos_creditos = creditos_viejos + cantidad
        update_user_credits(target_id, nuevos_creditos)
        bot.reply_to(message, f"🪙 <b>Inyección Exitosa</b>\n─────────────────────\n👤 Usuario: <code>{alias}</code>\n Recargados: +<code>{cantidad}</code> créditos.\n🪙 Total actual: <code>{nuevos_creditos}</code> monedas.", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "❌ Introduce una cantidad numérica válida.")
@bot.message_handler(commands=['register'])
def register_user(message):
    user_id = message.from_user.id
    tg_username = message.from_user.username or 'Usuario'
    args = message.text.split()
    if verificar_registro(user_id):
        bot.reply_to(message, "❌ Ya estas registrado.")
        return
    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: /register tu_nombre")
        return
    alias_deseado = args[-1]
    if not re.match(r'^[\w\d]+$', alias_deseado):
        bot.reply_to(message, "❌ Solo letras y numeros sin espacios.")
        return
    if comprobar_alias_existe(alias_deseado):
        bot.reply_to(message, "⚠️ Ese nombre ya esta ocupado.")
        return
    registrar_usuario_manual(user_id, alias_deseado, tg_username)
    bot.reply_to(message, f"🎉 Registro Exitoso! Bienvenido {alias_deseado.lower()}. Recibiste 10 creditos.")

@bot.message_handler(commands=['credits', 'bal'])
def show_credits(message):
    datos = verificar_registro(message.from_user.id)
    if not datos:
        bot.reply_to(message, "⚠️ Registrate con /register tu_nombre primero.")
        return
    alias = datos[0]
    creditos = datos[1]
    rango = datos[2]
    bot.reply_to(message, f"👤 Usuario: {alias} | 🪙 Creditos: {creditos} | 🔰 Rango: {rango}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    datos = verificar_registro(message.from_user.id)
    if datos:
        alias = datos[0]
        creditos = datos[1]
        rango = datos[2]
        welcome_text = f"👋 Hola de nuevo, {alias}!\n\nSaldo: {creditos} creditos | Rango: {rango}\n\n⚡ /chk CARD\n🎲 /gen BIN\n🔍 /bin BIN"
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
        response = f"🎲 Tarjetas Generadas (BIN: {bin_number})\n\n{cards_output}\n\nSaldo: {get_user_credits(message.from_user.id)[0]} creditos."
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
        response = f"🔍 BIN: {bin_number}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}\nSaldo: {get_user_credits(message.from_user.id)[0]}."
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
        response = f"💳 Card: {cc}|{mes}|{ano}|{cvv}\nEstado: {status}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}\nSaldo: {get_user_credits(message.from_user.id)[0]}"
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

while True:
    try:
        print("Limpiando webhooks...")
        bot.delete_webhook()
        print("Bot Premium Supabase conectado correctamente.")
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
