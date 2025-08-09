#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Import delle configurazioni e moduli
from config import BOT_TOKEN, logger
from database import db_manager
from states import state_manager
import handlers
import callbacks

# Inizializza il bot
bot = TeleBot(BOT_TOKEN)

# ————— REGISTRAZIONE HANDLER COMANDI —————
@bot.message_handler(commands=["start"])
def cmd_start(msg: types.Message):
    handlers.handle_start(bot, msg)

@bot.message_handler(commands=["comandi", "help"])
def cmd_help(msg: types.Message):
    handlers.handle_help(bot, msg)

@bot.message_handler(func=lambda message: state_manager.has_pending_password(message.chat.id))
def handler_password(msg: types.Message):
    handlers.handle_password(bot, msg)

@bot.message_handler(commands=["me"])
def cmd_me(msg: types.Message):
    handlers.handle_me(bot, msg)

@bot.message_handler(commands=["leaderboard"])
def cmd_leaderboard(msg: types.Message):
    handlers.handle_leaderboard(bot, msg)

@bot.message_handler(commands=["classifica"])
def cmd_classifica(msg: types.Message):
    handlers.handle_full_leaderboard(bot, msg)

@bot.message_handler(commands=["unregister"])
def cmd_unregister(msg: types.Message):
    handlers.handle_unregister(bot, msg)

@bot.message_handler(commands=["listmatti"])
def cmd_listmatti(msg: types.Message):
    handlers.handle_listmatti(bot, msg)

@bot.message_handler(commands=["galleria_utente"])
def cmd_galleria_utente(msg: types.Message):
    handlers.handle_galleria_utente(bot, msg)

@bot.message_handler(commands=["galleria_matto"])
def cmd_galleria_matto(msg: types.Message):
    handlers.handle_galleria_matto(bot, msg)

@bot.message_handler(commands=["setpunti"])
def cmd_setpunti(msg: types.Message):
    handlers.handle_setpunti(bot, msg)

@bot.message_handler(commands=["admin"])
def cmd_admin(msg: types.Message):
    handlers.handle_admin(bot, msg)

@bot.message_handler(commands=["add_matto"])
def cmd_add_matto(msg: types.Message):
    handlers.handle_add_matto(bot, msg)

@bot.message_handler(commands=["remove_matto"])
def cmd_remove_matto(msg: types.Message):
    handlers.handle_remove_matto(bot, msg)

@bot.message_handler(commands=["upload_matti"])
def cmd_upload_matti(msg: types.Message):
    handlers.handle_upload_matti(bot, msg)

@bot.message_handler(commands=["suggest"])
def cmd_suggest(msg: types.Message):
    handlers.handle_suggest(bot, msg)

@bot.message_handler(commands=["suggest_file"])
def cmd_suggest_file(msg: types.Message):
    handlers.handle_suggest_file(bot, msg)

@bot.message_handler(commands=["my_suggestions"])
def cmd_my_suggestions(msg: types.Message):
    handlers.handle_my_suggestions(bot, msg)

@bot.message_handler(commands=["review_suggestions"])
def cmd_review_suggestions(msg: types.Message):
    handlers.handle_review_suggestions(bot, msg)

@bot.message_handler(content_types=["document"])
def handler_document(msg: types.Message):
    # Gestisce sia upload admin che suggerimenti utenti
    if msg.chat.id == ADMIN_CHAT_ID and state_manager.is_admin_upload_pending():
        handlers.handle_document(bot, msg)
    elif state_manager.is_suggestion_upload_pending(msg.chat.id):
        handlers.handle_suggestion_document(bot, msg)

@bot.message_handler(func=lambda msg: state_manager.has_awaiting_point_update(msg.chat.id))
def handler_modifica_punti(msg: types.Message):
    handlers.handle_modifica_punti(bot, msg)

@bot.message_handler(func=lambda msg: state_manager.has_pending_suggestion_name(msg.chat.id))
def handler_suggestion_name(msg: types.Message):
    handlers.handle_suggestion_name(bot, msg)

@bot.message_handler(func=lambda msg: state_manager.has_pending_suggestion_points(msg.chat.id))
def handler_suggestion_points(msg: types.Message):
    handlers.handle_suggestion_points(bot, msg)

@bot.message_handler(func=lambda msg: state_manager.has_pending_suggestion_review(msg.chat.id))
def handler_suggestion_review_notes(msg: types.Message):
    handlers.handle_suggestion_review_notes(bot, msg)

@bot.message_handler(commands=["report"])
def cmd_report(msg: types.Message):
    handlers.handle_report(bot, msg)

@bot.message_handler(content_types=["photo"])
def handler_photo(msg: types.Message):
    handlers.handle_photo(bot, msg)

# ————— NUOVO HANDLER PER I VIDEO —————
@bot.message_handler(content_types=["video"])
def handler_video(msg: types.Message):
    handlers.handle_video(bot, msg)

# ————— REGISTRAZIONE CALLBACK HANDLER —————
@bot.callback_query_handler(func=lambda call: call.data.startswith("matto|"))
def callback_matto_handler(call: types.CallbackQuery):
    callbacks.callback_matto(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_matto|"))
def callback_remove_matto_handler(call: types.CallbackQuery):
    callbacks.callback_remove_matto(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_user|"))
def callback_select_user_handler(call: types.CallbackQuery):
    callbacks.callback_select_user(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_matto|"))
def callback_select_matto_handler(call: types.CallbackQuery):
    callbacks.callback_select_matto(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("modifica_punti|"))
def callback_modifica_punti_handler(call: types.CallbackQuery):
    callbacks.callback_modifica_punti(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("manage_user|"))
def callback_manage_user_handler(call: types.CallbackQuery):
    callbacks.callback_manage_user(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_sighting|"))
def callback_delete_sighting_handler(call: types.CallbackQuery):
    callbacks.callback_delete_sighting(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("use_weapon|"))
def callback_use_weapon_handler(call: types.CallbackQuery):
    callbacks.callback_use_weapon(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("gallery_mode|"))
def callback_gallery_mode_handler(call: types.CallbackQuery):
    callbacks.callback_gallery_mode(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("matto_mode|"))
def callback_matto_mode_handler(call: types.CallbackQuery):
    callbacks.callback_matto_mode(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_suggestion"))
def callback_approve_suggestion_handler(call: types.CallbackQuery):
    callbacks.callback_approve_suggestion(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_suggestion"))
def callback_reject_suggestion_handler(call: types.CallbackQuery):
    callbacks.callback_reject_suggestion(bot, call)

# ————— AVVIO BOT —————
if __name__ == "__main__":
    try:
        # Inizializza il database
        db_manager.init_db()
        db_manager.upgrade_db()
        
        logger.info("Bot avviato – in attesa di comandi.")
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot fermato dall'utente")
    except Exception as e:
        logger.error(f"Errore critico: {str(e)}")
    finally:
        # Pulizia risorse
        state_manager.cleanup_all_states()
        db_manager.close()
        logger.info("Risorse pulite, bot terminato")
