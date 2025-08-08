# IMPORTS Y CONFIGURACIÓN
import nest_asyncio
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv
import tempfile

load_dotenv() 

nest_asyncio.apply()


cred_input = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if cred_input and cred_input.strip().startswith("{"):
    print("[INFO] Las credenciales están embebidas como JSON")
    cred_dict = json.loads(cred_input)
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmpfile:
        json.dump(cred_dict, tmpfile)
        cred_path = tmpfile.name
else:
    print(f"[INFO] Ruta credenciales: {cred_input}")
    cred_path = cred_input or "./credentials.json"

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)



firebase_admin.initialize_app(cred)
db = firestore.client()

def get_today():
    return datetime.now().strftime('%Y-%m-%d')

def is_summer_schedule():
    return datetime.now().month in [7, 8]

def load_user_day(user_id, date_str):
    doc_ref = db.collection("registros").document(user_id).collection("dias").document(date_str)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else {}

def save_user_day(user_id, date_str, data):
    doc_ref = db.collection("registros").document(user_id).collection("dias").document(date_str)
    doc_ref.set(data)

def calculate_total_pause(pauses):
    total_pause = timedelta()
    for p in pauses:
        if "start" in p and "end" in p:
            pause_start = datetime.fromisoformat(p["start"])
            pause_end = datetime.fromisoformat(p["end"])
            duration = pause_end - pause_start
            if is_summer_schedule():
                excess = duration - timedelta(minutes=15)
                if excess > timedelta(0):
                    total_pause += excess
            else:
                total_pause += duration
    return total_pause

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Iniciar", callback_data="start_day")],
        [InlineKeyboardButton("⏸ Pausa", callback_data="pause"),
         InlineKeyboardButton("▶️ Reanudar", callback_data="resume")],
        [InlineKeyboardButton("🔴 Salir", callback_data="end_day")],
        [InlineKeyboardButton("📊 Resumen", callback_data="summary")]
    ])

# COMANDOS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Usa los botones para controlar tu jornada o /help para ver los comandos disponibles.",
        reply_markup=main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Aquí tienes las instrucciones para editar tus registros manualmente:\n\n"
        "✏️ Comandos disponibles:\n"
        "/editar_entrada HH:MM - Cambiar hora de entrada\n"
        "/editar_salida HH:MM - Cambiar hora de salida\n"
        "/editar_pausa_inicio N HH:MM - Cambiar inicio de la pausa número N\n"
        "/editar_pausa_fin N HH:MM - Cambiar fin de la pausa número N\n\n"
        "📌 N es el índice de la pausa (1 = primera, 2 = segunda, etc.)"
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    today = get_today()
    now_iso = datetime.now().isoformat()

    record = load_user_day(user_id, today)
    if "pauses" not in record:
        record["pauses"] = []

    action = query.data

    if action == "start_day":
        if "start" in record:
            start_dt = datetime.fromisoformat(record["start"])
            work_duration = timedelta(hours=7 if is_summer_schedule() else 8)
            total_pause = calculate_total_pause(record["pauses"])
            estimated_exit = start_dt + work_duration + total_pause
            msg = (
                f"🟢 Jornada ya iniciada a las {start_dt.strftime('%H:%M')}\n"
                f"📌 Hora estimada de salida: {estimated_exit.strftime('%H:%M')}"
            )
        else:
            start_dt = datetime.now()
            record["start"] = now_iso
            record["pauses"] = []
            work_duration = timedelta(hours=7 if is_summer_schedule() else 8)
            default_pause = timedelta(minutes=15) if is_summer_schedule() else timedelta()
            estimated_exit = start_dt + work_duration + default_pause
            msg = (
                f"🟢 Jornada iniciada a las {start_dt.strftime('%H:%M')}\n"
                f"📌 Hora estimada de salida: {estimated_exit.strftime('%H:%M')}"
            )


    elif action == "pause":
        if record["pauses"] and "end" not in record["pauses"][-1]:
            msg = "⚠️ Ya estás en pausa."
        else:
            record["pauses"].append({"start": now_iso})
            msg = "⏸ Pausa iniciada."

    elif action == "resume":
        if record["pauses"] and "end" not in record["pauses"][-1]:
            record["pauses"][-1]["end"] = now_iso
            msg = "▶️ Pausa finalizada."
        else:
            msg = "⚠️ No hay pausa activa."

    elif action == "end_day":
        record["end"] = now_iso
        save_user_day(user_id, today, record)

        # Cálculo personalizado de tiempo extra/faltante
        start = datetime.fromisoformat(record["start"])
        end = datetime.fromisoformat(record["end"])
        pauses = record.get("pauses", [])
        total_pause = calculate_total_pause(pauses)
        worked = end - start - total_pause
        required = timedelta(hours=7 if is_summer_schedule() else 8)
        balance = worked - required
        minutes = abs(int(balance.total_seconds() // 60))
        sign = "extra" if balance.total_seconds() > 0 else "faltante"

        msg = (
            f"🔴 Jornada finalizada.\n\n"
            f"{get_day_summary(record)}\n\n"
            f"📈 Has trabajado {minutes} minutos de hora {sign} hoy."
    )


    elif action == "summary":
        msg = get_day_summary(record)

    else:
        msg = "❓ Acción no reconocida."

    save_user_day(user_id, today, record)
    await query.edit_message_text(msg, reply_markup=main_keyboard())

def get_day_summary(record, include_balance=False):
    try:
        start = datetime.fromisoformat(record["start"])
        end = datetime.fromisoformat(record.get("end", datetime.now().isoformat()))
        pauses = record.get("pauses", [])
        total_pause = calculate_total_pause(pauses)
        total_worked = end - start - total_pause
        h, m = divmod(total_worked.seconds // 60, 60)
        salida = (start + timedelta(hours=7 if is_summer_schedule() else 8) + total_pause).strftime('%H:%M')

        msg = f"📊 Tiempo trabajado: {h}h {m}m\n📌 Hora estimada de salida: {salida}"

        if include_balance:
            balance = total_worked - timedelta(hours=7 if is_summer_schedule() else 8)
            sign = "➕" if balance.total_seconds() > 0 else "➖"
            msg += f"\n{sign} Tiempo {'extra' if sign == '➕' else 'faltante'}: {abs(int(balance.total_seconds() // 60))} min"

        return msg
    except:
        return "⚠️ No hay suficientes datos."

async def generic_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str):
    user_id = str(update.effective_user.id)
    today = get_today()
    record = load_user_day(user_id, today)
    if "pauses" not in record:
        record["pauses"] = []

    args = context.args
    if field in ["pause_start", "pause_end"]:
        if len(args) != 2:
            await update.message.reply_text("❗ Usa /editar_pausa_inicio N HH:MM")
            return
        idx = int(args[0]) - 1
        h, m = map(int, args[1].split(":"))
        time = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0).isoformat()
        if idx < 0 or idx >= len(record["pauses"]):
            await update.message.reply_text("❗ Índice inválido.")
            return
        key = "start" if field == "pause_start" else "end"
        record["pauses"][idx][key] = time
    else:
        if len(args) != 1:
            await update.message.reply_text("❗ Usa /editar_entrada HH:MM")
            return
        h, m = map(int, args[0].split(":"))
        record[field] = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0).isoformat()

    save_user_day(user_id, today, record)
    await update.message.reply_text("✏️ Actualizado correctamente.\n\n" + get_day_summary(record))

def run_bot():
    TOKEN = os.environ["BOT_TOKEN"]
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(CommandHandler("editar_entrada", lambda u, c: generic_edit(u, c, "start")))
    app.add_handler(CommandHandler("editar_salida", lambda u, c: generic_edit(u, c, "end")))
    app.add_handler(CommandHandler("editar_pausa_inicio", lambda u, c: generic_edit(u, c, "pause_start")))
    app.add_handler(CommandHandler("editar_pausa_fin", lambda u, c: generic_edit(u, c, "pause_end")))

    async def setup():
        await app.bot.set_my_commands([
            BotCommand("start", "Mostrar menú de fichaje"),
            BotCommand("help", "Instrucciones de uso"),
            BotCommand("editar_entrada", "Editar hora de entrada"),
            BotCommand("editar_salida", "Editar hora de salida"),
            BotCommand("editar_pausa_inicio", "Editar pausa inicio"),
            BotCommand("editar_pausa_fin", "Editar pausa fin"),
        ])
        print("Bot en marcha...")
        await app.run_polling(close_loop=False)

    loop = asyncio.get_event_loop()
    loop.create_task(setup())
    loop.run_forever()

if __name__ == "__main__":
    run_bot()
