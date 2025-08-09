#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import logging
from threading import Lock
from datetime import datetime, timezone
from collections import defaultdict
from config import DB_PATH

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.lock = Lock()
        
    def init_db(self):
        """Inizializza le tabelle del database"""
        try:
            with self.lock:
                # Tabella users
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        chat_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        registered INTEGER NOT NULL DEFAULT 0 CHECK (registered IN (0,1)),
                        total_points INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Tabella matti
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS matti (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        points INTEGER NOT NULL
                    );
                """)
                
                # Tabella sightings con supporto per media_type
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sightings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_chat_id INTEGER NOT NULL,
                        matto_id INTEGER NOT NULL,
                        target_chat_id INTEGER DEFAULT NULL,
                        points_awarded INTEGER NOT NULL,
                        file_id TEXT NOT NULL,
                        media_type TEXT DEFAULT 'photo' CHECK (media_type IN ('photo', 'video')),
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_chat_id) REFERENCES users(chat_id) ON DELETE CASCADE,
                        FOREIGN KEY (matto_id) REFERENCES matti(id) ON DELETE CASCADE,
                        FOREIGN KEY (target_chat_id) REFERENCES users(chat_id) ON DELETE SET NULL
                    );
                """)
                
                self.db.commit()
                logger.info("Tabelle del database create con successo")
        except Exception as e:
            logger.error(f"Errore durante l'inizializzazione del database: {str(e)}")
            raise

    def upgrade_db(self):
        """Aggiorna il database aggiungendo colonne se necessario"""
        with self.lock:
            # Verifica se la colonna target_chat_id esiste già
            self.cursor.execute("PRAGMA table_info(sightings);")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            if 'target_chat_id' not in columns:
                self.cursor.execute("ALTER TABLE sightings ADD COLUMN target_chat_id INTEGER DEFAULT NULL;")
                self.cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sightings_target 
                    ON sightings(target_chat_id);
                """)
                self.db.commit()
                logger.info("Database aggiornato con la colonna target_chat_id")
            
            # Verifica se la colonna media_type esiste già
            if 'media_type' not in columns:
                self.cursor.execute("ALTER TABLE sightings ADD COLUMN media_type TEXT DEFAULT 'photo' CHECK (media_type IN ('photo', 'video'));")
                self.db.commit()
                logger.info("Database aggiornato con la colonna media_type")

    # ————— METODI USERS —————
    def register_user(self, chat_id, username, first_name):
        with self.lock:
            self.cursor.execute(
                "INSERT OR IGNORE INTO users(chat_id, username, first_name) VALUES(?, ?, ?);",
                (chat_id, username, first_name)
            )
            self.db.commit()

    def set_registered(self, chat_id, is_reg=True):
        with self.lock:
            self.cursor.execute(
                "UPDATE users SET registered = ? WHERE chat_id = ?;",
                (1 if is_reg else 0, chat_id)
            )
            self.db.commit()

    def unregister_user(self, chat_id):
        with self.lock:
            self.cursor.execute("UPDATE users SET registered = 0 WHERE chat_id = ?;", (chat_id,))
            self.db.commit()

    def get_registered_users(self):
        with self.lock:
            return self.cursor.execute(
                "SELECT chat_id, username, first_name FROM users WHERE registered = 1 ORDER BY username;"
            ).fetchall()

    def get_registered_chat_ids(self):
        with self.lock:
            return [r["chat_id"] for r in self.cursor.execute(
                "SELECT chat_id FROM users WHERE registered = 1"
            ).fetchall()]

    def get_leaderboard(self, limit=None):
        with self.lock:
            query = "SELECT chat_id, username, first_name, total_points FROM users WHERE registered = 1 ORDER BY total_points DESC"
            if limit:
                query += f" LIMIT {limit}"
            return self.cursor.execute(query).fetchall()

    def get_user_rank_and_points(self, chat_id):
        with self.lock:
            res = self.cursor.execute(
                """
                SELECT chat_id, total_points,
                       (SELECT COUNT(*) + 1 FROM users u2
                        WHERE u2.total_points > u1.total_points AND u2.registered = 1
                       ) AS rank
                FROM users u1 WHERE chat_id = ? AND registered = 1;
                """, (chat_id,)
            ).fetchone()
            return res

    def update_user_points(self, chat_id, points):
        """Aggiorna i punti di un utente"""
        with self.lock:
            self.cursor.execute(
                "UPDATE users SET total_points = ? WHERE chat_id = ?;",
                (points, chat_id)
            )
            self.db.commit()

    # ————— METODI MATTI —————
    def add_matto(self, name, points):
        with self.lock:
            self.cursor.execute(
                "INSERT OR REPLACE INTO matti (name, points) VALUES (?, ?);",
                (name, points)
            )
            self.db.commit()
        return True

    def remove_matto(self, matto_id):
        with self.lock:
            self.cursor.execute("DELETE FROM matti WHERE id = ?;", (matto_id,))
            self.db.commit()
        return True

    def list_matti(self):
        with self.lock:
            return self.cursor.execute(
                "SELECT id, name, points FROM matti ORDER BY points DESC, name;"
            ).fetchall()

    def get_matto_by_id(self, matto_id):
        with self.lock:
            return self.cursor.execute(
                "SELECT id, name, points FROM matti WHERE id = ?;", (matto_id,)
            ).fetchone()

    def load_matti_from_data(self, matti_data):
        """Carica una lista di matti dal formato [(nome, punti), ...]"""
        with self.lock:
            self.cursor.executemany(
                "INSERT OR REPLACE INTO matti (name, points) VALUES (?, ?);", 
                matti_data
            )
            self.db.commit()
        return len(matti_data)

    # ————— METODI SIGHTINGS —————
    def add_sighting(self, chat_id, matto_id, points, file_id, target_chat_id=None, media_type="photo"):
        now = datetime.now(timezone.utc).isoformat()
        with self.lock:
            self.cursor.execute(
                "INSERT INTO sightings(user_chat_id, matto_id, points_awarded, file_id, media_type, timestamp, target_chat_id) VALUES(?, ?, ?, ?, ?, ?, ?);",
                (chat_id, matto_id, points, file_id, media_type, now, target_chat_id)
            )
            
            # Aggiorna punti SOLO se non è un'arma (punti positivi)
            if points > 0:
                self.cursor.execute(
                    "UPDATE users SET total_points = total_points + ? WHERE chat_id = ?;",
                    (points, chat_id)
                )
            
            # Se c'è un target, aggiorna i suoi punti (sottrai i punti assoluti)
            if target_chat_id:
                self.cursor.execute(
                    "UPDATE users SET total_points = total_points - ? WHERE chat_id = ?;",
                    (abs(points), target_chat_id)
                )
            
            self.db.commit()

    def get_matto_gallery(self, matto_id):
        with self.lock:
            return self.cursor.execute(
