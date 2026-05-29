import sys
from import_linkedin_contacts_csv import run as import_linkedin
from promote_linkedin_import import run as promote_linkedin
from targeted_account_news import run as targeted_news

def linkedin_import_safe():
    import_linkedin()
    promote_linkedin()

COMMANDS = {
    "linkedin-import-safe": linkedin_import_safe,
    "linkedin-import-only": import_linkedin,
    "linkedin-promote-only": promote_linkedin,
    "targeted-news": targeted_news,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in COMMANDS:
        raise SystemExit(f"Commande inconnue: {cmd}. Options: {list(COMMANDS)}")
    COMMANDS[cmd]()
