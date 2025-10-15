import os
from dotenv import load_dotenv, find_dotenv

print('=== DEBUG .env LOADING ===')
dotenv_path = find_dotenv()
print('Found .env at:', dotenv_path)

if dotenv_path:
    print('File exists:', os.path.exists(dotenv_path))
    
    # Read raw file content
    with open(dotenv_path, 'rb') as f:
        raw_content = f.read()
        print('Raw file content (bytes):')
        print(raw_content)
        print()
        
    # Read as text
    with open(dotenv_path, 'r', encoding='utf-8') as f:
        text_content = f.read()
        print('Text file content:')
        print(repr(text_content))
        print()
        
    # Try different encodings
    for encoding in ['utf-8', 'utf-16', 'latin-1']:
        try:
            with open(dotenv_path, 'r', encoding=encoding) as f:
                content = f.read()
                print(f'With {encoding} encoding:')
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    print(f'  Line {i}: {repr(line)}')
                print()
        except Exception as e:
            print(f'Failed with {encoding}: {e}')
    
    load_dotenv()
    print('Environment variables after load_dotenv():')
    for key in ['DATABASE_URL', 'SECRET_KEY', 'FLASK_DEBUG']:
        value = os.getenv(key)
        print(f'  {key}: {repr(value)}')
else:
    print('No .env file found!')
