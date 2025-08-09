#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import atexit
import logging

logger = logging.getLogger(__name__)

class StateManager:
    """Gestisce gli stati temporanei del bot"""
    
    def __init__(self):
        self.pending_matto = {}  # chat_id → {'id':..., 'name':..., 'points':...}
        self.pending_password = {}  # chat_id: True (in attesa di password)
        self.admin_upload_pending = False
        self.pending_gallery_user = {}  # chat_id → selected_user_chat_id
        self.pending_gallery_matto = {}  # chat_id → matto_id
        self.pending_manage_user = {}  # chat_id → selected_user_chat_id
        self.pending_weapon_target = {}  # chat_id → {'matto_id':..., 'file_id':..., 'points':...}
        self.awaiting_point_update = {}  # admin_chat_id -> chat_id_da_modificare
        
        # Registra la funzione di pulizia per la chiusura
        atexit.register(self.cleanup_all_states)
    
    # ————— PENDING MATTO —————
    def set_pending_matto(self, chat_id, matto_info):
        self.pending_matto[chat_id] = matto_info
    
    def get_pending_matto(self, chat_id):
        return self.pending_matto.get(chat_id)
    
    def remove_pending_matto(self, chat_id):
        return self.pending_matto.pop(chat_id, None)
    
    def has_pending_matto(self, chat_id):
        return chat_id in self.pending_matto
    
    # ————— PENDING PASSWORD —————
    def set_pending_password(self, chat_id):
        self.pending_password[chat_id] = True
    
    def has_pending_password(self, chat_id):
        return chat_id in self.pending_password
    
    def remove_pending_password(self, chat_id):
        return self.pending_password.pop(chat_id, None)
    
    # ————— ADMIN UPLOAD —————
    def set_admin_upload_pending(self, status=True):
        self.admin_upload_pending = status
    
    def is_admin_upload_pending(self):
        return self.admin_upload_pending
    
    # ————— PENDING GALLERY USER —————
    def set_pending_gallery_user(self, chat_id, user_chat_id):
        self.pending_gallery_user[chat_id] = user_chat_id
    
    def get_pending_gallery_user(self, chat_id):
        return self.pending_gallery_user.get(chat_id)
    
    def remove_pending_gallery_user(self, chat_id):
        return self.pending_gallery_user.pop(chat_id, None)
    
    def has_pending_gallery_user(self, chat_id):
        return chat_id in self.pending_gallery_user
    
    # ————— PENDING GALLERY MATTO —————
    def set_pending_gallery_matto(self, chat_id, matto_id):
        self.pending_gallery_matto[chat_id] = matto_id
    
    def get_pending_gallery_matto(self, chat_id):
        return self.pending_gallery_matto.get(chat_id)
    
    def remove_pending_gallery_matto(self, chat_id):
        return self.pending_gallery_matto.pop(chat_id, None)
    
    def has_pending_gallery_matto(self, chat_id):
        return chat_id in self.pending_gallery_matto
    
    # ————— PENDING MANAGE USER —————
    def set_pending_manage_user(self, chat_id, user_chat_id):
        self.pending_manage_user[chat_id] = user_chat_id
    
    def get_pending_manage_user(self, chat_id):
        return self.pending_manage_user.get(chat_id)
    
    def remove_pending_manage_user(self, chat_id):
        return self.pending_manage_user.pop(chat_id, None)
    
    def has_pending_manage_user(self, chat_id):
        return chat_id in self.pending_manage_user
    
    # ————— PENDING WEAPON TARGET —————
    def set_pending_weapon_target(self, chat_id, weapon_info):
        self.pending_weapon_target[chat_id] = weapon_info
    
    def get_pending_weapon_target(self, chat_id):
        return self.pending_weapon_target.get(chat_id)
    
    def remove_pending_weapon_target(self, chat_id):
        return self.pending_weapon_target.pop(chat_id, None)
    
    def has_pending_weapon_target(self, chat_id):
        return chat_id in self.pending_weapon_target
    
    # ————— AWAITING POINT UPDATE —————
    def set_awaiting_point_update(self, admin_chat_id, target_chat_id):
        self.awaiting_point_update[admin_chat_id] = target_chat_id
    
    def get_awaiting_point_update(self, admin_chat_id):
        return self.awaiting_point_update.get(admin_chat_id)
    
    def remove_awaiting_point_update(self, admin_chat_id):
        return self.awaiting_point_update.pop(admin_chat_id, None)
    
    def has_awaiting_point_update(self, admin_chat_id):
        return admin_chat_id in self.awaiting_point_update
    
    # ————— PULIZIA STATI —————
    def cleanup_all_states(self):
        """Pulisce tutti gli stati"""
        self.pending_matto.clear()
        self.pending_password.clear()
        self.admin_upload_pending = False
        self.pending_gallery_user.clear()
        self.pending_gallery_matto.clear()
        self.pending_manage_user.clear()
        self.pending_weapon_target.clear()
        self.awaiting_point_update.clear()
        logger.info("Stati del bot puliti")

# Istanza globale del gestore stati
state_manager = StateManager()