from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from pathspec import GitIgnoreSpec
import yaml

from .config import PROJECT_ROOT

PRIVATE_NAMES = re.compile(r"^(?:\.env(?:\..+)?|profiles\.(?:local|private)\..+|.+\.(?:bak|backup|pem|key))$")
TOKEN_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
ASSIGNMENT = re.compile(r"(?i)^\s*(?:export\s+)?(?:[A-Z_]*PASSWORD|[A-Z_]*SECRET_KEY|[A-Z_]*API_KEY)\s*=\s*(.+)$")


def candidates(root: Path):
    spec = GitIgnoreSpec.from_lines((root / ".gitignore").read_text().splitlines())
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if '.git' in path.relative_to(root).parts or spec.match_file(relative):
                continue
            yield relative, path.read_bytes()


def inspect_content(name: str, content: bytes) -> list[str]:
    issues=[]
    basename=Path(name).name
    if PRIVATE_NAMES.match(basename) and basename != '.env.example':
        issues.append(f"{name}: private configuration/backup candidate")
    try:
        text=content.decode('utf-8')
    except UnicodeDecodeError:
        return issues
    for number,line in enumerate(text.splitlines(),1):
        if any(pattern.search(line) for pattern in TOKEN_PATTERNS):
            issues.append(f"{name}:{number}: likely credential/private key (value omitted)")
        match=ASSIGNMENT.match(line)
        if match:
            value=match.group(1).strip().strip('\"\'')
            if Path(name).suffix in {'.py','.ps1','.sql'} and not match.group(1).lstrip().startswith(('\"', "'")):
                continue
            safe = value.startswith(('REPLACE_','${','$${','{{')) or value in ('','None','null')
            if not safe:
                issues.append(f"{name}:{number}: literal credential assignment (value omitted)")
    if basename=='profiles.yml':
        profile=yaml.safe_load(text)
        for definition in profile.values():
            if isinstance(definition,dict):
                for output in definition.get('outputs',{}).values():
                    if 'env_var(' not in str(output.get('password','')):
                        issues.append(f"{name}: profile password must use env_var")
    return issues


def check_tree(root: Path = PROJECT_ROOT) -> list[str]:
    found=[]
    spec=GitIgnoreSpec.from_lines((root/'.gitignore').read_text().splitlines())
    for private in ['.env','.env.local','.env.production','dbt/agridax/profiles.local.yml','local.key','config.bak','dbt/agridax/.user.yml']:
        if not spec.match_file(private): found.append(f".gitignore does not protect {private}")
    for required in ['.env.example','dbt/agridax/profiles.yml','requirements.txt','pyproject.toml']:
        if spec.match_file(required) or not (root/required).is_file(): found.append(f"Required reproducibility file missing/ignored: {required}")
    for name,data in candidates(root): found.extend(inspect_content(name,data))
    return found


def main() -> None:
    parser=argparse.ArgumentParser(description='Read-only publication preflight; never stages/commits/pushes')
    parser.add_argument('--staged',action='store_true',help='Inspect existing staged content via read-only Git commands')
    args=parser.parse_args()
    if args.staged:
        command=['git','-C',str(PROJECT_ROOT),'diff','--cached','--name-only','--diff-filter=ACMR','-z']
        result=subprocess.run(command,check=True,stdout=subprocess.PIPE)
        issues=[]
        for name in result.stdout.decode().split('\0'):
            if name:
                content=subprocess.run(['git','-C',str(PROJECT_ROOT),'show',':'+name],check=True,stdout=subprocess.PIPE).stdout
                issues.extend(inspect_content(name,content))
    else:
        issues=check_tree()
    if issues:
        print('\n'.join(issues))
        raise SystemExit(1)
    print('Preflight passed. Heuristic scan; no Git mutation or publication was performed.')


if __name__=='__main__': main()
