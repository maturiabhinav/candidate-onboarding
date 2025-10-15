import os
from dotenv import load_dotenv

# Read the raw file
with open('.env', 'rb') as f:
    raw = f.read()
    print('Raw file bytes:', repr(raw))
    print('First 10 bytes:', repr(raw[:10]))

# Try to see what dotenv is parsing
from dotenv.main import DotEnv
dotenv = DotEnv('.env')
parsed = dotenv.dict()
print('Parsed variables:', parsed)

load_dotenv()
print('Environment:')
print('  DB_URL:', repr(os.getenv('DB_URL')))
print('  SECRET_KEY:', repr(os.getenv('SECRET_KEY')))
print('  FLASK_DEBUG:', repr(os.getenv('FLASK_DEBUG')))
