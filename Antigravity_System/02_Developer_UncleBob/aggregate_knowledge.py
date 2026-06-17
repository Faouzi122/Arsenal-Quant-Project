import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# === CONFIGURATION ÉLITE ANTIGRAVITY ===
CONFIG = {
    "Flux_Projets": "1dQ0RFj9ybUbBVtiSsB48p83suq-T700L7tBxqqQ6YoQ",
    "Sources_Syntheses": "1z14INQWKMXEk8Yn5o49AzQ4rwcbjBSOtQANagCprW60"
}

ROOT_DIR = os.path.expanduser("~/Antigravity_System")
KNOWLEDGE_BASE = os.path.expanduser("~/Antigravity_Knowledge_Base")
CREDENTIALS_PATH = os.path.join(ROOT_DIR, "config/credentials.json")
TOKEN_PATH = os.path.join(ROOT_DIR, "config/token.pickle")

SCOPES = ['https://www.googleapis.com/auth/documents']

def get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    return build('docs', 'v1', credentials=creds)

def update_master(service, folder_name, doc_id):
    path = os.path.join(KNOWLEDGE_BASE, folder_name)
    content = f"=== DERNIÈRE SYNCHRONISATION SYSTÈME : {folder_name} ===\n"
    
    if not os.path.exists(path):
        return

    for filename in sorted(os.listdir(path)):
        if filename.endswith((".md", ".txt")):
            with open(os.path.join(path, filename), 'r') as f:
                content += f"\n\n--- SOURCE: {filename} ---\n" + f.read()

    try:
        doc = service.documents().get(documentId=doc_id).execute()
        end_index = doc.get('body')['content'][-1]['endIndex'] - 1
        
        requests = [
            {'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_index}}} if end_index > 1 else None,
            {'insertText': {'location': {'index': 1}, 'text': content}}
        ]
        # Filtrer les requêtes None
        requests = [r for r in requests if r]
        
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        print(f"[OK] {folder_name} synchronisé avec succès.")
    except Exception as e:
        print(f"[ERREUR] Doc ID {doc_id} : {e}")

if __name__ == "__main__":
    print("--- DÉMARRAGE DE LA GRANDE SYNCHRONISATION ---")
    try:
        drive_service = get_service()
        for folder, doc_id in CONFIG.items():
            update_master(drive_service, folder, doc_id)
    except Exception as error:
        print(f"[ERREUR CRITIQUE] : {error}")
