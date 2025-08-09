#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import os
import logging
import uuid  # Aggiunto per generare ID unici per i suggerimenti
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiException

from config import ADMIN_CHAT_ID, REGISTRATION_PASSWORD, logger
from database import db_manager
from states import state_manager
from utils import (
    parse_matti_file_content, create_temp_file_from_content, 
    cleanup_temp_file, format_username, format_user_info,
    create_leaderboard_text, save_text_to_temp_file
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
/suggest - Suggerisci un nuovo matto
/suggest_file - Suggerisci più matti tramite un file .txt

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
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

def handle_full_leaderboard(bot, msg: types.Message):
    all_users = db_manager.get_leaderboard()
    text = create_leaderboard_text(all_users, "🏆 *Classifica Completa*", False)
    
    # Se il messaggio è troppo lungo, invialo come file
    if len(text) > 4000:
        tmp_path = save_text_to_temp_file(text)
        with open(tmp_path, "rb") as f:
            bot.send_document(msg.chat.id, f, caption="Classifica completa")
        cleanup_temp_file(tmp_path)
    else:
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")

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
            "📂 Lista matti vuota\\. L'admin può usare `/upload_matti` per caricarla\\.",
            parse_mode="MarkdownV2"
        )
        return
    
    text = "*Lista matti disponibili:*"
    for itm in items:
        text += f"\n• {itm['name']} – *{itm['points']} punti*"
    
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# ————— HANDLER SUGGERIMENTI UTENTE (NUOVA FUNZIONE) —————
def handle_suggest(bot, msg: types.Message):
    chat_id = msg.chat.id
    if not db_manager.get_user_rank_and_points(chat_id):
        bot.send_message(chat_id, "❌ Devi prima registrarti con /start.")
        return

    bot.send_message(chat_id, "📝 Inserisci il *nome* del matto che vuoi suggerire:", parse_mode="Markdown")
    state_manager.set_awaiting_suggestion_name(chat_id)

def handle_suggest_file(bot, msg: types.Message):
    chat_id = msg.chat.id
    if not db_manager.get_user_rank_and_points(chat_id):
        bot.send_message(chat_id, "❌ Devi prima registrarti con /start.")
        return

    bot.send_message(
        chat_id,
        "📄 Invia un file `.txt` con i tuoi suggerimenti.\n"
        "Ogni riga deve essere nel formato: `nome del matto,punteggio`",
        parse_mode="Markdown"
    )
    state_manager.set_awaiting_suggestion_file(chat_id)

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
            "📂 Nessun matto definito\\.",
            parse_mode="MarkdownV2"
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
        bot.send_message(msg.chat.id, f"✅ Matto aggiunto: *{name}* con *{points} punti*", parse_mode="Markdown")
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
        "📄 Invia ora il file `.txt` con la lista \\(ogni riga: `nome, punti`\\)\\.",
        parse_mode="MarkdownV2"
    )

# ————— HANDLER DOCUMENTI (MODIFICATO) —————
def handle_document(bot, msg: types.Message):
    chat_id = msg.chat.id
    
    # Logica per i file di suggerimento utente
    if state_manager.is_awaiting_suggestion_file(chat_id):
        handle_suggestion_document(bot, msg)
        return
    
    # Logica originale per l'upload admin
    if chat_id != ADMIN_CHAT_ID or not state_manager.is_admin_upload_pending():
        return
    
    doc = msg.document
    if not doc.file_name.lower().endswith(".txt"):
        bot.send_message(msg.chat.id, "❌ Per favore invia un file di testo `.txt`.", parse_mode="Markdown")
        state_manager.set_admin_upload_pending(False)
        return
    
    try:
        file_info = bot.get_file(doc.file_id)
        content = bot.download_file(file_info.file_path).decode("utf-8")
        
        matti_data = parse_matti_file_content(content)
        count = db_manager.load_matti_from_data(matti_data)
        
        state_manager.set_admin_upload_pending(False)
        bot.send_message(msg.chat.id, f"✅ Caricati {count} matti nel database.")
        
    except Exception as e:
        logger.error(f"Errore caricamento matti: {str(e)}")
        bot.send_message(msg.chat.id, f"❌ Errore durante il caricamento: {str(e)}")
        state_manager.set_admin_upload_pending(False)

# ————— NUOVO HANDLER PER FILE SUGGERIMENTI —————
def handle_suggestion_document(bot, msg: types.Message):
    chat_id = msg.chat.id
    state_manager.clear_suggestion_states(chat_id)

    doc = msg.document
    if not doc.file_name.lower().endswith(".txt"):
        bot.send_message(chat_id, "❌ File non valido. Invia un file `.txt`.")
        return

    try:
        file_info = bot.get_file(doc.file_id)
        content = bot.download_file(file_info.file_path).decode("utf-8")
        matti_data = parse_matti_file_content(content)
        
        if not matti_data:
            bot.send_message(chat_id, "⚠️ Il file è vuoto o formattato male. Nessun suggerimento inviato.")
            return

        user_info = format_user_info(msg.from_user.username, msg.from_user.first_name)
        suggestions_sent = 0

        for name, points in matti_data:
            suggestion_id = str(uuid.uuid4())
            suggestion_data = {
                'suggester_id': chat_id, 'suggester_info': user_info,
                'name': name, 'points': points
            }
            state_manager.add_pending_suggestion(suggestion_id, suggestion_data)

            text_to_admin = (f"🔔 *Nuovo suggerimento Matto (da file)*\n\n"
                             f"Da: {user_info}\n"
                             f"Nome: *{name}*\n"
                             f"Punti: *{points}*")
            
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ Approva", callback_data=f"review_suggestion|approve|{suggestion_id}"),
                InlineKeyboardButton("❌ Rifiuta", callback_data=f"review_suggestion|reject|{suggestion_id}")
            )

            try:
                bot.send_message(ADMIN_CHAT_ID, text_to_admin, reply_markup=markup, parse_mode="Markdown")
                suggestions_sent += 1
            except Exception as e:
                logger.error(f"Impossibile inviare suggerimento da file all'admin: {e}")

        bot.send_message(chat_id, f"✅ Inviati {suggestions_sent} suggerimenti all'admin per la revisione.")

    except Exception as e:
        logger.error(f"Errore elaborazione file suggerimenti: {str(e)}")
        bot.send_message(chat_id, "❌ Si è verificato un errore durante la lettura del file.")

# ————— HANDLER DI STATO —————
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
        bot.send_message(admin_id, f"✅ Il punteggio di *{nome}* è stato aggiornato a *{nuovo_punteggio}*.", parse_mode="Markdown")

# ————— NUOVI HANDLER CONVERSAZIONALI PER SUGGERIMENTI —————
def handle_suggestion_name(bot, msg: types.Message):
    chat_id = msg.chat.id
    matto_name = msg.text.strip()

    if not matto_name:
        bot.send_message(chat_id, "❌ Il nome non può essere vuoto. Riprova.")
        return
    
    bot.send_message(chat_id, f"👍 Nome: *{matto_name}*.\nOra inserisci il *punteggio* (es. 50, o -20 per un'arma):", parse_mode="Markdown")
    state_manager.set_awaiting_suggestion_points(chat_id, matto_name)

def handle_suggestion_points(bot, msg: types.Message):
    chat_id = msg.chat.id
    
    try:
        points = int(msg.text.strip())
    except ValueError:
        bot.send_message(chat_id, "❌ Punteggio non valido. Inserisci un numero intero.")
        return

    matto_name = state_manager.get_pending_suggestion_name(chat_id)
    state_manager.clear_suggestion_states(chat_id) 

    user_info = format_user_info(msg.from_user.username, msg.from_user.first_name)
    
    suggestion_id = str(uuid.uuid4())
    suggestion_data = {
        'suggester_id': chat_id, 'suggester_info': user_info,
        'name': matto_name, 'points': points
    }
    state_manager.add_pending_suggestion(suggestion_id, suggestion_data)

    text_to_admin = (f"🔔 *Nuovo suggerimento Matto*\n\n"
                     f"Da: {user_info} (`{chat_id}`)\n"
                     f"Nome: *{matto_name}*\n"
                     f"Punti: *{points}*")

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Approva", callback_data=f"review_suggestion|approve|{suggestion_id}"),
        InlineKeyboardButton("❌ Rifiuta", callback_data=f"review_suggestion|reject|{suggestion_id}")
    )

    try:
        bot.send_message(ADMIN_CHAT_ID, text_to_admin, reply_markup=markup, parse_mode="Markdown")
        bot.send_message(chat_id, "✅ Suggerimento inviato all'admin per la revisione.")
    except Exception as e:
        bot.send_message(chat_id, "⚠️ Impossibile inviare il suggerimento. Riprova più tardi.")
        logger.error(f"Impossibile inviare suggerimento all'admin: {e}")

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
            "📂 Nessun matto definito\\. L'admin può caricarli con `/upload_matti`\\.",
            parse_mode="MarkdownV2"
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
                continue
                
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
    
    user_info = format_user_info(uname, first)
    text = (
        f"📸 {user_info} ha trovato il matto {name} ➕ {pts} punti\n"
        f"🏅 Ora ha {total_pts} punti."
    )
    
    photo_caption = (
        f"Segnalato da: {user_info}\n"
        f"Matto: {name} ({pts} punti)"
    )
    
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
