from app.config import Config
from supabase import create_client, Client
import os
from typing import Optional
import logging

#password: q08sSEWoHlB2Uyzf

class DBClient:
    _instance: Optional['DBClient'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        try:
            supabase_url = Config.get('SUPABASE_URL') or os.getenv('SUPABASE_URL')
            supabase_key = Config.get('SUPABASE_KEY') or os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be specified in the configuration or environment variables")
                
            self.supabase: Client = create_client(supabase_url, supabase_key)
            self._initialized = True
            logging.info("Connection to Supabase successfully established")
        except Exception as e:
            logging.error(f"Error initializing connection to Supabase: {str(e)}")
            raise

    def get_supabase(self) -> Client:
        return self.supabase
