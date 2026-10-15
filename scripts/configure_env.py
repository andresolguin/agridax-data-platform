"""Generate private local credentials; never include the resulting .env in an archive."""
import argparse
import os
import secrets

from agridax.config import PROJECT_ROOT

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=5432)
    args=parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1 through 65535")
    path=PROJECT_ROOT / '.env'
    if path.exists():
        parser.error(".env already exists; it was not overwritten")
    template=(PROJECT_ROOT / '.env.example').read_text()
    for role in ['ADMIN','INGEST','DBT','PUBLISH','READER']:
        template=template.replace('REPLACE_'+role+'_PASSWORD',secrets.token_urlsafe(32))
    template=template.replace('POSTGRES_PORT=5432',f'POSTGRES_PORT={args.port}')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: f.write(template)
    print('Private .env created; credentials were not printed. Keep it ignored.')

if __name__ == '__main__': main()
