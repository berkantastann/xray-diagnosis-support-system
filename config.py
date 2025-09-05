import os
from dotenv import load_dotenv

# .env dosyasından ortam değişkenlerini yükle
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bu-anahtari-uretim-ortaminda-degistir'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB maksimum dosya boyutu
    
    # Gemini API Yapılandırması !!!
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY bulunamadı. Lütfen .env dosyasında GOOGLE_API_KEY değerini kontrol edin.")
    
    # Hız Sınırlama Yapılandırması
    API_RATE_LIMIT = {
        'requests_per_minute': 60,  # Ücretsiz katman limiti
        'requests_per_day': 1000,   # Ücretsiz katman limiti
        'retry_delay': 40,          # Yeniden denemeden önce beklenecek saniye
        'max_retries': 3            # Maksimum yeniden deneme sayısı
    }
    
    # Model Yapılandırması
    GENERATION_CONFIG = {
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 2048,
    }
    
    SAFETY_SETTINGS = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
    ] 