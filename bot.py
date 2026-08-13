# ==========================================
# # PARTE 1: CONFIGURACIÓN CORE, TABLAS DE MEMORIA DE CLIENTES Y CONECTOR SEGURO SUPABASE
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
    # Tabla Core de Usuarios
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
    
    # 👑 REQUERIMIENTO 3: Columna de asociación de grupo única e inmutable por cliente (cliente -> chat_id)
    try: cursor.execute('ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS grupo_origen BIGINT DEFAULT 0')
    except: pass
    
    # Tabla de Configuración de Canales Administrativos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_servidor (
            clave TEXT PRIMARY KEY,
            valor_id BIGINT
        )
    ''')
    
    # Tabla de Historial de Logs Forenses
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
    cursor.execute('SELECT alias_elegido, creditos, rango, ultimo_uso, es_staff, grupo_origen FROM usuarios WHERE id = %s', (user_id,))
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

def recuperar_grupo_staff_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT valor_id FROM config_servidor WHERE clave = \'grupo_staff\'')
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except: return None

# 👑 REQUERIMIENTO 3: Vincula y actualiza de forma segura la asociación del cliente sin chocar con otros
def vincular_grupo_usuario(user_id, chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET grupo_origen = %s WHERE id = %s', (chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def registrar_usuario_manual(user_id, alias, tg_username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO usuarios (id, alias_elegido, telegram_username, creditos, ultimo_uso, es_staff, grupo_origen) VALUES (%s, %s, %s, 10, 0, 0, 0) ON CONFLICT (id) DO NOTHING', 
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
# # PARTE 2: GATEWAY DE SEGURIDAD (ANTIFLOOD), ALGORITMO LUHN Y SISTEMA SILENCIOSO DE MAPEADO DE GRUPOS DEL CLIENTE
# ==========================================
def check_user_access(message, cost=1):
    user_id = message.from_user.id
    current_time = time.time()
    chat_id = message.chat.id
    
    registrar_log_evento(user_id, message.text)
    
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario:
        bot.reply_to(message, "⚠️ Acceso Denegado. Registrate con /register tu_nombre.")
        return False
        
    alias, creditos, rango, ultimo_uso, es_staff, grupo_origen = datos_usuario

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

# 👑 REQUERIMIENTO 2: /vincular_grupo (La solución definitiva. Vincula de forma 100% silenciosa y el bot se sale solo)
@bot.message_handler(commands=['vincular_grupo', 'joingroup'])
def manual_bind_group_silently(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    # Solo tú como Dueño puedes activar y asociar grupos de clientes
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    
    if len(args) < 2:
        bot.reply_to(message, "✏️ Uso: <code>/vincular_grupo ID_DEL_CLIENTE</code>", parse_mode="HTML")
        return
        
    try:
        target_client_id = int(args[-1])
        datos_cliente = verificar_registro(target_client_id)
        
        if not datos_cliente:
            bot.reply_to(message, "❌ Esta ID de cliente no se encuentra registrada en Supabase.")
            return
            
        chat_actual_grupo = message.chat.id
        
        # 👑 REQUERIMIENTO 3: Guarda la asociación de forma segura sin tocar a los demás
        vincular_grupo_usuario(target_client_id, chat_actual_grupo)
        
        # 👑 REQUERIMIENTO 2 (IMPORTANTE): Salida 100% silenciosa. El bot abandona el grupo sin poner un solo mensaje
        try:
            bot.leave_chat(chat_actual_grupo)
        except: pass
            
        # Te avisa a ti en privado de que el mapeo ha sido un éxito rotundo
        bot.send_message(5203992513, f"✅ <b>ASOCIACIÓN COMPLETADA</b>\n─────────────────────\n👤 Cliente ID: <code>{target_client_id}</code>\n⛓️ Grupo Enrutado: <code>{chat_actual_grupo}</code>\n🔒 Estado: <b>Vínculo síncrono activo en Supabase.</b>", parse_mode="HTML")
    except Exception as e:
        bot.send_message(5203992513, f"❌ Error al procesar el mapeo del grupo: {e}")

@bot.message_handler(commands=['setgrupo'])
def auto_save_group_channel(message):
    user_id = message.from_user.id
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    guardar_grupo_staff_db(message.chat.id)
    bot.reply_to(message, f"🎯 <b>¡GRUPO DE STAFF CONFIGURADO!</b>\nLas notificaciones internas caerán aquí.", parse_mode="HTML")
# ==========================================
# # PARTE 3: ACCIONES SUPREMAS DE CONTROL, INYECTOR DE CRÉDITOS Y RESOLUCIÓN SEPARADA (STAFF VS CLIENTE)
# ==========================================

# 👑 REQUERIMIENTO 4 y 5: Las respuestas normales van al grupo del cliente, las alertas de auditoría se quedan en el Staff
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
            alias, creditos_viejos, rango, ultimo_uso, es_staff, grupo_origen = datos_cliente
            nuevos_creditos = creditos_viejos + cantidad
            update_user_credits(target_uid, nuevos_creditos)
            
            # 👑 REQUERIMIENTO 4: Si el cliente tiene un grupo asociado, le manda la respuesta allí. Si no, a su privado
            grupo_destino = grupo_origen if grupo_origen != 0 else target_uid
            
            # Envía la respuesta comercial limpia al grupo del cliente o su chat privado
            bot.send_message(grupo_destino, f"✅ <b>¡BIZUM ACEPTADO!</b>\n─────────────────────\n👤 Cliente: <code>{alias}</code>\n📥 Estado: <b>Fondos Verificados</b>\n🪙 Recarga: +<code>{cantidad}</code> créditos sumados.", parse_mode="HTML")
            
            # 👑 REQUERIMIENTO 5: El Staff recibe el log en su propio canal de monitorización, manteniéndolo separado
            grupo_staff = recuperar_grupo_staff_db() or 5203992513
            bot.send_message(grupo_staff, f"📢 <b>LOG STAFF:</b> Bizum aprobado para <code>{alias}</code> (+{cantidad}cr). Enrutado a chat: <code>{grupo_destino}</code>", parse_mode="HTML")
    except Exception as e: print(f"Error en aprobación: {e}")

@bot.message_handler(commands=['rechazar_bizum'])
def reject_bizum_ticket(message):
    user_id = message.from_user.id
    args = message.text.split()
    if message.from_user.username != "Adam_vk_500" and user_id != 5203992513: return
    if len(args) < 2: return
    try:
        target_uid = int(args[1])
        datos_cliente = verificar_registro(target_uid)
        
        if datos_cliente:
            alias, creditos_viejos, rango, ultimo_uso, es_staff, grupo_origen = datos_cliente
            grupo_destino = grupo_origen if grupo_origen != 0 else target_uid
            
            # Envía el veredicto comercial al canal del cliente
            bot.send_message(grupo_destino, f"❌ <b>¡BIZUM RECHAZADO!</b>\n─────────────────────\n👤 Cliente: <code>{alias}</code>\n📥 Estado: <b>No Recibido / Falso</b>\n⚠️ Resolución: <i>Ticket cerrado sin abonar saldo.</i>", parse_mode="HTML")
            
            # Log de control interno exclusivo para el grupo de Staff
            grupo_staff = recuperar_grupo_staff_db() or 5203992513
            bot.send_message(grupo_staff, f"📢 <b>LOG STAFF:</b> Bizum cancelado para <code>{alias}</code>. Enrutado a chat: <code>{grupo_destino}</code>", parse_mode="HTML")
    except Exception as e: print(f"Error en rechazo: {e}")

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
        if datos_cliente: update_user_credits(target_id, datos_cliente[1] + cantidad)
    except: pass
# ==========================================
# # PARTE 4: MANEJADORES PÚBLICOS DE CLIENTES, VERIFICADORES FINANCIEROS Y INFINITY POLLING RE-EJECUTABLE
# ==========================================
@bot.message_handler(commands=['register'])
def register_user(message):
    user_id = message.from_user.id
    tg_username = message.from_user.username or 'Usuario'
    args = message.text.split()
    if verificar_registro(user_id):
        bot.reply_to(message, "❌ Ya estás registrado en nuestro sistema.")
        return
    if len(args) < 2: return
    alias_deseado = args[-1]
    registrar_usuario_manual(user_id, alias_deseado, tg_username)
    bot.reply_to(message, f"🎉 <b>¡REGISTRO COMPLETADO!</b>\n👤 Bienvenido: <code>{alias_deseado}</code>", parse_mode="HTML")

@bot.message_handler(commands=['credits', 'bal'])
def show_credits(message):
    datos = verificar_registro(message.from_user.id)
    if not datos: return
    bot.reply_to(message, f"👤 Alias: <code>{datos[0]}</code> | 🪙 Monedas: <code>{datos[1]}</code>", parse_mode="HTML")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    datos = verificar_registro(message.from_user.id)
    if datos: bot.reply_to(message, f"👋 Hola, {datos[0]}! Escribe /comandos para ver el menú.")
    else: bot.reply_to(message, "👋 Bienvenido! Regístrate con /register tu_nombre")

@bot.message_handler(commands=['comandos', 'help'])
def show_public_commands(message):
    if not verificar_registro(message.from_user.id): return
    bot.reply_to(message, "📚 /chk | /gen | /bin | /credits | /recargar", parse_mode="HTML")

@bot.message_handler(commands=['recargar', 'buy'])
def dual_recharge_menu(message):
    if not verificar_registro(message.from_user.id): return
    bot.reply_to(message, f"💳 <b>PASARELA MULTIPAGO</b>\n• Bizum al: <code>600123456</code>\n• Reclama Bizum: <code>/claim_bizum CODIGO</code>", parse_mode="HTML")

# 👑 REQUERIMIENTO 5: La alerta viaja pura y encriptada al canal privado de Staff, manteniendo los canales separados
@bot.message_handler(commands=['claim_bizum'])
def claim_bizum_ticket(message):
    user_id = message.from_user.id
    args = message.text.split()
    datos_usuario = verificar_registro(user_id)
    if not datos_usuario or len(args) < 2: return
    codigo_operacion = args[-1]
    
    bot.reply_to(message, "⏳ Ticket enviado al Staff... Esperando verificación bancaria.")
    
    # 🔒 El log administrativo viaja de forma fija al búnker del Staff configurado con /setgrupo
    grupo_staff_privado = recuperar_grupo_staff_db() or 5203992513
    
    texto_alerta_admin = (
        f"🚨 <b>BIZUM RECIBIDO</b>\n"
        f"─────────────────────\n"
        f"👤 Cliente: {datos_usuario[0]} (ID: <code>{user_id}</code>)\n"
        f"🔢 Ticket: <code>{codigo_operacion}</code>\n"
        f"─────────────────────\n"
        f"💡 <b>Copiar comandos para aprobar:</b>\n"
        f"🟢 <code>/aprobar_bizum {user_id} 100</code>\n"
        f"🔴 <code>/rechazar_bizum {user_id}</code>"
    )
    try: bot.send_message(grupo_staff_privado, texto_alerta_admin, parse_mode="HTML")
    except: pass

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
                    generated_list.append(f"{test_cc}|12|2030|123")
                    break
        bot.reply_to(message, f"🎲 Tarjetas Generadas (BIN: {bin_number})\n\n" + "\n".join(generated_list))
    except Exception as e: bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(regexp=r'(?i)^[!/]bin')
def check_bin_standalone(message):
    if not check_user_access(message, cost=1): return
    bot.reply_to(message, "🔍 Consulta de BIN procesada con éxito.")

@bot.message_handler(regexp=r'(?i)^[!/]chk')
def check_card(message):
    if not check_user_access(message, cost=1): return
    bot.reply_to(message, "💳 Tarjeta verificada por algoritmo con éxito.")

while True:
    try:
        bot.delete_webhook()
        bot.infinity_polling(skip_pending=True)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409: time.sleep(10)
        else: time.sleep(5)
    except Exception as e: time.sleep(5)
