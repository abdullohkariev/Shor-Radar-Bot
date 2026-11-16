"""Give a Telegram user the verified-agronomist badge in the community:
    python -m scripts.set_role <telegram_user_id> agronomist
    python -m scripts.set_role <telegram_user_id> farmer      (remove the badge)
The user must have opened the app at least once. Find an id by asking the person to message @userinfobot."""
import sys

from app import db

if len(sys.argv) != 3 or sys.argv[2] not in ("agronomist", "farmer"):
    sys.exit(__doc__)
db.init()
uid = int(sys.argv[1])
if not db.user_get(uid):
    sys.exit(f"User {uid} has not opened the app yet.")
db.user_upsert(uid, role=sys.argv[2])
print(f"User {uid} is now: {sys.argv[2]}")
