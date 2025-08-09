#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import os
import logging
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiException

from config import ADMIN_CHAT_ID, REGISTRATION_PASSWORD, logger
from database import db_manager
from states import state_manager
from utils import (
    parse_matti_file_content, create_temp_file_from_content, 
    cleanup_temp_file, format_username, format_user_info,
    create_leaderboard_text, save_text_to_temp_file, escape_markdown_v1
)

# ————— HANDLER COMANDI BASE —————
def handle_start(bot, msg: types.Message):
    chat_id = msg.chat.id
    db_manager.register_user(
        chat_id, 
        msg.from_user.username or "", 
        msg.from_user.first_name or ""
    )
    
    row = db_manager.get_user_rank_and_points(chat_id)
    
    # Se non registrato o in attesa di password
    if not row:
        state_manager.set_pending_password(chat_id)
        bot.send_message(
            chat_id, 
            "🔒 Per registrarti, inserisci la password:",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id, 
            "✅ Sei già registrato! Usa /report per segnalare un matto.",
            parse_mode="Markdown"
        )

def handle_help(bot, msg: types.Message):
    help_text = """
📜 *Lista comandi disponibili:*

/start - Registrati al bot
/report - Segnala un matto
/listmatti - Mostra la lista dei matti disponibili
/classifica - Classifica completa
/galleria_utente - Visualizza le segnalazioni di un utente
/galleria_matto - Visualizza tutte le segnalazioni di un matto
/me - Mostra la tua posizione in classifica

"""
    bot.send_message(msg.chat.id, help_text, parse_mode="Markdown")

def handle_password(bot, msg: types.Message):
    chat_id = msg.chat.id
    password = msg.text.strip()
    
    if password == REGISTRATION_PASSWORD:
        state_manager.remove_pending_password(chat_id)
        db_manager.set_registered(chat_id, True)
        bot.send_message(
            chat_id, 
            "✅ Password corretta! Sei registrato. Usa /report per segnalare un matto.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id, 
            "❌ Password errata. Riprova o contatta l'amministratore.",
            parse_mode="Markdown"
        )

def handle_me(bot, msg: types.Message):
    data = db_manager.get_user_rank_and_points(msg.chat.id)
    if not data:
        bot.send_message(msg.chat.id, "🤔 Non sei registrato. Usa /start.")
        return
    
    bot.send_message(
        msg.chat.id,
        f"Sei *#{data['rank']}* in classifica con *{data['total_points']} punti*.",
        parse_mode="Markdown"
    )

def handle_leaderboard(bot, msg: types.Message):
    top = db_manager.get_leaderboard(10)
    text = create_leaderboard_text(top, "🏆 *Classifica – Top10*", True, 10)
    bot.send_message(msg.chat.id, text, parse_mode="MarkdownV2")

def handle_full_leaderboard(bot, msg: types.Message):
    all_users = db_manager.get_leaderboard()
    
    # Crea il testo della classifica senza markdown problematico
    if not all_users:
        text = "🏆 Classifica Completa\nLa classifica è vuota!"
    else:
        text = "🏆 Classifica Completa\n"
        for i, row in enumerate(all_users):
            usr = format_username(row['username'], row['first_name'], row['chat_id'])
            pts = row['total_points']
            text += f"🔹 {i+1}. {usr} – {pts} punti\n"
    
    # Se il messaggio è troppo lungo, invialo come file
    if len(text) > 4000:
        tmp_path = save_text_to_temp_file(text)
        try:
            with open(tmp_path, "rb") as f:
                bot.send_document(msg.chat.id, f, caption="Classifica completa")
        finally:
            cleanup_temp_file(tmp_path)
    else:
        # Invia senza parse_mode per evitare problemi di parsing
        bot.send_message(msg.chat.id, text, parse_mode=None)

def handle_unregister(bot, msg: types.Message):
    db_manager.unregister_user(msg.chat.id)
    bot.send_message(
        msg.chat.id, 
        "❌ Non riceverai più notifiche finché non fai /start di nuovo."
    )

def handle_listmatti(bot, msg: types.Message):
    items = db_manager.list_matti()
    if not items:
        bot.send_message(
            msg.chat.id, 
            "📂 Lista matti vuota. L'admin può usare /upload_matti per caricarla.",
            parse_mode=None
        )
        return
    
    text = "Lista matti disponibili:\n"
    for itm in items:
        # Escape del nome del matto per evitare problemi
        safe_name = escape_markdown_v1(itm['name'])
        text += f"• {safe_name} – {itm['points']} punti\n"
    
    bot.send_message(msg.chat.id, text, parse_mode=None)

# ————— HANDLER GALLERIE —————
def handle_galleria_utente(bot, msg: types.Message):
    users = db_manager.get_registered_users()
    if not users:
        bot.send_message(msg.chat.id, "👥 Nessun utente registrato.")
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for user in users:
        username = format_username(user['username'], user['first_name'], user['chat_id'])
        markup.add(InlineKeyboardButton(
            text=username,
            callback_data=f"select_user|{user['chat_id']}"
        ))
    
    bot.send_message(
        msg.chat.id, 
        "👤 Scegli un utente per vedere la sua galleria:", 
        reply_markup=markup
    )

def handle_galleria_matto(bot, msg: types.Message):
    items = db_manager.list_matti()
    if not items:
        bot.send_message(
            msg.chat.id, 
            "📂 Nessun matto definito.",
            parse_mode=None
        )
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    for itm in items:
        markup.add(InlineKeyboardButton(
            text=f"{itm['name']} ({itm['points']} punti)",
            callback_data=f"select_matto|{itm['id']}"
        ))
    
    bot.send_message(
        msg.chat.id, 
        "🏞️ Scegli un matto per vedere la sua galleria:", 
        reply_markup=markup
    )

# ————— HANDLER ADMIN —————
def handle_setpunti(bot, msg: types.Message):
    if msg.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(msg, "❌ Comando riservato all'amministratore.")
        return

    users = db_manager.get_registered_users()
    if not users:
        bot.send_message(msg.chat.id, "⚠️ Nessun partecipante registrato.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for user in users:
        nome = user["first_name"] or user["username"] or str(user["chat_id"])
        markup.add(InlineKeyboardButton(
            f"{nome}", callback_data=f"modifica_punti|{user['chat_id']}"
        ))

    bot.send_message(msg.chat.id, "👤 Seleziona un utente per aggiornare i punti:", reply_markup=markup)

def handle_admin(bot, msg: types.Message):
    if msg.chat.id != ADMIN_CHAT_ID:
        bot.send_message(msg.chat.id, "❌ Comando riservato all'admin!")
        return
    
    users = db_manager.get_registered_users()
    if not users:
        bot.send_message(msg.chat.id, "👥 Nessun utente registrato.")
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for user in users:
        username = format_username(user['username'], user['first_name'], user['chat_id'])
        markup.add(InlineKeyboardButton(
            text=username,
            callback_data=f"manage_user|{user['chat_id']}"
        ))
    
    bot.send_message(
        msg.chat.id, 
        "👤 Scegli un utente per gestire le sue segnalazioni:", 
        reply_markup=markup
    )

def handle_add_matto(bot, msg: types.Message):
    if msg.chat.id != ADMIN_CHAT_ID:
        bot.send_message(msg.chat.id, "❌ Comando riservato all'admin!")
        return
    
    try:
        _, name, points = msg.text.split(' ', 2)
        points = int(points)
        db_manager.add_matto(name, points)
        
        # Escape del nome per il messaggio di conferma
        safe_name = escape_markdown_v1(name)
        bot.send_message(msg.chat.id, f"✅ Matto aggiunto: *{safe_name}* con *{points} punti*", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Errore aggiunta matto: {str(e)}")
        bot.send_message(msg.chat.id, "❌ Formato errato. Usa: /add_matto <nome> <punti>")

def handle_remove_matto(bot, msg: types.Message):
    if msg.chat.id != ADMIN_CHAT_ID:
        bot.send_message(msg.chat.id, "❌ Comando riservato all'admin!")
        return
    
    items = db_manager.list_matti()
    if not items:
        bot.send_message(msg.chat.id, "📂 Nessun matto definito.")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    for itm in items:
        markup.add(InlineKeyboardButton(
            text=f"{itm['name']} ({itm['points']} punti)",
            callback_data=f"remove_matto|{itm['id']}"
        ))
    
    bot.send_message(
        msg.chat.id, 
        "❌ Scegli un matto da rimuovere:", 
        reply_markup=markup
    )

def handle_upload_matti(bot, msg: types.Message):
    if msg.chat.id != ADMIN_CHAT_ID:
        bot.send_message(msg.chat.id, "❌ Comando riservato all'admin!")
        return
    
    state_manager.set_admin_upload_pending(True)
    bot.send_message(
        msg.chat.id, 
        "📄 Invia ora il file .txt con la lista (ogni riga: nome, punti).",
        parse_mode=None
    )

def handle_document(bot, msg: types.Message):
    if msg.chat.id != ADMIN_CHAT_ID or not state_manager.is_admin_upload_pending():
        return
    
    doc = msg.document
    if not doc.file_name.lower().endswith(".txt"):
        bot.send_message(msg.chat.id, "❌ Per favore invia un file di testo .txt.", parse_mode=None)
        state_manager.set_admin_upload_pending(False)
        return
    
    try:
        file_info = bot.get_file(doc.file_id)
        content = bot.download_file(file_info.file_path).decode("utf-8")
        
        matti_data = parse_matti_file_content(content)
        count = db_manager.load_matti_from_data(matti_data)
        
        state_manager.set_admin_upload_pending(False)
        bot.send_message(msg.chat.id, f"✅ Caricati {count} matti nel database (aggiunti/aggiornati senza sovrascrivere).")
        
    except Exception as e:
        logger.error(f"Errore caricamento matti: {str(e)}")
        bot.send_message(msg.chat.id, f"❌ Errore durante il caricamento: {str(e)}")
        state_manager.set_admin_upload_pending(False)

def handle_modifica_punti(bot, msg: types.Message):
    admin_id = msg.chat.id
    target_id = state_manager.get_awaiting_point_update(admin_id)
    
    if not target_id:
        return
    
    state_manager.remove_awaiting_point_update(admin_id)

    try:
        nuovo_punteggio = int(msg.text.strip())
    except ValueError:
        bot.send_message(admin_id, "❌ Inserisci un numero valido.")
        return

    db_manager.update_user_points(target_id, nuovo_punteggio)
    
    users = db_manager.get_registered_users()
    user = next((u for u in users if u['chat_id'] == target_id), None)
    
    if user:
        nome = user["first_name"] or user["username"] or str(target_id)
        safe_nome = escape_markdown_v1(nome)
        bot.send_message(admin_id, f"✅ Il punteggio di *{safe_nome}* è stato aggiornato a *{nuovo_punteggio}*.", parse_mode="Markdown")

# ————— HANDLER REPORT E FOTO —————
def handle_report(bot, msg: types.Message):
    chat_id = msg.chat.id
    user_data = db_manager.get_user_rank_and_points(chat_id)
    
    if not user_data:
        bot.send_message(chat_id, "❌ Devi prima registrarti con /start.")
        return
    
    items = db_manager.list_matti()
    if not items:
        bot.send_message(
            chat_id, 
            "📂 Nessun matto definito. L'admin può caricarli con /upload_matti.",
            parse_mode=None
        )
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    for itm in items:
        markup.add(InlineKeyboardButton(
            text=f"{itm['name']} ({itm['points']} punti)",
            callback_data=f"matto|{itm['id']}"
        ))
    
    bot.send_message(
        chat_id, 
        "🏹 Scegli il matto cliccando sul pulsante:", 
        reply_markup=markup
    )

def handle_photo(bot, msg: types.Message):
    chat_id = msg.chat.id
    if not state_manager.has_pending_matto(chat_id):
        return
    
    info = state_manager.remove_pending_matto(chat_id)
    matto_id = info["id"]
    name = info["name"]
    pts = info["points"]
    first = info["first_name"]
    uname = info["username"]
    file_id = msg.photo[-1].file_id
    
    # Controlla se è un'arma (punti negativi)
    if pts < 0:
        state_manager.set_pending_weapon_target(chat_id, {
            "matto_id": matto_id,
            "points": pts,
            "file_id": file_id,
            "first_name": first,
            "username": uname
        })
        
        users = db_manager.get_registered_users()
        if not users:
            bot.send_message(chat_id, "👥 Nessun giocatore registrato per usare l'arma!")
            return
        
        markup = InlineKeyboardMarkup(row_width=1)
        for user in users:
            if user['chat_id'] == chat_id:
                continue  # Salta se stesso
                
            username = format_username(user['username'], user['first_name'], user['chat_id'])
            markup.add(InlineKeyboardButton(
                text=username,
                callback_data=f"use_weapon|{user['chat_id']}"
            ))
        
        bot.send_message(
            chat_id, 
            f"💥 Hai trovato un'arma! {name} ha {pts} punti.\n"
            "Scegli un giocatore a cui assegnare i punti negativi:",
            reply_markup=markup,
            parse_mode=None
        )
        return
    
    # Matto normale (punti positivi)
    db_manager.add_sighting(chat_id, matto_id, pts, file_id)
    
    user_data = db_manager.get_user_rank_and_points(chat_id)
    total_pts = user_data["total_points"] if user_data else 0
    
    # Prepara i testi senza formattazione Markdown
    user_info = format_user_info(uname, first)
    text = (
        f"📸 {user_info} ha trovato il matto {name} ➕ {pts} punti\n"
        f"🏅 Ora ha {total_pts} punti."
    )
    
    photo_caption = (
        f"Segnalato da: {user_info}\n"
        f"Matto: {name} ({pts} punti)"
    )
    
    # Invia a tutti gli utenti registrati
    sent = 0
    registered_ids = db_manager.get_registered_chat_ids()

    for cid in registered_ids:
        try:
            bot.send_message(cid, text, parse_mode=None)
            bot.send_photo(cid, photo=file_id, caption=photo_caption, parse_mode=None)
            sent += 1

        except ApiException as e:
            error_msg = str(e).lower()
            if any(kw in error_msg for kw in ("blocked", "not found", "deactivated")):
                db_manager.unregister_user(cid)
            else:
                logger.error(f"Errore invio a {cid}: {error_msg}")

        except Exception as e:
            logger.error(f"Errore generico invio a {cid}: {str(e)}")

    bot.send_message(chat_id, f"✅ Segnalazione inviata a {sent} utenti.", parse_mode=None)
