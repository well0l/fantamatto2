#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import os
import logging

logger = logging.getLogger(__name__)

def escape_markdown(text):
    """Escape dei caratteri speciali per MarkdownV2"""
    if not text:
        return ""
    # Caratteri speciali che devono essere escapati per MarkdownV2
    escape_chars = '_*[]()~`>#+-=|{}.!'
    escaped_text = []
    for char in text:
        if char in escape_chars:
            escaped_text.append(f'\\{char}')
        else:
            escaped_text.append(char)
    return ''.join(escaped_text)

def escape_markdown_v1(text):
    """Escape dei caratteri speciali per Markdown standard (v1)"""
    if not text:
        return ""
    # Per Markdown v1, solo alcuni caratteri necessitano di escape
    escape_chars = '_*`['
    escaped_text = []
    for char in text:
        if char in escape_chars:
            escaped_text.append(f'\\{char}')
        else:
            escaped_text.append(char)
    return ''.join(escaped_text)

def parse_matti_file_content(content):
    """Parsa il contenuto del file matti e restituisce una lista di tuple (nome, punti)"""
    lines = [ln.strip() for ln in content.split('\n') if ln.strip()]
    
    parsed = []
    seen_names = set()  # Per evitare duplicati esatti
    
    for ln in lines:
        if ',' not in ln:
            logger.warning(f"Riga malformata, salto: {ln}")
            continue
        
        try:
            nome = ln.split(',', 1)[0].strip()
            pts = int(ln.split(',', 1)[1].strip())
            
            # Controlla se il nome esatto è già stato processato
            if nome in seen_names:
                logger.warning(f"Nome duplicato esatto, salto: {nome}")
                continue
                
            parsed.append((nome, pts))
            seen_names.add(nome)
            
        except ValueError:
            logger.warning(f"Riga malformata, salto: {ln}")
    
    return parsed

def create_temp_file_from_content(content):
    """Crea un file temporaneo dal contenuto e restituisce il path"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        return tmp.name

def cleanup_temp_file(filepath):
    """Rimuove un file temporaneo"""
    try:
        os.unlink(filepath)
    except Exception as e:
        logger.warning(f"Errore nella rimozione del file temporaneo {filepath}: {e}")

def format_username(username=None, first_name=None, chat_id=None):
    """Formatta il nome utente per la visualizzazione (senza escape markdown)"""
    if username:
        return f"@{username}"
    elif first_name:
        return first_name
    elif chat_id:
        return f"ID {chat_id}"
    else:
        return "Utente sconosciuto"

def format_username_safe(username=None, first_name=None, chat_id=None):
    """Formatta il nome utente per la visualizzazione con escape markdown"""
    formatted = format_username(username, first_name, chat_id)
    return escape_markdown_v1(formatted)

def format_user_info(username=None, first_name=None):
    """Formatta le informazioni utente complete"""
    if first_name and username:
        return f"{first_name} (@{username})"
    elif first_name:
        return f"{first_name} (senza username)"
    elif username:
        return f"@{username}"
    else:
        return "Utente sconosciuto"

def create_leaderboard_text(users, title="🏆 Classifica", show_medals=True, limit=None):
    """Crea il testo della classifica con escape markdown corretto"""
    if not users:
        return f"{title}\nLa classifica è vuota!"
    
    if limit:
        users = users[:limit]
    
    text = f"{title}\n"
    
    if show_medals and limit and limit <= 10:
        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
    else:
        medals = ["🔹"] * len(users)
    
    for i, row in enumerate(users):
        med = medals[i] if i < len(medals) else "🔹"
        
        # Usa la versione safe per evitare problemi con markdown
        usr = format_username_safe(row['username'], row['first_name'], row['chat_id'])
        pts = row['total_points']
        
        text += f"{med} {i+1}\\. {usr} – \\*{pts} punti\\*\n"
    
    return text

def get_media_emoji(media_type):
    """Restituisce l'emoji appropriato per il tipo di media"""
    return "📹" if media_type == "video" else "📸"

def format_media_type_text(media_type):
    """Restituisce il testo descrittivo per il tipo di media"""
    return "video" if media_type == "video" else "foto"

def save_text_to_temp_file(text, suffix=".txt"):
    """Salva del testo in un file temporaneo e restituisce il path"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=suffix, encoding="utf-8") as tmp:
        tmp.write(text)
        return tmp.name
