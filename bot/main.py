import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bot.config import Settings
from bot.storage import Storage

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.INFO)
logger = logging.getLogger('price-hunter-radar')

def services(context):
    return context.application.bot_data['settings'], context.application.bot_data['storage']

def allowed(update, settings):
    chat = update.effective_chat
    return bool(chat and str(chat.id) == settings.telegram_chat_id)

async def deny(update):
    if update.effective_message:
        await update.effective_message.reply_text('Accès non autorisé.')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings, _ = services(context)
    if not allowed(update, settings): return await deny(update)
    await update.effective_message.reply_text('Price Hunter Radar connecté.\n/help — commandes\n/status — état\n/watchlist — produits suivis\n/add <produit> — ajouter\n/remove <produit> — retirer\n/scan — lancer un scan\n/pause et /resume — surveillance')

async def help_command(update, context):
    settings, _ = services(context)
    if not allowed(update, settings): return await deny(update)
    await update.effective_message.reply_text('/status\n/watchlist\n/add <produit>\n/remove <produit>\n/scan\n/pause\n/resume')

async def status(update, context):
    settings, store = services(context)
    if not allowed(update, settings): return await deny(update)
    scan_state = 'activé' if settings.scanner_enabled else 'désactivé (API produit non configurée)'
    await update.effective_message.reply_text(f'Bot Telegram : opérationnel\nScanner : {scan_state}\nPause : {"oui" if store.is_paused() else "non"}\nProduits suivis : {len(store.list_watchlist())}')

async def watchlist(update, context):
    settings, store = services(context)
    if not allowed(update, settings): return await deny(update)
    items = store.list_watchlist()
    await update.effective_message.reply_text('Watchlist vide.' if not items else 'Produits suivis :\n' + '\n'.join('• ' + x for x in items))

async def add(update, context):
    settings, store = services(context)
    if not allowed(update, settings): return await deny(update)
    query = ' '.join(context.args).strip()
    if not query: return await update.effective_message.reply_text('Utilisation : /add <produit>')
    await update.effective_message.reply_text('Ajouté.' if store.add_watch(query) else 'Déjà présent.')

async def remove(update, context):
    settings, store = services(context)
    if not allowed(update, settings): return await deny(update)
    query = ' '.join(context.args).strip()
    if not query: return await update.effective_message.reply_text('Utilisation : /remove <produit>')
    await update.effective_message.reply_text('Retiré.' if store.remove_watch(query) else 'Introuvable.')

async def pause(update, context):
    settings, store = services(context)
    if not allowed(update, settings): return await deny(update)
    store.set_paused(True)
    await update.effective_message.reply_text('Surveillance en pause.')

async def resume(update, context):
    settings, store = services(context)
    if not allowed(update, settings): return await deny(update)
    store.set_paused(False)
    await update.effective_message.reply_text('Surveillance reprise.')

async def scan(update, context):
    settings, store = services(context)
    if not allowed(update, settings): return await deny(update)
    if store.is_paused(): return await update.effective_message.reply_text('Surveillance en pause.')
    await update.effective_message.reply_text("Scan non disponible : aucune API produit autorisée n'est raccordée. Aucune fausse alerte ne sera générée.")

def main():
    load_dotenv()
    settings = Settings.from_env()
    store = Storage(settings.database_path)
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data.update(settings=settings, storage=store)
    for command, handler in [('start', start), ('help', help_command), ('status', status), ('watchlist', watchlist), ('add', add), ('remove', remove), ('pause', pause), ('resume', resume), ('scan', scan)]:
        app.add_handler(CommandHandler(command, handler))
    logger.info('Starting Price Hunter Radar')
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
