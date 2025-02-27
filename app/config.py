import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('it4GAZ', 'it4GAZ')
    
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://xqakkqeunqanfmrgmikf.supabase.co')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhxYWtrcWV1bnFhbmZtcmdtaWtmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA2NTIxMTEsImV4cCI6MjA1NjIyODExMX0.f9I3tsGTehG-ofLLjZY73w8yKhYfi49O4ZfTpxWYIEs')
    
    @classmethod
    def get(cls, key, default=None):
        return getattr(cls, key, default)




