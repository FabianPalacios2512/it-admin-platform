import sys
sys.path.append('.')
from app.services.ad_service import get_locked_accounts
locked = get_locked_accounts()
print(locked[:2] if locked else "No locked accounts")
