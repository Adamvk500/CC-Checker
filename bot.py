import os
import re
import random
import sys
import time
import sqlite3
import string
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
import telebot

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

DB_FILE = "usuarios.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Tabla de usuarios de la Fase anterior
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            alias_elegido TEXT UNIQUE,
            telegram_username TEXT,
            creditos INTEGER DEFAULT 0,
            rango TEXT DEFAULT 'Gratis'
        )
    ''')
    # NUEVA: Tabla para almacenar los codigos de saldo recargables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key_code TEXT PRIMARY KEY,
            creditos_valor INTEGER,
            estado TEXT DEFAULT 'Disponible'
        )
    ''')
    conn.commit()
    conn.close()

init_db()
def verificar_registro(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT alias_elegido, creditos, rango FROM usuarios WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def comprobar_alias_existe(alias):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE alias_elegido = ?', (alias.lower(),))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def registrar_usuario_manual(user_id, alias, tg_username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO usuarios (id, alias_elegido, telegram_username, creditos) VALUES (?, ?, ?, ?)', 
                   (user_id, alias.lower(), tg_username, 10))
    conn.commit()
    conn.close()

def get_user_credits(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT creditos FROM usuarios WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else 0

def update_user_credits(user_id, nuevos_creditos):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET creditos = ? WHERE id = ?', (nuevos_creditos, user_id))
    conn.commit()
    conn.close()

# Funciones de base de datos exclusivas para el sistema de llaves de pago
def db_guardar_key(codigo, cantidad):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO keys (key_code, creditos_valor) VALUES (?, ?)', (codigo, cantidad))
    conn.commit()
    conn.close()

def db_reclamar_key(codigo):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT creditos_valor, estado FROM keys WHERE key_code = ?', (codigo,))
    result = cursor.fetchone()
    if result and result[1] == 'Disponible':
        cursor.execute('UPDATE keys SET estado = "Reclamada" WHERE key_code = ?', (codigo,))
        conn.commit()
        conn.close()
        return result[0] # Retorna el numero de creditos que vale la key
    conn.close()
    return None

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
        bot.reply_to(message, "⚠️ Acceso Denegado. Registrate con /register tu_nombre para obtener 10 creditos.")
        return False
        
    alias, creditos, rango = datos_usuario

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
# --- COMANDO EXCLUSIVO: /keygen CANTIDAD ---
@bot.message_handler(commands=['keygen'])
def generate_key_admin(message):
    args = message.text.split()
    
    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: <code>/keygen cantidad_de_creditos</code>", parse_mode="HTML")
        return

    try:
        # CORREGIDO: Extraer el número correctamente de la lista
        cantidad = int(args[1])
        
        # Generar un codigo aleatorio seguro de 12 letras y numeros
        chars = string.ascii_uppercase + string.digits
        codigo_random = "ADAM-" + "".join(random.choice(chars) for _ in range(12))
        
        db_guardar_key(codigo_random, cantidad)
        
        texto_admin = f"🔑 <b>KEY GENERADA CON ÉXITO</b>\n─────────────────────\n<b>Código:</b> <code>{codigo_random}</code>\n<b>Valor:</b> <code>{cantidad}</code> créditos 🪙\n─────────────────────\n<i>Puedes poner este código a la venta. El usuario que lo use recibirá los créditos al instante.</i>"
        bot.reply_to(message, texto_admin, parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "❌ Por favor, introduce un numero valido de creditos.")

# --- COMANDO PÚBLICO: /claim CODIGO ---
@bot.message_handler(commands=['claim'])
def claim_key_user(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    datos = verificar_registro(user_id)
    if not datos:
        bot.reply_to(message, "⚠️ Debes registrarte primero usando <code>/register tu_nombre</code>", parse_mode="HTML")
        return

    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: <code>/claim ADAM-CODIGO_SECRETO</code>", parse_mode="HTML")
        return

    key_solicitada = args[1].upper()
    creditos_ganados = db_reclamar_key(key_solicitada)

    if creditos_ganados:
        alias, creditos_viejos, rango = datos
        nuevos_creditos = creditos_viejos + creditos_ganados
        update_user_credits(user_id, nuevos_creditos)
        
        texto_exito = f"🎉 <b>¡Código Reclamado!</b>\n\n👤 Usuario: <code>{alias}</code>\n Recargados: +<code>{creditos_ganados}</code> créditos.\n🪙 Total actual: <code>{nuevos_creditos}</code> monedas."
        bot.reply_to(message, texto_exito, parse_mode="HTML")
    else:
        bot.reply_to(message, "❌ <b>Código inválido o ya utilizado.</b>")

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
    alias_deseado = args[1]
    if not re.match(r'^[\w\d]+$', alias_deseado):
        bot.reply_to(message, "❌ Solo letras y numeros sin espacios.")
        return
    if comprobar_alias_existe(alias_deseado):
        bot.reply_to(message, "⚠️ Ese nombre ya esta ocupado.")
        return
        
    registrar_usuario_manual(user_id, alias_deseado, tg_username)
    bot.reply_to(message, f"🎉 Registro Exitoso! Bienvenido {alias_deseado.lower()}. Recibiste 10 creditos.")

@bot.message_handler(commands=['add'])
def add_credits_admin(message):
    try:
        args = message.text.split()
        if len(args) < 2 or not message.reply_to_message:
            bot.reply_to(message, "✏️ Responde al mensaje de alguien y escribe: /add cantidad")
            return
        amount = int(args[-1])
        target_id = message.reply_to_message.from_user.id
        datos = verificar_registro(target_id)
        if not datos:
            bot.reply_to(message, "❌ El usuario no esta registrado.")
            return
        nuevos_creditos = datos[1] + amount
        update_user_credits(target_id, nuevos_creditos)
        bot.reply_to(message, f"🪙 Añadidos {amount} creditos.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['credits', 'bal'])
def show_credits(message):
    datos = verificar_registro(message.from_user.id)
    if not datos:
        bot.reply_to(message, "⚠️ Registrate con /register tu_nombre primero.")
        return
    bot.reply_to(message, f"👤 Usuario: {datos[0]} | 🪙 Creditos: {datos[1]} | 🔰 Rango: {datos[2]}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    datos = verificar_registro(message.from_user.id)
    if datos:
        welcome_text = f"👋 Hola de nuevo, {datos[0]}!\n\nSaldo: {datos[1]} creditos | Rango: {datos[2]}\n\n⚡ /chk CARD\n🎲 /gen BIN\n🔍 /bin BIN\n🔑 Recargar: /claim CODIGO"
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
        response = f"🎲 Tarjetas Generadas (BIN: {bin_number})\n\n{cards_output}\n\nSaldo: {get_user_credits(message.from_user.id)} creditos."
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
        response = f"🔍 BIN: {bin_number}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}\nSaldo: {get_user_credits(message.from_user.id)}."
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
        response = f"💳 Card: {cc}|{mes}|{ano}|{cvv}\nEstado: {status}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}\nSaldo: {get_user_credits(message.from_user.id)}"
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

while True:
    try:
        print("Limpiando webhooks...")
        bot.delete_webhook()
        print("Bot Premium encendido correctamente.")
        bot.infinity_polling(skip_pending=True)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409:
            print("⚠️ Conflicto. Esperando 10 segundos...")
            time.sleep(10)
        else:
            print(f"Error: {e}")
            time.sleep(5)
    except Exception as e:
        print(f"Error general: {e}")
        time.sleep(5)
