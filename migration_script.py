#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script di migrazione per aggiungere il supporto video e suggerimenti al database esistente.
Esegui questo script una volta sola per aggiornare il database esistente.
"""

import sqlite3
import logging
from config import DB_PATH

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Migra il database esistente per supportare video e suggerimenti"""
    try:
        # Connessione al database
        db = sqlite3.connect(DB_PATH)
        cursor = db.cursor()
        
        # Verifica se la colonna media_type esiste già
        cursor.execute("PRAGMA table_info(sightings);")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'media_type' not in columns:
            logger.info("Aggiunta colonna media_type alla tabella sightings...")
            
            # Aggiungi la colonna media_type
            cursor.execute("""
                ALTER TABLE sightings 
                ADD COLUMN media_type TEXT DEFAULT 'photo' 
                CHECK (media_type IN ('photo', 'video'));
            """)
            
            # Aggiorna tutti i record esistenti come 'photo' (default)
            cursor.execute("""
                UPDATE sightings 
                SET media_type = 'photo' 
                WHERE media_type IS NULL;
            """)
            
            logger.info("✅ Colonna media_type aggiunta con successo!")
            
        else:
            logger.info("✅ La colonna media_type esiste già.")
        
        # Verifica se la tabella matto_suggestions esiste già
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matto_suggestions';")
        if not cursor.fetchone():
            logger.info("Creazione tabella matto_suggestions...")
            
            cursor.execute("""
                CREATE TABLE matto_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_chat_id INTEGER NOT NULL,
                    suggested_name TEXT NOT NULL,
                    suggested_points INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                    admin_notes TEXT DEFAULT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TEXT DEFAULT NULL,
                    FOREIGN KEY (user_chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );
            """)
            
            logger.info("✅ Tabella matto_suggestions creata con successo!")
        else:
            logger.info("✅ La tabella matto_suggestions esiste già.")
        
        db.commit()
        db.close()
        
        logger.info("🎉 Migrazione completata con successo!")
        logger.info("Il database ora supporta:")
        logger.info("  - 📹 Video per le segnalazioni")
        logger.info("  - 💡 Sistema di suggerimenti matti")
        
    except Exception as e:
        logger.error(f"❌ Errore durante la migrazione: {str(e)}")
        raise

if __name__ == "__main__":
    print("🔄 Avvio migrazione database per supporto video e suggerimenti...")
    migrate_database()
    print("🎉 Migrazione completata!")
