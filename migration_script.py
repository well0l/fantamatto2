#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script di migrazione per aggiungere il supporto video al database esistente.
Esegui questo script una volta sola per aggiornare il database esistente.
"""

import sqlite3
import logging
from config import DB_PATH

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Migra il database esistente per supportare i video"""
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
            
            db.commit()
            logger.info("✅ Migrazione completata con successo!")
            logger.info("Il database ora supporta foto e video per le segnalazioni.")
            
        else:
            logger.info("✅ La colonna media_type esiste già. Nessuna migrazione necessaria.")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Errore durante la migrazione: {str(e)}")
        raise

if __name__ == "__main__":
    print("🔄 Avvio migrazione database per supporto video...")
    migrate_database()
    print("🎉 Migrazione completata!")
