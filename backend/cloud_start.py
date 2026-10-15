"""Initialize a newly mounted upload disk, then drop root before app startup."""
import os
from pathlib import Path
import pwd
import sys

uploads = Path(os.environ.get('UPLOAD_DIR', '/data/uploads'))
uploads.mkdir(parents=True, exist_ok=True)
if os.getuid() == 0:
    account = pwd.getpwnam('app')
    os.chown(uploads, account.pw_uid, account.pw_gid)
    os.setgroups([])
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
os.execv(sys.executable, [sys.executable, 'start.py'])
