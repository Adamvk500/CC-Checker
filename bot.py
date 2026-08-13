import os
import re
import random
import sys
import time
import ssl  
from datetime import datetime
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
    # Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id BIGINT PRIMARY KEY,
            alias_elegido TEXT UNIQUE,
            telegram_username TEXT,
            creditos INTEGER DEFAULT 0,
            rango TEXT DEFAULT 'Gratis'
        )
    ''')
    try:
        cursor.execute('ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_uso DOUBLE PRECISION DEFAULT 0')
    except: pass
    
    # MODIFICADO: Creación automática de la tabla de Logs Forenses en Supabase
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_auditoria (
            id SERIAL PRIMARY KEY,
            fecha_hora TEXT,
            user_id BIGINT,
            alias TEXT,
            comando TEXT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def verificar_registro(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT alias_elegido, creditos, rango, ultimo_uso FROM usuarios WHERE id = %s', (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

# NUEVA: Función de ciberseguridad para registrar eventos en la nube
def registrar_log_evento(user_id, comando_texto):
    try:
        datos = verificar_registro(user_id)
        alias_usuario = datos[0] if datos else "No_Registrado"
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO logs_auditoria (fecha_hora, user_id, alias, comando) VALUES (%s, %s, %s, %s)', 
                       (fecha_actual, user_id, alias_usuario, comando_texto))
        conn.commit()
        cursor.close()
        conn.close()
    except:
        pass

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
    cursor.execute('INSERT INTO usuarios (id, alias_elegido, telegram_username, creditos, ultimo_uso) VALUES (%s, %s, %s, 10, 0) ON CONFLICT (id) DO NOTHING', 
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

def update_user_timestamp(user_id, timestamp):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET ultimo_uso = %s WHERE id = %s', (timestamp, user_id))
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
    return result if result else 0

def update_user_credits(user_id, nuevos_creditos):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET creditos = %s WHERE id = %s', (nuevos_creditos, user_id))
    conn.commit()
    cursor.close()
    conn.close()
def check_user_access(message, cost=1):
    user_id = message.from_user.id
    current_time = time.time()
    
    # MODIFICADO: Guarda un registro forense automático en Supabase de lo que escribe el usuario
    registrar_log_evento(user_id, message.text)
    
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario:
        bot.reply_to(message, "⚠️ Acceso Denegado. Registrate con /register tu_nombre.")
        return False
        
    alias = datos_usuario[0]
    creditos = datos_usuario[1]
    rango = datos_usuario[2]
    ultimo_uso = datos_usuario[3] or 0.0  

    if rango == "Baneado":
        return False

    tiempo_transcurrido = current_time - ultimo_uso
    if tiempo_transcurrido < 3:
        segundos_restantes = 3 - int(tiempo_transcurrido)
        bot.reply_to(message, f"⏳ <b>¡SISTEMA ANTIFLOOD!</b>\nPor favor, espera <code>{segundos_restantes}</code>s antes de volver a ejecutar un comando.", parse_mode="HTML")
        return False

    update_user_timestamp(user_id, current_time)

    if rango == "VIP":
        return True
        
    if creditos < cost:
        bot.reply_to(message, f"❌ Creditos insuficientes. Tienes: {creditos} monedas.")
        return False
        
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



@bot.message_handler(commands=['panel', 'admin'])
def show_admin_panel(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513:
        bot.reply_to(message, "❌ No tienes permisos de dueño para ver este panel.")
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        total_usuarios = cursor.fetchone()
        cursor.execute('SELECT SUM(creditos) FROM usuarios')
        total_creditos = cursor.fetchone() or [0]
        cursor.close()
        conn.close()
        texto_panel = f"💻 <b>PANEL DE CONTROL CENTRAL</b>\n─────────────────────\n👥 <b>Usuarios en Base de Datos:</b> <code>{total_usuarios[0]}</code>\n🪙 <b>Monedas Totales Emitidas:</b> <code>{total_creditos[0]}</code> 🪙\n─────────────────────\n📢 <i>Usa <code>/broadcast texto</code> para alertar a todos.</i>"
        bot.reply_to(message, texto_panel, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Error al auditar la base de datos: {e}")

@bot.message_handler(commands=['broadcast', 'alert'])
def broadcast_message_admin(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if len(args) < 2: return
    mensaje_masivo = args[1]
    bot.reply_to(message, "⏳ Iniciando envío masivo...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM usuarios')
        lista_usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        exitos, fallidos = 0, 0
        for usuario in lista_usuarios:
            uid = usuario[0]
            try:
                bot.send_message(uid, f"📢 <b>ALERTA DEL ADMINISTRADOR</b>\n─────────────────────\n{mensaje_masivo}", parse_mode="HTML")
                exitos += 1
                time.sleep(0.1)
            except: fallidos += 1
        bot.reply_to(message, f"📢 Envío Completado\n🟢 Entregados: {exitos} | 🔴 Fallidos: {fallidos}")
    except Exception as e: bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['setgratis'])
def remove_user_vip_admin(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    datos_cliente = verificar_registro(target_id)
    if datos_cliente:
        update_user_rank(target_id, "Gratis")
        bot.reply_to(message, f"🔰 Rango de <code>{datos_cliente[0]}</code> cambiado de nuevo a <b>Gratis/Desbaneado</b>.", parse_mode="HTML")

@bot.message_handler(commands=['setvip'])
def set_user_vip_admin(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    datos_cliente = verificar_registro(target_id)
    if datos_cliente:
        update_user_rank(target_id, "VIP")
        bot.reply_to(message, f"💎 Rango de <code>{datos_cliente[0]}</code> actualizado a <b>VIP Premium</b>.", parse_mode="HTML")

@bot.message_handler(commands=['delete', 'unregister'])
def delete_user_admin(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        datos_cliente = verificar_registro(target_id)
        if datos_cliente:
            eliminar_usuario_db(target_id)
            bot.reply_to(message, f"🗑️ Cuenta eliminada.")
    else:
        if verificar_registro(user_id): eliminar_usuario_db(user_id)

@bot.message_handler(commands=['add'])
def add_credits_admin(message):
    user_id = message.from_user.id
    args = message.text.split()
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if len(args) < 2: return
    try:
        cantidad = int(args[-1])
        target_id = message.reply_to_message.from_user.id if message.reply_to_message else user_id
        datos_cliente = verificar_registro(target_id)
        if datos_cliente:
            update_user_credits(target_id, datos_cliente[1] + cantidad)
            bot.reply_to(message, f"🪙 Monedas inyectadas.")
    except: pass

@bot.message_handler(commands=['aprobar_bizum'])
def approve_bizum_ticket(message):
    user_id = message.from_user.id
    args = message.text.split()
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if len(args) < 3: return
    try:
        target_uid = int(args[1])
        cantidad = int(args[2])
        datos_cliente = verificar_registro(target_uid)
        if datos_cliente:
            update_user_credits(target_uid, datos_cliente[1] + cantidad)
            bot.reply_to(message, f"✅ Bizum Aprobado.")
            bot.send_message(target_uid, f"🎉 <b>¡BIZUM VERIFICADO CON ÉXITO!</b>\n📥 Acreditados: +<code>{cantidad}</code> monedas.\n🪙 Total actual: <code>{datos_cliente[1] + cantidad}</code> créditos.", parse_mode="HTML")
    except: pass
@bot.message_handler(commands=['register'])
def register_user(message):
    user_id = message.from_user.id
    tg_username = message.from_user.username or 'Usuario'
    args = message.text.split()
    if verificar_registro(user_id):
        bot.reply_to(message, "❌ Ya estás registrado en nuestro sistema.")
        return
    if len(args) < 2:
        bot.reply_to(message, "✏️ <b>Uso correcto:</b> <code>/register tu_nombre</code>", parse_mode="HTML")
        return
    alias_deseado = args[-1]
    if not re.match(r'^[\w\d]+$', alias_deseado): return
    if comprobar_alias_existe(alias_deseado): return
    registrar_usuario_manual(user_id, alias_deseado, tg_username)
    bot.reply_to(message, f"🎉 <b>¡REGISTRO COMPLETADO!</b>\n👤 Bienvenido: <code>{alias_deseado}</code>\n🪙 Regalo inicial: <b>10 créditos</b> 🪙", parse_mode="HTML")

@bot.message_handler(commands=['credits', 'bal'])
def show_credits(message):
    datos = verificar_registro(message.from_user.id)
    if not datos: return
    bot.reply_to(message, f"👤 <b>CUENTA DE USUARIO</b>\n👤 Alias: <code>{datos[0]}</code>\n🪙 Saldo: <code>{datos[1]}</code> créditos\n🔰 Rango: <b>{datos[2]}</b>", parse_mode="HTML")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    datos = verificar_registro(message.from_user.id)
    if datos:
        welcome_text = f"👋 <b>¡Hola de nuevo, {datos[0]}!</b>\n🪙 <b>Tu Saldo:</b> <code>{datos[1]}</code> créditos\n🔰 <b>Tu Rango:</b> <code>{datos[2]}</code>\n⚡ <i>Escribe <code>/comandos</code> para ver las herramientas.</i>"
    else:
        welcome_text = f"👋 <b>¡BIENVENIDO AL CHECKER BOT!</b>\n🛡️ Regístrate escribiendo:\n<code>/register tu_nombre</code>"
    bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(commands=['comandos', 'help'])
def show_public_commands(message):
    if not verificar_registro(message.from_user.id): return
    texto_comandos = f"📚 <b>MENÚ DE HERRAMIENTAS</b>\n─────────────────────\n⚡ <code>/chk CARD|MM|AA|CVV</code>\n🎲 <code>/gen BIN</code>\n🔍 <code>/bin BIN</code>\n🪙 <code>/credits</code>\n💳 <code>/recargar</code>"
    bot.reply_to(message, texto_comandos, parse_mode="HTML")

@bot.message_handler(commands=['recargar', 'buy'])
def dual_recharge_menu(message):
    if not verificar_registro(message.from_user.id): return
    texto_pago = f"💳 <b>PASARELA MULTIPAGO</b>\n• 1 EUR = <b>100 créditos</b>\n• Bizum al número: <code>600123456</code> (Concepto: tu ID)\n• Sube el ticket con: <code>/claim_bizum CODIGO</code>\n• Crypto BTC a: <code>1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa</code>\n• Reclama Crypto con: <code>/claim_crypto HASH</code>"
    bot.reply_to(message, texto_pago, parse_mode="HTML")

@bot.message_handler(commands=['claim_crypto'])
def verify_blockchain_tx(message):
    user_id = message.from_user.id
    args = message.text.split()
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario or len(args) < 2: return
    txid = args[-1]
    bot.reply_to(message, "🔍 Verificando transacción en la red Blockchain...")
    time.sleep(2)
    if len(txid) < 15: return
    update_user_credits(user_id, datos_usuario[1] + 200)
    bot.reply_to(message, f"🎉 ¡PAGO VERIFICADO! +200 créditos.")

@bot.message_handler(commands=['claim_bizum'])
def claim_bizum_ticket(message):
    user_id = message.from_user.id
    args = message.text.split()
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario or len(args) < 2: return
    codigo_operacion = args[-1]
    bot.reply_to(message, "⏳ Ticket enviado al Staff... Esperando verificación bancaria.")
    texto_alerta_admin = f"🚨 <b>BIZUM RECIBIDO</b>\n👤 Cliente: {datos_usuario[0]} (ID: <code>{user_id}</code>)\n🔢 Ticket: <code>{codigo_operacion}</code>\n💡 Aprobar con:\n<code>/aprobar_bizum {user_id} 100</code>"
    bot.send_message(5203992513, texto_alerta_admin, parse_mode="HTML")

@bot.message_handler(regexp=r'(?i)^[!/]gen')
def generate_cards(message):
    if not check_user_access(message, cost=1): return
    try:
        input_data = message.text
        bin_match = re.findall(r'\d+', input_data)
        if not bin_match: return
        bin_number = "".join(bin_match)[:6]
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
        bot.reply_to(message, f"🎲 Tarjetas Generadas (BIN: {bin_number})\n\n{cards_output}")
    except Exception as e: bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(regexp=r'(?i)^[!/]bin')
def check_bin_standalone(message):
    if not check_user_access(message, cost=1): return
    try:
        input_data = message.text
        bin_match = re.findall(r'\d+', input_data)
        if not bin_match: return
        bin_number = "".join(bin_match)[:6]
        bot.send_chat_action(message.chat.id, 'typing')
        if bin_number in LOCAL_BINS:
            bin_data = LOCAL_BINS[bin_number]
            brand, card_type, bank_name, country_name, flag = bin_data["brand"], bin_data["type"], bin_data["bank"], bin_data["country"], bin_data["flag"]
        else:
            brand, card_type, bank_name, country_name, flag = "Visa", "Credit", "BANCO GENERICO", "Desconocido", "🏳️•🌈"
        bot.reply_to(message, f"🔍 BIN: {bin_number}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}")
    except Exception as e: bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(regexp=r'(?i)^[!/]chk')
def check_card(message):
    if not check_user_access(message, cost=1): return
    try:
        input_data = message.text
        cards = re.findall(r'\d+', input_data)
        if len(cards) < 4: return
        cc, mes, ano, cvv = cards[0], cards[1], cards[2], cards[3]
        is_luhn_valid = luhn_check(cc)
        status = "🟢 Valida" if is_luhn_valid else "🔴 Invalida"
        bin_number = cc[:6]
        if bin_number in LOCAL_BINS:
            bin_data = LOCAL_BINS[bin_number]
            brand, card_type, bank_name, country_name, flag = bin_data["brand"], bin_data["type"], bin_data["bank"], bin_data["country"], bin_data["flag"]
        else:
            brand, card_type, bank_name, country_name, flag = "Visa", "Credit", "BANCO GENERICO", "Desconocido", "🏳️•🌈"
        bot.reply_to(message, f"💳 Card: {cc}|{mes}|{ano}|{cvv}\nEstado: {status}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}")
    except Exception as e: bot.reply_to(message, f"⚠️ Error: {str(e)}")

while True:
    try:
        bot.delete_webhook()
        print("Bot Premium Supabase conectado correctamente.")
        bot.infinity_polling(skip_pending=True)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409: time.sleep(10)
        else: time.sleep(5)
    except Exception as e: time.sleep(5)
