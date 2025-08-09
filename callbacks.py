#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_CHAT_ID, logger
from database import db_manager
from states import state_manager
from utils import format_username, format_user_info

# ————— CALLBACK MATTO SELECTION —————
def callback_matto(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    parts = call.data.split("|", 1)
    
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    matto_id = int(parts[1])
    matto = db_manager.get_matto_by_id(matto_id)
    
    if not matto:
        bot.answer_callback_query(call.id, "Matto non trovato!", show_alert=True)
        return
    
    name = matto["name"]
    pts = matto["points"]
    
    state_manager.set_pending_matto(chat_id, {
        "id": matto_id, 
        "name": name, 
        "points": pts,
        "first_name": call.from_user.first_name or "",
        "username": call.from_user.username or ""
    })
    
    bot.answer_callback_query(call.id, f"Hai scelto: {name} ({pts} punti)")
    
    # Gestione speciale per punti negativi (armi)
    if pts < 0:
        bot.send_message(
            chat_id, 
            f"Hai scelto un'arma: {name} ({pts} punti).\nAdesso inviami la foto o il video.",
            parse_mode=None
        )
    else:
        from utils import escape_markdown
        escaped_name = escape_markdown(name)
        bot.send_message(
            chat_id, 
            f"Hai scelto *{escaped_name}* \\(*{pts} punti*\\)\\.\nAdesso inviami la *foto o il video*\\.",
            parse_mode="MarkdownV2"
        )

# ————— CALLBACK REMOVE MATTO —————
def callback_remove_matto(bot, call: types.CallbackQuery):
    if call.from_user.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "❌ Solo l'admin può rimuovere matti!", show_alert=True)
        return
    
    parts = call.data.split("|", 1)
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    matto_id = int(parts[1])
    matto = db_manager.get_matto_by_id(matto_id)
    
    if not matto:
        bot.answer_callback_query(call.id, "Matto non trovato!", show_alert=True)
        return
    
    name = matto["name"]
    db_manager.remove_matto(matto_id)
    
    bot.answer_callback_query(call.id, f"❌ Matto rimosso: {name}", show_alert=True)
    bot.edit_message_text(
        f"✅ Matto rimosso: *{name}*",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

# ————— CALLBACK USER SELECTION —————
def callback_select_user(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    parts = call.data.split("|", 1)
    
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    user_chat_id = int(parts[1])
    state_manager.set_pending_gallery_user(chat_id, user_chat_id)
    
    # Crea tastiera per scegliere la modalità di visualizzazione
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Solo testo", callback_data="gallery_mode|text"),
        InlineKeyboardButton("Con media", callback_data="gallery_mode|photos")
    )
    
    bot.send_message(
        chat_id,
        "📸 Come vuoi visualizzare la galleria di questo utente?",
        reply_markup=markup
    )
    
    bot.answer_callback_query(call.id)

# ————— CALLBACK MATTO SELECTION PER GALLERIA —————
def callback_select_matto(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    parts = call.data.split("|", 1)
    
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    matto_id = int(parts[1])
    state_manager.set_pending_gallery_matto(chat_id, matto_id)
    
    # Crea tastiera per scegliere la modalità di visualizzazione
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Solo testo", callback_data="matto_mode|text"),
        InlineKeyboardButton("Con media", callback_data="matto_mode|photos")
    )
    
    bot.send_message(
        chat_id,
        "📸 Come vuoi visualizzare la galleria di questo matto?",
        reply_markup=markup
    )
    
    bot.answer_callback_query(call.id)

# ————— CALLBACK MODIFICA PUNTI —————
def callback_modifica_punti(bot, call: types.CallbackQuery):
    if call.from_user.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "❌ Solo l'amministratore può modificare i punti.", show_alert=True)
        return

    chat_id = call.message.chat.id
    target_chat_id = int(call.data.split("|")[1])
    state_manager.set_awaiting_point_update(chat_id, target_chat_id)

    users = db_manager.get_registered_users()
    user = next((u for u in users if u['chat_id'] == target_chat_id), None)
    
    if user:
        nome = user["first_name"] or user["username"] or str(target_chat_id)
        current_points = db_manager.get_user_rank_and_points(target_chat_id)
        points = current_points["total_points"] if current_points else 0
        bot.send_message(chat_id, f"✏️ Invia il nuovo punteggio per *{nome}* (attualmente *{points} punti*)", parse_mode="Markdown")
    
    bot.answer_callback_query(call.id)

# ————— CALLBACK MANAGE USER —————
def callback_manage_user(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    parts = call.data.split("|", 1)
    
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    user_chat_id = int(parts[1])
    state_manager.set_pending_manage_user(chat_id, user_chat_id)
    
    matto_stats = db_manager.get_user_gallery(user_chat_id)
    
    if not matto_stats:
        bot.send_message(chat_id, "📭 Questo utente non ha ancora segnalato nessun matto!")
        return
    
    # Ottieni i dettagli dell'utente
    users = db_manager.get_registered_users()
    user = next((u for u in users if u['chat_id'] == user_chat_id), None)
    
    if user:
        username = format_username(user['username'], user['first_name'], user['chat_id'])
        text = f"👤 *Galleria di {username}*\n\n"
        
        for matto, stats in matto_stats.items():
            text += f"• *{matto}*: {stats['count']} segnalazioni, {stats['points']} punti\n"
        
        bot.send_message(chat_id, text, parse_mode="Markdown")
        
        # Per ogni matto, mostra le segnalazioni con pulsante elimina
        for matto, stats in matto_stats.items():
            text = f"🖼️ *{matto}* - Segnalazioni:"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
            for photo in stats["photos"]:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(
                    text="❌ Elimina segnalazione",
                    callback_data=f"delete_sighting|{photo['sighting_id']}"
                ))
                
                try:
                    media_type = photo.get("media_type", "photo")
                    if media_type == "video":
                        bot.send_video(
                            chat_id, 
                            video=photo["file_id"],
                            reply_markup=markup
                        )
                    else:
                        bot.send_photo(
                            chat_id, 
                            photo=photo["file_id"],
                            reply_markup=markup
                        )
                except Exception as e:
                    logger.error(f"Errore invio media: {str(e)}")
    
    bot.answer_callback_query(call.id)

# ————— CALLBACK DELETE SIGHTING —————
def callback_delete_sighting(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    parts = call.data.split("|", 1)
    
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    sighting_id = int(parts[1])
    
    if chat_id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "❌ Solo l'admin può eliminare segnalazioni!", show_alert=True)
        return
    
    if db_manager.delete_sighting(sighting_id):
        bot.answer_callback_query(call.id, "✅ Segnalazione eliminata con successo!", show_alert=True)
        bot.delete_message(chat_id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Errore durante l'eliminazione!", show_alert=True)

# ————— CALLBACK USE WEAPON —————
def callback_use_weapon(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    parts = call.data.split("|", 1)
    
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    target_chat_id = int(parts[1])
    
    if not state_manager.has_pending_weapon_target(chat_id):
        bot.answer_callback_query(call.id, "❌ Sessione scaduta, riprova.")
        return
    
    weapon_info = state_manager.remove_pending_weapon_target(chat_id)
    
    # Aggiungi la segnalazione dell'arma
    media_type = weapon_info.get('media_type', 'photo')
    db_manager.add_sighting(
        chat_id, 
        weapon_info['matto_id'], 
        weapon_info['points'],
        weapon_info['file_id'],
        target_chat_id,
        media_type
    )
    
    # Ottieni i nomi per la notifica
    users = db_manager.get_registered_users()
    finder = next((u for u in users if u['chat_id'] == chat_id), None)
    target = next((u for u in users if u['chat_id'] == target_chat_id), None)
    matto = db_manager.get_matto_by_id(weapon_info['matto_id'])
    
    finder_name = finder['first_name'] or finder['username'] or "Sconosciuto" if finder else "Sconosciuto"
    target_name = target['first_name'] or target['username'] or "Sconosciuto" if target else "Sconosciuto"
    matto_name = matto['name'] if matto else "Matto Sconosciuto"
    damage = abs(matto['points']) if matto else 0
    
    # Notifica a tutti
    text = (
        f"💥 *{finder_name}* ha usato l'arma *{matto_name}* contro *{target_name}*!\n"
        f"🔥 {target_name} perde *{damage} punti*!"
    )
    
    for cid in db_manager.get_registered_chat_ids():
        try:
            bot.send_message(cid, text, parse_mode="Markdown")
            # Invia il media appropriato
            if media_type == "video":
                bot.send_video(cid, video=weapon_info['file_id'])
            else:
                bot.send_photo(cid, photo=weapon_info['file_id'])
        except Exception:
            continue
    
    bot.answer_callback_query(call.id, "💥 Arma usata con successo!", show_alert=True)

# ————— CALLBACK GALLERY MODES —————
def callback_gallery_mode(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    mode = call.data.split("|")[1]
    
    if not state_manager.has_pending_gallery_user(chat_id):
        bot.answer_callback_query(call.id, "❌ Sessione scaduta, riprova.")
        return
    
    user_chat_id = state_manager.get_pending_gallery_user(chat_id)
    matto_stats = db_manager.get_user_gallery(user_chat_id)
    
    if not matto_stats:
        bot.send_message(chat_id, "📭 Questo utente non ha segnalato nessun matto!")
        bot.answer_callback_query(call.id)
        return
    
    # Ottieni i dettagli dell'utente
    users = db_manager.get_registered_users()
    user = next((u for u in users if u['chat_id'] == user_chat_id), None)
    username = format_username(user['username'], user['first_name'], user['chat_id']) if user else "Utente sconosciuto"
    
    if mode == "text":
        # Visualizzazione testuale
        text = f"📋 *Galleria di {username}:*\n"
        for matto, stats in matto_stats.items():
            text += f"\n- *{matto}*: {stats['count']} volte, {stats['points']} punti"
        
        bot.send_message(chat_id, text, parse_mode="Markdown")
    
    elif mode == "photos":
        # Visualizzazione con media (foto e video)
        bot.send_message(chat_id, f"📸 *Galleria di {username}:*", parse_mode="Markdown")
        
        for matto, stats in matto_stats.items():
            text = f"*{matto}*: {stats['count']} segnalazioni, {stats['points']} punti"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
            for idx, media in enumerate(stats["photos"], 1):
                caption = f"Segnalazione {idx}/{stats['count']}"
                # Aggiungi info sull'attacco se presente
                if media["target_first_name"] or media["target_username"]:
                    target = media["target_username"] or media["target_first_name"]
                    caption += f"\n💥 Usato contro: {target}"
                
                try:
                    media_type = media.get("media_type", "photo")
                    if media_type == "video":
                        bot.send_video(
                            chat_id, 
                            video=media["file_id"],
                            caption=caption
                        )
                    else:
                        bot.send_photo(
                            chat_id, 
                            photo=media["file_id"],
                            caption=caption
                        )
                except Exception as e:
                    logger.error(f"Errore invio media: {str(e)}")
    
    state_manager.remove_pending_gallery_user(chat_id)
    bot.answer_callback_query(call.id)

def callback_matto_mode(bot, call: types.CallbackQuery):
    chat_id = call.from_user.id
    mode = call.data.split("|")[1]
    
    if not state_manager.has_pending_gallery_matto(chat_id):
        bot.answer_callback_query(call.id, "❌ Sessione scaduta, riprova.")
        return
    
    matto_id = state_manager.get_pending_gallery_matto(chat_id)
    gallery = db_manager.get_matto_gallery(matto_id)
    
    if not gallery:
        bot.send_message(chat_id, "📭 Nessuna segnalazione per questo matto!")
        bot.answer_callback_query(call.id)
        return
    
    # Ottieni i dettagli del matto
    matto = db_manager.get_matto_by_id(matto_id)
    matto_name = matto['name'] if matto else "Matto sconosciuto"
    
    if mode == "text":
        # Visualizzazione testuale
        text = f"📋 *Galleria di {matto_name}:*\n"
        text += f"Totale segnalazioni: {len(gallery)}\n\n"
        
        for idx, sighting in enumerate(gallery, 1):
            username = sighting['username'] or sighting['first_name'] or "Utente sconosciuto"
            media_emoji = "📹" if sighting.get('media_type') == 'video' else "📸"
            text += f"{idx}. {media_emoji} Segnalato da: {username}\n"
            if sighting['target_username'] or sighting['target_first_name']:
                target = sighting['target_username'] or sighting['target_first_name']
                text += f"   💥 Usato contro: {target}\n"
        
        bot.send_message(chat_id, text, parse_mode="Markdown")
    
    elif mode == "photos":
        # Visualizzazione con media
        bot.send_message(chat_id, f"📸 *Galleria di {matto_name}:*\nTotale: {len(gallery)} segnalazioni", parse_mode="Markdown")
        
        for idx, sighting in enumerate(gallery, 1):
            username = sighting['username'] or sighting['first_name'] or "Utente sconosciuto"
            media_type = sighting.get('media_type', 'photo')
            media_emoji = "📹" if media_type == 'video' else "📸"
            caption = f"{media_emoji} Segnalazione {idx}/{len(gallery)} - Da: {username}"
            
            if sighting['target_username'] or sighting['target_first_name']:
                target = sighting['target_username'] or sighting['target_first_name']
                caption += f"\n💥 Usato contro: {target}"
            
            try:
                if media_type == "video":
                    bot.send_video(
                        chat_id,
                        video=sighting['file_id'],
                        caption=caption
                    )
                else:
                    bot.send_photo(
                        chat_id,
                        photo=sighting['file_id'],
                        caption=caption
                    )
            except Exception as e:
                logger.error(f"Errore invio media: {str(e)}")
    
    state_manager.remove_pending_gallery_matto(chat_id)
    bot.answer_callback_query(call.id)

# ————— CALLBACK SUGGESTION REVIEW —————
def callback_approve_suggestion(bot, call: types.CallbackQuery):
    """Gestisce l'approvazione di un suggerimento"""
    if call.from_user.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "❌ Solo l'admin può approvare suggerimenti!", show_alert=True)
        return
    
    parts = call.data.split("|", 1)
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    suggestion_id = int(parts[1])
    
    # Controlla se è approvazione silenziosa
    if call.data.startswith("approve_suggestion_silent|"):
        success = db_manager.approve_suggestion(suggestion_id)
        if success:
            suggestion = db_manager.get_suggestion_by_id(suggestion_id)
            bot.answer_callback_query(call.id, f"✅ {suggestion['suggested_name']} approvato!", show_alert=True)
            bot.edit_message_text(
                f"✅ Suggerimento approvato: *{suggestion['suggested_name']}*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            
            # Notifica all'utente senza note
            user_text = (
                f"🎉 *Suggerimento approvato!*\n\n"
                f"📝 Il tuo matto *{suggestion['suggested_name']}* ({suggestion['suggested_points']} punti) è stato aggiunto al gioco!"
            )
            try:
                bot.send_message(suggestion['user_chat_id'], user_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Errore notifica utente approvazione: {str(e)}")
        else:
            bot.answer_callback_query(call.id, "❌ Errore durante l'approvazione!", show_alert=True)
    else:
        # Approvazione con note
        state_manager.set_pending_suggestion_review(call.message.chat.id, suggestion_id, 'approve')
        bot.send_message(
            call.message.chat.id,
            "✅ Inserisci delle note per l'approvazione (opzionale, invia solo un punto '.' se non vuoi note):"
        )
        bot.answer_callback_query(call.id)

def callback_reject_suggestion(bot, call: types.CallbackQuery):
    """Gestisce il rifiuto di un suggerimento"""
    if call.from_user.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "❌ Solo l'admin può rifiutare suggerimenti!", show_alert=True)
        return
    
    parts = call.data.split("|", 1)
    if len(parts) < 2 or not parts[1].isdigit():
        bot.answer_callback_query(call.id, "ID non valido!", show_alert=True)
        return
    
    suggestion_id = int(parts[1])
    
    # Controlla se è rifiuto silenzioso
    if call.data.startswith("reject_suggestion_silent|"):
        success = db_manager.reject_suggestion(suggestion_id)
        if success:
            suggestion = db_manager.get_suggestion_by_id(suggestion_id)
            bot.answer_callback_query(call.id, f"❌ {suggestion['suggested_name']} rifiutato!", show_alert=True)
            bot.edit_message_text(
                f"❌ Suggerimento rifiutato: *{suggestion['suggested_name']}*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            
            # Notifica all'utente senza note
            user_text = (
                f"😔 *Suggerimento rifiutato*\n\n"
                f"📝 Il tuo matto *{suggestion['suggested_name']}* non è stato approvato."
            )
            try:
                bot.send_message(suggestion['user_chat_id'], user_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Errore notifica utente rifiuto: {str(e)}")
        else:
            bot.answer_callback_query(call.id, "❌ Errore durante il rifiuto!", show_alert=True)
    else:
        # Rifiuto con note
        state_manager.set_pending_suggestion_review(call.message.chat.id, suggestion_id, 'reject')
        bot.send_message(
            call.message.chat.id,
            "❌ Inserisci il motivo del rifiuto:"
        )
        bot.answer_callback_query(call.id)
