import os
from dotenv import load_dotenv

load_dotenv()
print('DATABASE_URL:', repr(os.getenv('DATABASE_URL')))
print('SECRET_KEY:', repr(os.getenv('SECRET_KEY')))
print('FLASK_DEBUG:', repr(os.getenv('FLASK_DEBUG')))
