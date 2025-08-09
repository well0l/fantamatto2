#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Configurazione bot
BOT_TOKEN = os.getenv("BOT_TOKEN") or "USALO_NELLA_TUA_ENV"
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
REGISTRATION_PASSWORD = os.getenv("REGISTRATION_PASSWORD", "fantamattopwd")

# Configurazione database
DB_PATH = "bot_matti.db"

# Configurazione logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()