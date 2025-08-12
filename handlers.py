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
🤖 *FantaMatto Bot - Lista Comandi*

*🎮 COMANDI PRINCIPALI*
/start - Registrati al gioco
/report - 📸 Segnala un matto avvistato
/me - 🏅 La tua posizione in classifica

*📊 CLASSIFICHE E STATISTICHE*
/leaderboard - 🏆 Top 10 giocatori
/classifica - 📋 Classifica completa

*🔍 GALLERIE*
/galleria_utente - 👤 Vedi le segnalazioni di un utente
/galleria_matto - 🏞️ Vedi tutte le segnalazioni di un matto
/listmatti - 📂 Lista di tutti i matti disponibili

*💡 SUGGERIMENTI*
/suggest - ✍️ Suggerisci un nuovo matto
/suggest_file - 📄 Suggerisci più matti tramite file
/my_suggestions - 📝 I tuoi suggerimenti inviati

*❓ AIUTO*
/help - 📜 Mostra questo messaggio
/comandi - 📜 Alias per /help

*⚙️ ADMIN* (solo amministratore)
/admin - 👨‍💼 Gestione utenti e segnalazioni
/review_suggestions - 💡 Approva/rifiuta suggerimenti
/add_matto - ➕ Aggiungi un matto manualmente
/remove_matto - ❌ Rimuovi un matto
/upload_matti - 📤 Carica matti da file
/setpunti - 🔢 Modifica punti di un utente

🎯 *Come giocare:*
1️⃣ Registrati con /start
2️⃣ Trova un "matto" nella vita reale
3️⃣ Usa /report per segnalarlo
4️⃣ Invia la foto/video come prova
5️⃣ Guadagna punti e scala la classifica! 🏆
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

# ————— HANDLER REPORT E FOTO/VIDEO —————
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
    """Gestisce le foto per le segnalazioni"""
    chat_id = msg.chat.id
    if not state_manager.has_pending_matto(chat_id):
        return
    
    file_id = msg.photo[-1].file_id
    media_type = "photo"
    process_media_sighting(bot, msg, file_id, media_type)

def handle_video(bot, msg: types.Message):
    """Gestisce i video per le segnalazioni"""
    chat_id = msg.chat.id
    if not state_manager.has_pending_matto(chat_id):
        return
    
    file_id = msg.video.file_id
    media_type = "video"
    process_media_sighting(bot, msg, file_id, media_type)

def process_media_sighting(bot, msg: types.Message, file_id: str, media_type: str):
    """Processa una segnalazione con media (foto o video)"""
    chat_id = msg.chat.id
    info = state_manager.remove_pending_matto(chat_id)
    matto_id = info["id"]
    name = info["name"]
    pts = info["points"]
    first = info["first_name"]
    uname = info["username"]
    
    # Controlla se è un'arma (punti negativi)
    if pts < 0:
        state_manager.set_pending_weapon_target(chat_id, {
            "matto_id": matto_id,
            "points": pts,
            "file_id": file_id,
            "media_type": media_type,
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
        
        media_emoji = "📹" if media_type == "video" else "📸"
        bot.send_message(
            chat_id, 
            f"💥 Hai trovato un'arma! {name} ha {pts} punti.\n"
            "Scegli un giocatore a cui assegnare i punti negativi:",
            reply_markup=markup,
            parse_mode=None
        )
        return
    
    # Matto normale (punti positivi)
    db_manager.add_sighting(chat_id, matto_id, pts, file_id, media_type=media_type)
    
    user_data = db_manager.get_user_rank_and_points(chat_id)
    total_pts = user_data["total_points"] if user_data else 0
    
    # Prepara i testi senza formattazione Markdown
    user_info = format_user_info(uname, first)
    media_emoji = "📹" if media_type == "video" else "📸"
    text = (
        f"{media_emoji} {user_info} ha trovato il matto {name} ➕ {pts} punti\n"
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
            
            # Invia il media appropriato
            if media_type == "video":
                bot.send_video(cid, video=file_id, caption=photo_caption, parse_mode=None)
            else:
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

# ————— HANDLER ADMIN SUGGERIMENTI —————
def handle_review_suggestions(bot, msg: types.Message):
    """Mostra i suggerimenti in attesa di approvazione (solo admin)"""
    if msg.chat.id != ADMIN_CHAT_ID:
        bot.send_message(msg.chat.id, "❌ Comando riservato all'admin!")
        return
    
    suggestions = db_manager.get_pending_suggestions()
    
    if not suggestions:
        bot.send_message(msg.chat.id, "📭 Nessun suggerimento in attesa di approvazione.")
        return
    
    bot.send_message(msg.chat.id, "💡 *Suggerimenti in attesa di approvazione:*", parse_mode="Markdown")
    
    for s in suggestions:
        user_info = format_username(s['username'], s['first_name'], s['user_chat_id'])
        points_text = f"{s['suggested_points']} punti" if s['suggested_points'] >= 0 else f"{s['suggested_points']} punti (arma)"
        
        # Escape dei caratteri speciali per evitare errori di parsing
        safe_user_info = escape_markdown_v1(user_info)
        safe_matto_name = escape_markdown_v1(s['suggested_name'])
        safe_points_text = escape_markdown_v1(points_text)
        
        text = (
            f"📝 *{safe_matto_name}* ({safe_points_text})\n"
            f"👤 Suggerito da: {safe_user_info}\n"
            f"📅 Data: {s['created_at'][:10]}"
        )
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Approva", callback_data=f"approve_suggestion|{s['id']}"),
            InlineKeyboardButton("❌ Rifiuta", callback_data=f"reject_suggestion|{s['id']}")
        )
        markup.row(
            InlineKeyboardButton("✅ Approva senza note", callback_data=f"approve_suggestion_silent|{s['id']}"),
            InlineKeyboardButton("❌ Rifiuta senza note", callback_data=f"reject_suggestion_silent|{s['id']}")
        )
        
        try:
            bot.send_message(msg.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Errore invio suggerimento con Markdown: {str(e)}")
            # Fallback: invia senza markdown
            try:
                fallback_text = (
                    f"📝 {s['suggested_name']} ({points_text})\n"
                    f"👤 Suggerito da: {user_info}\n"
                    f"📅 Data: {s['created_at'][:10]}"
                )
                bot.send_message(msg.chat.id, fallback_text, reply_markup=markup, parse_mode=None)
            except Exception as e2:
                logger.error(f"Errore anche nel fallback review: {str(e2)}")

def handle_suggestion_review_notes(bot, msg: types.Message):
    """Gestisce l'inserimento delle note per la review di un suggerimento"""
    admin_chat_id = msg.chat.id
    review_info = state_manager.get_pending_suggestion_review(admin_chat_id)
    
    if not review_info:
        return
    
    state_manager.remove_pending_suggestion_review(admin_chat_id)
    suggestion_id = review_info['suggestion_id']
    action = review_info['action']
    notes = msg.text.strip()
    
    # Ottieni i dettagli del suggerimento
    suggestion = db_manager.get_suggestion_by_id(suggestion_id)
    if not suggestion:
        bot.send_message(admin_chat_id, "❌ Suggerimento non trovato!")
        return
    
    # Esegui l'azione
    if action == 'approve':
        success = db_manager.approve_suggestion(suggestion_id, notes)
        if success:
            bot.send_message(
                admin_chat_id,
                f"✅ Matto *{suggestion['suggested_name']}* approvato e aggiunto!",
                parse_mode="Markdown"
            )
            
            # Notifica all'utente
            user_text = (
                f"🎉 *Suggerimento approvato!*\n\n"
                f"📝 Il tuo matto *{suggestion['suggested_name']}* ({suggestion['suggested_points']} punti) è stato aggiunto al gioco!"
            )
            if notes:
                user_text += f"\n\n📝 Note dell'admin: _{notes}_"
            
            try:
                bot.send_message(suggestion['user_chat_id'], user_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Errore notifica utente approvazione: {str(e)}")
        else:
            bot.send_message(admin_chat_id, "❌ Errore durante l'approvazione!")
    
    elif action == 'reject':
        success = db_manager.reject_suggestion(suggestion_id, notes)
        if success:
            bot.send_message(
                admin_chat_id,
                f"❌ Suggerimento *{suggestion['suggested_name']}* rifiutato.",
                parse_mode="Markdown"
            )
            
            # Notifica all'utente
            user_text = (
                f"😔 *Suggerimento rifiutato*\n\n"
                f"📝 Il tuo matto *{suggestion['suggested_name']}* non è stato approvato."
            )
            if notes:
                user_text += f"\n\n📝 Motivo: _{notes}_"
            
            try:
                bot.send_message(suggestion['user_chat_id'], user_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Errore notifica utente rifiuto: {str(e)}")
        else:
            bot.send_message(admin_chat_id, "❌ Errore durante il rifiuto!")

# ————— HANDLER SUGGERIMENTI —————
def handle_suggest(bot, msg: types.Message):
    """Inizia il processo di suggerimento di un nuovo matto"""
    chat_id = msg.chat.id
    user_data = db_manager.get_user_rank_and_points(chat_id)
    
    if not user_data:
        bot.send_message(chat_id, "❌ Devi prima registrarti con /start.")
        return
    
    state_manager.set_pending_suggestion_name(chat_id)
    bot.send_message(
        chat_id,
        "💡 *Suggerisci un nuovo matto!*\n\nInvia il nome del matto che vuoi suggerire:",
        parse_mode="Markdown"
    )

def handle_suggestion_name(bot, msg: types.Message):
    """Gestisce l'inserimento del nome del matto suggerito"""
    chat_id = msg.chat.id
    matto_name = msg.text.strip()
    
    if not matto_name:
        bot.send_message(chat_id, "❌ Il nome non può essere vuoto. Riprova:")
        return
    
    state_manager.remove_pending_suggestion_name(chat_id)
    state_manager.set_pending_suggestion_points(chat_id, matto_name)
    
    bot.send_message(
        chat_id,
        f"📝 Nome scelto: *{matto_name}*\n\nOra invia i punti (numero intero, può essere negativo per le armi):",
        parse_mode="Markdown"
    )

def handle_suggestion_points(bot, msg: types.Message):
    """Gestisce l'inserimento dei punti del matto suggerito"""
    chat_id = msg.chat.id
    matto_name = state_manager.get_pending_suggestion_points(chat_id)
    
    try:
        points = int(msg.text.strip())
    except ValueError:
        bot.send_message(chat_id, "❌ Inserisci un numero valido:")
        return
    
    state_manager.remove_pending_suggestion_points(chat_id)
    
    # Salva il suggerimento nel database
    suggestion_id = db_manager.add_suggestion(chat_id, matto_name, points)
    
    # Notifica all'utente
    points_text = f"{points} punti" if points >= 0 else f"{points} punti (arma)"
    bot.send_message(
        chat_id,
        f"✅ Suggerimento inviato!\n\n"
        f"📝 Matto: *{matto_name}*\n"
        f"🎯 Punti: *{points_text}*\n\n"
        f"L'admin riceverà la tua proposta per l'approvazione.",
        parse_mode="Markdown"
    )
    
    # Notifica all'admin
    users = db_manager.get_registered_users()
    user = next((u for u in users if u['chat_id'] == chat_id), None)
    user_info = format_username(user['username'], user['first_name'], user['chat_id']) if user else "Utente sconosciuto"
    
    # Escape dei caratteri speciali per evitare errori di parsing
    safe_user_info = escape_markdown_v1(user_info)
    safe_matto_name = escape_markdown_v1(matto_name)
    safe_points_text = escape_markdown_v1(points_text)
    
    admin_text = (
        f"💡 *Nuovo suggerimento matto!*\n\n"
        f"👤 Da: {safe_user_info}\n"
        f"📝 Nome: *{safe_matto_name}*\n"
        f"🎯 Punti: *{safe_points_text}*\n\n"
        f"Usa /review_suggestions per gestire i suggerimenti."
    )
    
    try:
        bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Errore notifica admin suggerimento: {str(e)}")
        # Fallback: invia senza markdown
        try:
            fallback_text = (
                f"💡 Nuovo suggerimento matto!\n\n"
                f"👤 Da: {user_info}\n"
                f"📝 Nome: {matto_name}\n"
                f"🎯 Punti: {points_text}\n\n"
                f"Usa /review_suggestions per gestire i suggerimenti."
            )
            bot.send_message(ADMIN_CHAT_ID, fallback_text, parse_mode=None)
        except Exception as e2:
            logger.error(f"Errore anche nel fallback: {str(e2)}")

def handle_suggest_file(bot, msg: types.Message):
    """Inizia il processo di caricamento file con suggerimenti"""
    chat_id = msg.chat.id
    user_data = db_manager.get_user_rank_and_points(chat_id)
    
    if not user_data:
        bot.send_message(chat_id, "❌ Devi prima registrarti con /start.")
        return
    
    state_manager.set_suggestion_upload_pending(chat_id, True)
    bot.send_message(
        chat_id,
        "📄 *Suggerisci più matti tramite file!*\n\n"
        "Invia un file .txt con il formato:\n"
        "`nome_matto,punti`\n\n"
        "Esempio:\n"
        "`pepp u sorrident,-10`\n"
        "`mario u pazz,5`",
        parse_mode="Markdown"
    )

def handle_suggestion_document(bot, msg: types.Message):
    """Gestisce il caricamento del file con suggerimenti"""
    chat_id = msg.chat.id
    
    if not state_manager.is_suggestion_upload_pending(chat_id):
        return
    
    doc = msg.document
    if not doc.file_name.lower().endswith(".txt"):
        bot.send_message(chat_id, "❌ Per favore invia un file di testo .txt.")
        return
    
    try:
        file_info = bot.get_file(doc.file_id)
        content = bot.download_file(file_info.file_path).decode("utf-8")
        
        # Parsa il contenuto
        suggestions = parse_matti_file_content(content)
        
        if not suggestions:
            bot.send_message(chat_id, "❌ Nessun suggerimento valido trovato nel file.")
            state_manager.set_suggestion_upload_pending(chat_id, False)
            return
        
        # Salva tutti i suggerimenti
        count = 0
        for name, points in suggestions:
            db_manager.add_suggestion(chat_id, name, points)
            count += 1
        
        state_manager.set_suggestion_upload_pending(chat_id, False)
        
        bot.send_message(
            chat_id,
            f"✅ {count} suggerimenti inviati con successo!\n\n"
            f"L'admin riceverà le tue proposte per l'approvazione.",
            parse_mode="Markdown"
        )
        
        # Notifica all'admin
        users = db_manager.get_registered_users()
        user = next((u for u in users if u['chat_id'] == chat_id), None)
        user_info = format_username(user['username'], user['first_name'], user['chat_id']) if user else "Utente sconosciuto"
        
        # Escape dei caratteri speciali
        safe_user_info = escape_markdown_v1(user_info)
        
        admin_text = (
            f"💡 *Nuovi suggerimenti matti!*\n\n"
            f"👤 Da: {safe_user_info}\n"
            f"📄 {count} matti suggeriti tramite file\n\n"
            f"Usa /review_suggestions per gestire i suggerimenti."
        )
        
        try:
            bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Errore notifica admin suggerimenti file: {str(e)}")
            # Fallback: invia senza markdown
            try:
                fallback_text = (
                    f"💡 Nuovi suggerimenti matti!\n\n"
                    f"👤 Da: {user_info}\n"
                    f"📄 {count} matti suggeriti tramite file\n\n"
                    f"Usa /review_suggestions per gestire i suggerimenti."
                )
                bot.send_message(ADMIN_CHAT_ID, fallback_text, parse_mode=None)
            except Exception as e2:
                logger.error(f"Errore anche nel fallback: {str(e2)}")
        
    except Exception as e:
        logger.error(f"Errore caricamento suggerimenti: {str(e)}")
        bot.send_message(chat_id, f"❌ Errore durante il caricamento: {str(e)}")
        state_manager.set_suggestion_upload_pending(chat_id, False)

def handle_my_suggestions(bot, msg: types.Message):
    """Mostra i suggerimenti dell'utente"""
    chat_id = msg.chat.id
    user_data = db_manager.get_user_rank_and_points(chat_id)
    
    if not user_data:
        bot.send_message(chat_id, "❌ Devi prima registrarti con /start.")
        return
    
    suggestions = db_manager.get_user_suggestions(chat_id)
    
    if not suggestions:
        bot.send_message(chat_id, "📭 Non hai ancora fatto suggerimenti.")
        return
    
    text = "💡 *I tuoi suggerimenti:*\n\n"
    
    for s in suggestions:
        status_emoji = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }.get(s['status'], '❓')
        
        points_text = f"{s['suggested_points']} punti" if s['suggested_points'] >= 0 else f"{s['suggested_points']} punti (arma)"
        text += f"{status_emoji} *{s['suggested_name']}* ({points_text})\n"
        
        if s['status'] != 'pending' and s['admin_notes']:
            text += f"   📝 Note admin: _{s['admin_notes']}_\n"
        
        text += "\n"
    
    bot.send_message(chat_id, text, parse_mode="Markdown")
