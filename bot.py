# ==========================================
# # PARTE 1: INFRAESTRUCTURA DE RED, CONFIGURACIÓN CORE Y CONEXIONES SEGURAS SUPABASE PERMANENTES
# ==========================================
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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id BIGINT PRIMARY KEY,
            alias_elegido TEXT UNIQUE,
            telegram_username TEXT,
            creditos INTEGER DEFAULT 0,
            rango TEXT DEFAULT 'Gratis'
        )
    ''')
    try: cursor.execute('ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_uso DOUBLE PRECISION DEFAULT 0')
    except: pass
    try: cursor.execute('ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS es_staff INTEGER DEFAULT 0')
    except: pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_servidor (
            clave TEXT PRIMARY KEY,
            valor_id BIGINT
        )
    ''')
    
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
    cursor.execute('SELECT alias_elegido, creditos, rango, ultimo_uso, es_staff FROM usuarios WHERE id = %s', (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

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
    except: pass

def guardar_grupo_staff_db(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO config_servidor (clave, valor_id) VALUES (\'grupo_staff\', %s) ON CONFLICT (clave) DO UPDATE SET valor_id = %s', (chat_id, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

# 👑 FIJO: Extracción estricta por result[0] para romper el bug de la tupla
def recuperar_grupo_staff_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT valor_id FROM config_servidor WHERE clave = \'grupo_staff\'')
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error forense al leer la ID del grupo en Supabase: {e}")
        return None

def registrar_usuario_manual(user_id, alias, tg_username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO usuarios (id, alias_elegido, telegram_username, creditos, ultimo_uso, es_staff) VALUES (%s, %s, %s, 10, 0, 0) ON CONFLICT (id) DO NOTHING', 
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

def update_user_staff_status(user_id, nivel_staff):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET es_staff = %s WHERE id = %s', (nivel_staff, user_id))
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
    return result[0] if result else 0

def update_user_credits(user_id, nuevos_creditos):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET creditos = %s WHERE id = %s', (nuevos_creditos, user_id))
    conn.commit()
    cursor.close()
    conn.close()
# ==========================================
# # PARTE 2: GATEWAY DE SEGURIDAD (ANTIFLOOD), VALIDACIONES TÉCNICAS Y GESTIÓN DEL GRUPO CENTRAL STAFF
# ==========================================
def check_user_access(message, cost=1):
    user_id = message.from_user.id
    current_time = time.time()
    
    registrar_log_evento(user_id, message.text)
    
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario:
        bot.reply_to(message, "⚠️ Acceso Denegado. Registrate con /register tu_nombre.")
        return False
        
    alias, creditos, rango, ultimo_uso, es_staff = datos_usuario

    if rango == "Baneado": return False

    if 'LAST_COMMAND_TIME' not in globals(): globals()['LAST_COMMAND_TIME'] = {}
    if user_id in globals()['LAST_COMMAND_TIME']:
        tiempo_transcurrido = current_time - globals()['LAST_COMMAND_TIME'][user_id]
        if tiempo_transcurrido < 3:
            segundos_restantes = 3 - int(tiempo_transcurrido)
            bot.reply_to(message, f"⏳ <b>¡SISTEMA ANTIFLOOD!</b>\nPor favor, espera <code>{segundos_restantes}</code>s.", parse_mode="HTML")
            return False

    globals()['LAST_COMMAND_TIME'][user_id] = current_time
    if rango == "VIP": return True
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

@bot.message_handler(commands=['setgrupo'])
def auto_save_group_channel(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    guardar_grupo_staff_db(message.chat.id)
    bot.reply_to(message, f"🎯 <b>¡GRUPO DE STAFF CONFIGURADO!</b>\nLas alertas de Bizum cazarán de forma centralizada el entero puro.", parse_mode="HTML")

@bot.message_handler(commands=['panel', 'admin'])
def show_admin_panel(message):
    user_id = message.from_user.id
    datos = verificar_registro(user_id)
    is_staff_user = datos[4] if datos else 0
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513 and is_staff_user != 1: return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        total_usuarios = cursor.fetchone()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"💻 Usuarios totales registrados en Supabase: {total_usuarios[0]}")
    except: pass

@bot.message_handler(commands=['addstaff'])
def promote_to_staff_owner(message):
    user_id = message.from_user.id
    args = message.text.split()
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if len(args) < 2: return
    target_alias = args[-1].lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM usuarios WHERE alias_elegido = %s', (target_alias,))
        target_data = cursor.fetchone()
        cursor.close()
        conn.close()
        if target_data:
            update_user_staff_status(target_data[0], 1)
            bot.reply_to(message, f"🛠️ Staff asignado a <code>{target_alias}</code>.", parse_mode="HTML")
    except: pass
# ==========================================
# # PARTE 3: CANDADOS ADMINISTRATIVOS COMPLETO (APROBAR / RECHAZAR BIZUM DIRIGIDO COMO FRANCOTIRADOR)
# ==========================================
@bot.message_handler(commands=['aprobar_bizum'])
def approve_bizum_ticket(message):
    user_id = message.from_user.id
    args = message.text.split()
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if len(args) < 4: return 
    try:
        target_uid = int(args[1])
        cantidad = int(args[2])
        chat_origen_salva = int(args[3]) 
        
        datos_cliente = verificar_registro(target_uid)
        if datos_cliente:
            alias, creditos_viejos = datos_cliente[0], datos_cliente[1]
            nuevos_creditos = creditos_viejos + cantidad
            update_user_credits(target_uid, nuevos_creditos)
            
            bot.send_message(chat_origen_salva, f"✅ <b>¡BIZUM ACEPTADO!</b>\n─────────────────────\n👤 Cliente: <code>{alias}</code>\n📥 Estado: <b>Fondos Verificados</b>\n🪙 Recarga: +<code>{cantidad}</code> créditos sumados a tu perfil.", parse_mode="HTML")
    except Exception as e: 
        print(f"Error técnico en enrutador de pagos: {e}")

@bot.message_handler(commands=['rechazar_bizum'])
def reject_bizum_ticket(message):
    user_id = message.from_user.id
    args = message.text.split()
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if len(args) < 3: return 
    try:
        target_uid = int(args[1])
        chat_origen_salva = int(args[2])
        datos_cliente = verificar_registro(target_uid)
        if datos_cliente:
            alias = datos_cliente[0]
            bot.send_message(chat_origen_salva, f"❌ <b>¡BIZUM RECHAZADO!</b>\n─────────────────────\n👤 Cliente: <code>{alias}</code>\n📥 Estado: <b>No Recibido / Falso</b>\n⚠️ Resolución: <i>Ticket cerrado. No se ha encontrado ningún ingreso en el banco.</i>", parse_mode="HTML")
    except Exception as e:
        print(f"Error técnico en denegador de pagos: {e}")

@bot.message_handler(commands=['setvip'])
def set_user_vip_admin(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513:
        bot.reply_to(message, "❌ Acceso Denegado. Tu rango de Staff no te permite gestionar miembros.")
        return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    datos_cliente = verificar_registro(target_id)
    if datos_cliente:
        update_user_rank(target_id, "VIP")
        bot.reply_to(message, f"💎 Rango de <code>{datos_cliente[0]}</code> actualizado a <b>VIP Premium</b>.", parse_mode="HTML")

@bot.message_handler(commands=['delete', 'unregister'])
def delete_user_admin(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513:
        bot.reply_to(message, "❌ Acceso Denegado. Tu rango de Staff no te permite gestionar miembros.")
        return
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        datos_cliente = verificar_registro(target_id)
        if datos_cliente: eliminar_usuario_db(target_id)
# ==========================================
# # PARTE 4: COMANDOS PÚBLICOS, MANEJADOR DE BOTONES INLINE CONGELADO INTEGRO Y INFINITY POLLING
# ==========================================
@bot.message_handler(commands=['register'])
def register_user(message):
    user_id = message.from_user.id
    tg_username = message.from_user.username or 'Usuario'
    args = message.text.split()
    if verificar_registro(user_id):
        bot.reply_to(message, "❌ Ya estás registrado.")
        return
    if len(args) < 2: return
    alias_deseado = args[-1]
    registrar_usuario_manual(user_id, alias_deseado, tg_username)
    bot.reply_to(message, f"🎉 <b>¡REGISTRO COMPLETADO!</b>\n👤 Bienvenido: <code>{alias_deseado}</code>", parse_mode="HTML")

@bot.message_handler(commands=['credits', 'bal'])
def show_credits(message):
    datos = verificar_registro(message.from_user.id)
    if not datos: return
    alias, creditos, rango = datos[0], datos[1], datos[2]
    bot.reply_to(message, f"👤 <b>CUENTA</b>\n👤 Alias: <code>{alias}</code>\n🪙 Saldo: <code>{creditos}</code> créditos\n🔰 Rango: <b>{rango}</b>", parse_mode="HTML")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    datos = verificar_registro(message.from_user.id)
    if datos:
        alias, creditos, rango = datos[0], datos[1], datos[2]
        markup = InlineKeyboardMarkup()
        btn_comandos = InlineKeyboardButton("📚 Ver Herramientas", callback_data="abrir_menu_comandos")
        btn_recargar = InlineKeyboardButton("💳 Comprar Créditos", callback_data="abrir_menu_recargar")
        markup.add(btn_comandos, btn_recargar)
        bot.reply_to(message, f"👋 <b>¡Hola de nuevo, {alias}!</b>\n\n👑 Bienvenido a la central de simulación.\n🌕 Saldo: <code>{creditos}</code> créditos\n🔰 Rango: <code>{rango}</code>\n\n👇 <i>Selecciona una opción del panel interactivo:</i>", parse_mode="HTML", reply_markup=markup)
    else:
        bot.reply_to(message, "👋 <b>¡BIENVENIDO!</b>\n🛡️ Regístrate con: <code>/register tu_nombre</code>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_listener_buttons(call):
    try: bot.answer_callback_query(call.id)
    except: pass
    mensaje_clonado = call.message
    mensaje_clonado.from_user.id = call.from_user.id
    if call.data == "abrir_menu_comandos": show_public_commands(mensaje_clonado)
    elif call.data == "abrir_menu_recargar": dual_recharge_menu(mensaje_clonado)

@bot.message_handler(commands=['comandos', 'help'])
def show_public_commands(message):
    if not verificar_registro(message.from_user.id): return
    bot.reply_to(message, "📚 <b>HERRAMIENTAS</b>\n─────────────────────\n⚡ <code>/chk CARD</code>\n🎲 <code>/gen BIN</code>\n🔍 <code>/bin BIN</code>\n🪙 <code>/credits</code>\n💳 <code>/recargar</code>\n📢 <code>/soporte TU_MENSAJE</code>", parse_mode="HTML")

@bot.message_handler(commands=['recargar', 'buy'])
def dual_recharge_menu(message):
    if not verificar_registro(message.from_user.id): return
    bot.reply_to(message, f"💳 <b>PASARELA MULTIPAGO</b>\n• Bizum al: <code>600123456</code>\n• Reclama Bizum: <code>/claim_bizum CODIGO</code>", parse_mode="HTML")

@bot.message_handler(commands=['soporte', 'contact'])
def contact_support_team(message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario: return
    if len(args) < 2:
        bot.reply_to(message, "✏️ <b>Uso correcto:</b> <code>/soporte Tu mensaje aquí</code>", parse_mode="HTML")
        return
    mensaje_soporte = args[-1]
    alias = datos_usuario[0]
    bot.reply_to(message, "📥 <b>¡Ticket Enviado!</b> Tu mensaje ha sido transmitido de forma encriptada al Staff de guardia.", parse_mode="HTML")
    
    grupo_staff_privado = recuperar_grupo_staff_db() or 5203992513
    texto_soporte_staff = f"📩 <b>¡NUEVO TICKET DE SOPORTE!</b>\n─────────────────────\n👤 Usuario: <code>{alias}</code> (ID: <code>{user_id}</code>)\n💬 {mensaje_soporte}"
    try: 
        bot.send_message(grupo_staff_privado, texto_soporte_staff, parse_mode="HTML")
    except Exception as e:
        print(f"🚨 Error en vivo de la API de Telegram al enviar /soporte al canal STAFF: {e}")

@bot.message_handler(commands=['claim_bizum'])
def claim_bizum_ticket(message):
    user_id = message.from_user.id
    args = message.text.split()
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario or len(args) < 2: return
    codigo_operacion = args[-1]
    chat_origen_exacto = message.chat.id
    alias = datos_usuario[0]
    bot.reply_to(message, "⏳ Ticket enviado al Staff... Esperando verificación bancaria.")
    
    grupo_staff_privado = recuperar_grupo_staff_db() or 5203992513
    texto_alerta_admin = (
        f"🚨 <b>BIZUM RECIBIDO</b>\n─────────────────────\n"
        f"👤 Cliente: {alias} (ID: <code>{user_id}</code>)\n"
        f"🔢 Ticket: <code>{codigo_operacion}</code>\n"
        f"⛓️ Chat Origen: <code>{chat_origen_exacto}</code>\n─────────────────────\n"
        f"💡 <b>Copiar resolución:</b>\n"
        f"🟢 <code>/aprobar_bizum {user_id} 100 {chat_origen_exacto}</code>\n"
        f"🔴 <code>/rechazar_bizum {user_id} {chat_origen_exacto}</code>"
    )
    try: 
        bot.send_message(grupo_staff_privado, texto_alerta_admin, parse_mode="HTML")
    except Exception as e:
        print(f"🚨 Error en vivo de la API de Telegram al enviar /claim_bizum al canal STAFF: {e}")

# 👑 REPARADO: Generador real intacto por Luhn con indexación de créditos Supabase limpia
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
        creditos_actuales = get_user_credits(message.from_user.id)
        bot.reply_to(message, f"🎲 Tarjetas Generadas (BIN: {bin_number})\n\n{cards_output}\n\nSaldo: {creditos_actuales} creditos.")
    except Exception as e: bot.reply_to(message, f"⚠️ Error al generar: {str(e)}")

# 👑 REPARADO: Analizador de BIN real intacto con indexación Supabase limpia
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
            brand, card_type, bank_name, country_name, flag = bin_data["brand"], bin_data["type"], bin_data["bank"], bin_data["country"], bin_data["flag"]
        else:
            brand, card_type, bank_name, country_name, flag = "Visa" if bin_number.startswith('4') else "Mastercard", "Credit", "BANCO GENERICO", "Desconocido", "🏳️•🌈"
        creditos_actuales = get_user_credits(message.from_user.id)
        bot.reply_to(message, f"🔍 BIN: {bin_number}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}\nSaldo: {creditos_actuales}.")
    except Exception as e: bot.reply_to(message, f"⚠️ Error: {str(e)}")

# 👑 REPARADO: Checker real intacto por Luhn con indexación Supabase limpia
@bot.message_handler(regexp=r'(?i)^[!/]chk')
def check_card(message):
    if not check_user_access(message, cost=1): return
    try:
        input_data = message.text
        cards = re.findall(r'\d+', input_data)
        if len(cards) < 4: 
            bot.reply_to(message, "❌ Uso incorrecto. Formato: /chk CARD|MM|AA|CVV")
            return
        cc, mes, ano, cvv = cards[0], cards[1], cards[2], cards[3]
        is_luhn_valid = luhn_check(cc)
        status = "🟢 Valida" if is_luhn_valid else "🔴 Invalida"
        bin_number = cc[:6]
        if bin_number in LOCAL_BINS:
            bin_data = LOCAL_BINS[bin_number]
            brand, card_type, bank_name, country_name, flag = bin_data["brand"], bin_data["type"], bin_data["bank"], bin_data["country"], bin_data["flag"]
        else:
            brand, card_type, bank_name, country_name, flag = "Visa" if bin_number.startswith('4') else "Mastercard", "Credit", "BANCO GENERICO", "Desconocido", "🏳️•🌈"
        bot.reply_to(message, f"💳 Card: {cc}|{mes}|{ano}|{cvv}\nEstado: {status}\nFranquicia: {brand}\nTipo: {card_type}\nBanco: {bank_name}\nPais: {country_name} {flag}")
    except Exception as e: bot.reply_to(message, f"⚠️ Error: {str(e)}")

while True:
    try:
        bot.delete_webhook()
        bot.infinity_polling(skip_pending=True)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409: time.sleep(10)
        else: time.sleep(5)
    except Exception as e: time.sleep(5)
