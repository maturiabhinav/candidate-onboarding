import os
from dotenv import load_dotenv

load_dotenv()
print('DB_URL:', repr(os.getenv('DB_URL')))
print('SECRET_KEY:', repr(os.getenv('SECRET_KEY')))
