import os
from dotenv import load_dotenv

print('Before load_dotenv():')
print('DATABASE_URL:', os.getenv('DATABASE_URL'))
print('SECRET_KEY:', os.getenv('SECRET_KEY'))

load_dotenv()

print('After load_dotenv():')
print('DATABASE_URL:', os.getenv('DATABASE_URL'))
print('SECRET_KEY:', os.getenv('SECRET_KEY'))
