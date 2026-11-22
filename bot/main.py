import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bot.config import Settings
from bot.storage import Storage
from bot.price_engine import PriceEngine

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
    if not allowed(update, settings):
        return await deny(update)
    await update.effective_message.reply_text(
        'Price Hunter Radar connecté.\n'
        '/help — commandes\n/status — état\n/watchlist — produits suivis\n'
        '/add <produit> — ajouter\n/remove <produit> — retirer\n/review — candidats à vérifier\n/approve <id> — approuver sans publier\n/reject <id> — rejeter\n'
        '/testchannel — tester la publication sur le canal\n'
        '/scan — lancer un scan\n/pause et /resume — surveillance'
    )


async def help_command(update, context):
    settings, _ = services(context)
    if not allowed(update, settings):
        return await deny(update)
    await update.effective_message.reply_text(
        '/status\n/watchlist\n/add <produit>\n/remove <produit>\n'
        '/review\n/approve <id> (sans publier)\n/reject <id>\n/testchannel\n/scan\n/pause\n/resume'
    )


async def status(update, context):
    settings, store = services(context)
    if not allowed(update, settings):
        return await deny(update)
    engine = context.application.bot_data['price_engine']
    budget = engine.budget_status()
    pending = len(engine.list_review('pending', limit=1000))
    scan_state = 'activé' if settings.scanner_enabled else 'désactivé (source produit non configurée)'
    channel_state = 'configuré' if settings.telegram_channel_id else 'non configuré'
    await update.effective_message.reply_text(
        f'Bot Telegram : opérationnel\nCanal d’alertes : {channel_state}\n'
        f'Scanner : {scan_state}\nPause : {"oui" if store.is_paused() else "non"}\n'
        f'Produits suivis : {len(store.list_watchlist())}\nReview Queue : {pending} en attente\n'\n        f'Budget API : {budget[\"requests_used\"]}/{budget[\"requests_limit\"]} appels, {budget[\"estimated_usd\"]:.4f}/{budget[\"usd_limit\"]:.2f} USD estimés'
    )


async def watchlist(update, context):
    settings, store = services(context)
    if not allowed(update, settings):
        return await deny(update)
    items = store.list_watchlist()
    await update.effective_message.reply_text(
        'Watchlist vide.' if not items else 'Produits suivis :\n' + '\n'.join('• ' + x for x in items)
    )


async def add(update, context):
    settings, store = services(context)
    if not allowed(update, settings):
        return await deny(update)
    query = ' '.join(context.args).strip()
    if not query:
        return await update.effective_message.reply_text('Utilisation : /add <produit>')
    await update.effective_message.reply_text('Ajouté.' if store.add_watch(query) else 'Déjà présent.')


async def remove(update, context):
    settings, store = services(context)
    if not allowed(update, settings):
        return await deny(update)
    query = ' '.join(context.args).strip()
    if not query:
        return await update.effective_message.reply_text('Utilisation : /remove <produit>')
    await update.effective_message.reply_text('Retiré.' if store.remove_watch(query) else 'Introuvable.')


async def pause(update, context):
    settings, store = services(context)
    if not allowed(update, settings):
        return await deny(update)
    store.set_paused(True)
    await update.effective_message.reply_text('Surveillance en pause.')


async def resume(update, context):
    settings, store = services(context)
    if not allowed(update, settings):
        return await deny(update)
    store.set_paused(False)
    await update.effective_message.reply_text('Surveillance reprise.')


async def test_channel(update, context):
    settings, _ = services(context)
    if not allowed(update, settings):
        return await deny(update)
    if not settings.telegram_channel_id:
        return await update.effective_message.reply_text('Canal non configuré : renseigne TELEGRAM_CHANNEL_ID dans les variables secrètes.')
    try:
        sent = await context.bot.send_message(
            chat_id=settings.telegram_channel_id,
            text='✅ Price Hunter Radar — test de publication réussi. Le bot peut publier sur ce canal.'
        )
    except Exception:
        logger.exception('Telegram channel test failed')
        return await update.effective_message.reply_text(
            'Échec de publication. Vérifie que le bot est administrateur du canal et possède le droit de publier.'
        )
    await update.effective_message.reply_text(f'Publication de test envoyée (message {sent.message_id}).')


async def scan(update, context):
    settings, store = services(context)
    if not allowed(update, settings):
        return await deny(update)
    if store.is_paused():
        return await update.effective_message.reply_text('Surveillance en pause.')
    await update.effective_message.reply_text(
        "Scan non disponible : aucune API produit autorisée n'est raccordée. Aucune fausse alerte ne sera générée."
    )



async def review_queue(update, context):
    settings, _ = services(context)
    engine = context.application.bot_data['price_engine']
    if not allowed(update, settings):
        return await deny(update)
    rows = engine.list_review('pending', limit=8)
    if not rows:
        return await update.effective_message.reply_text('Review Queue vide. Les candidats restent non publiés.')
    lines = ['Candidats à vérifier (aucune publication automatique) :']
    for item in rows:
        lines.append(f"#{item['id']} — {item['title']} | {item['current_price']:.2f} {item['currency']} | score {item['score']}/100")
        lines.append(f"   vendeur: {item['seller'] or 'inconnu'} | écart: {item['discount_pct'] or 0:.1f}% | médiane: {item['baseline_price'] or 'N/A'}")
        lines.append(f"   /approve {item['id']} ou /reject {item['id']}")
    await update.effective_message.reply_text('\n'.join(lines))

async def review_decision(update, context, decision):
    settings, _ = services(context)
    engine = context.application.bot_data['price_engine']
    if not allowed(update, settings):
        return await deny(update)
    if not context.args or not context.args[0].isdigit():
        return await update.effective_message.reply_text(f'Usage: /{decision} <id>')
    cid = int(context.args[0])
    if not engine.candidate(cid):
        return await update.effective_message.reply_text('Candidat introuvable.')
    ok = engine.review(cid, 'approved' if decision == 'approve' else 'rejected', 'manual Telegram decision')
    if not ok:
        return await update.effective_message.reply_text('Candidat déjà traité.')
    await update.effective_message.reply_text(f'Candidat #{cid} {decision} : décision enregistrée. Aucune publication automatique.')

async def approve(update, context):
    return await review_decision(update, context, 'approve')

async def reject(update, context):
    return await review_decision(update, context, 'reject')


def main():
    load_dotenv()
    settings = Settings.from_env()
    store = Storage(settings.database_path)
    engine = PriceEngine(settings.database_path)
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data.update(settings=settings, storage=store, price_engine=engine)
    handlers = [
        ('start', start), ('help', help_command), ('status', status),
        ('watchlist', watchlist), ('add', add), ('remove', remove),
        ('pause', pause), ('resume', resume), ('scan', scan),
        ('testchannel', test_channel), ('review', review_queue),
        ('approve', approve), ('reject', reject),
    ]
    for command, handler in handlers:
        app.add_handler(CommandHandler(command, handler))
    logger.info('Starting Price Hunter Radar')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
