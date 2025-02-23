import os
import json
import requests
import time
import csv
import base64
import re

# ElevenLabs API Key (Replace with your actual key)
ELEVENLABS_API_KEY = ""

# AnkiConnect Configuration
ANKI_CONNECT_URL = "http://localhost:8765"

# Path to store audio files
AUDIO_DIR = "anki_audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Folder containing multiple CSV files
CSV_FOLDER = "csv_files"
os.makedirs(CSV_FOLDER, exist_ok=True)

# Get list of CSV files
csv_files = [f for f in os.listdir(CSV_FOLDER) if f.endswith(".csv")]

# Function to generate audio using ElevenLabs TTS
def generate_audio(text, filename):
    url = "https://api.elevenlabs.io/v1/text-to-speech/qBDvhofpxp92JgXJxDjB"  #Lily Wolf voice
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}  # Adjust for different speech effects
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        audio_path = os.path.join(AUDIO_DIR, filename)
        with open(audio_path, "wb") as audio_file:
            audio_file.write(response.content)
        print(f"✅ Audio saved: {audio_path}")
        return audio_path
    else:
        print(f"❌ ElevenLabs API Error: {response.json()}")
        return None

# Function to check if a deck exists in Anki
def check_and_create_deck(deck_name):
    response = requests.post(ANKI_CONNECT_URL, json={"action": "deckNames", "version": 6}).json()
    if "result" in response and deck_name not in response["result"]:
        print(f"🛠 Creating deck: {deck_name}")
        requests.post(ANKI_CONNECT_URL, json={
            "action": "createDeck",
            "version": 6,
            "params": {"deck": deck_name}
        })

# Function to check if a card exists in Anki
def find_existing_note_id(deck_name, front):
    payload = {
        "action": "findNotes",
        "version": 6,
        "params": {"query": f"deck:{deck_name} Front:\"{front}\""}
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    return response.get("result", [])

# Function to update an existing note
def update_note_in_anki(note_id, front, back, audio_path):
    with open(audio_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")  # Convert to Base64
    
    audio_filename = os.path.basename(audio_path)
    audio_field = f'[sound:{audio_filename}]'

    # Upload audio file to Anki
    response = requests.post(ANKI_CONNECT_URL, json={
        "action": "storeMediaFile",
        "version": 6,
        "params": {"filename": audio_filename, "data": audio_data}
    }).json()

    if response.get("error"):
        print(f"❌ Failed to upload {audio_filename}: {response['error']}")
    else:
        print(f"✅ Uploaded {audio_filename} successfully!")

    # Update the existing note
    payload = {
        "action": "updateNoteFields",
        "version": 6,
        "params": {
            "note": {
                "id": note_id,
                "fields": {"Front": front, "Back": f"{back} {audio_field}"}
            }
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    if response.get("error"):
        print(f"❌ Failed to update note {note_id}: {response['error']}")
    else:
        print(f"✅ Updated note {note_id} with new answer and audio!")

# Function to add a new note to Anki (Prevents Duplicates)
def add_note_to_anki(deck_name, front, back):
    existing_notes = find_existing_note_id(deck_name, front)

    if existing_notes:
        print(f"⚠️ Note already exists for: {front}, checking for updates...")

        # Fetch the existing answer (Back field) from Anki
        existing_back = requests.post("http://localhost:8765", json={
            "action": "notesInfo",
            "version": 6,
            "params": {"notes": [existing_notes[0]]}
        }).json()["result"][0]["fields"]["Back"]["value"]
        existing_back_cleaned = re.sub(r"\[sound:.*?\]", "", existing_back).strip()

        print(existing_back_cleaned)
        print(back)
        # Check if the answer has changed
        if existing_back_cleaned.strip() == back.strip():
            print(f"✅ No changes detected for: {front}, skipping update.")
            return  # Skip updating if nothing has changed
        
    audio_filename = f"{deck_name}_audio_{index}.mp3"
    audio_path = generate_audio(back, audio_filename)
    
    if not audio_path:
        return
    
    if existing_notes:
        print(f"🔄 Changes detected, updating note: {front}")
        update_note_in_anki(existing_notes[0], front, back, audio_path)
        return

    with open(audio_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")  # Convert to Base64
    
    audio_filename = os.path.basename(audio_path)
    audio_field = f'[sound:{audio_filename}]'

    # Upload audio file to Anki
    response = requests.post(ANKI_CONNECT_URL, json={
        "action": "storeMediaFile",
        "version": 6,
        "params": {"filename": audio_filename, "data": audio_data}
    }).json()

    if response.get("error"):
        print(f"❌ Failed to upload {audio_filename}: {response['error']}")
    else:
        print(f"✅ Uploaded {audio_filename} successfully!")

    # Add the new note
    payload = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": deck_name,
                "modelName": "Basic",
                "fields": {"Front": front, "Back": f"{back} {audio_field}"},
                "tags": ["auto-generated"]
            }
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    
    if response.get("error"):
        print(f"❌ Failed to add note: {response['error']}")
    else:
        print(f"✅ Added new note with audio!")

# Process each CSV file
for csv_file in csv_files:
    deck_name = os.path.splitext(csv_file)[0].replace(" ", "_")  # Use filename as deck name, replacing spaces
    check_and_create_deck(deck_name)  # Ensure deck exists
    print(f"📂 Processing file: {csv_file} into deck: {deck_name}")
    flashcards = []
    
    with open(os.path.join(CSV_FOLDER, csv_file), newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row
        for row in reader:
            if len(row) >= 2:
                flashcards.append((row[0], row[1]))
    
    # Process each flashcard
    for index, (front, back) in enumerate(flashcards):
        print(f"🎴 Processing card {index + 1}/{len(flashcards)}: {front}")
        # audio_filename = f"{deck_name}_audio_{index}.mp3"
        # audio_path = generate_audio(back, audio_filename)
        
        # if audio_path:
            # existing_notes = find_existing_note_id(deck_name, front)
            # print(existing_notes)
            # if existing_notes:
            #     update_note_in_anki(existing_notes[0], front, back, audio_path)
            # else:
        add_note_to_anki(deck_name, front, back)
        
        time.sleep(1)  # Prevent API rate limits

print("✅ All flashcards processed and added/updated in Anki!")
