import os
import json
import requests
import time
import csv
import base64
from gtts import gTTS

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

# Function to generate audio using gTTS and re-encode with FFmpeg
def generate_audio(text, filename):
    tts = gTTS(text, lang='en')
    temp_audio_path = os.path.join(AUDIO_DIR, "temp_" + filename)  # Temporary file
    final_audio_path = os.path.join(AUDIO_DIR, filename)

    tts.save(temp_audio_path)  # Save initial MP3 file

    # Convert MP3 to universal format using FFmpeg
    os.system(f"ffmpeg -y -i {temp_audio_path} -acodec libmp3lame -b:a 128k -ar 44100 -ac 2 -map_metadata -1 {final_audio_path}")

    os.remove(temp_audio_path)  # Delete temp file

    return final_audio_path  # Return the properly formatted MP3 file

# Function to check if a deck exists in Anki
def check_and_create_deck(deck_name):
    response = requests.post(ANKI_CONNECT_URL, json={
        "action": "deckNames",
        "version": 6
    }).json()
    
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
        "params": {
            "query": f"deck:{deck_name} front:{front}"
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    return response.get("result", [])

# Function to update an existing note
def update_note_in_anki(note_id, back, audio_path):
    with open(audio_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")  # Convert to Base64
    
    audio_filename = os.path.basename(audio_path)
    audio_field = f'[sound:{audio_filename}]'
    
    # Upload audio file to Anki
    response = requests.post(ANKI_CONNECT_URL, json={
        "action": "storeMediaFile",
        "version": 6,
        "params": {
            "filename": audio_filename,
            "data": audio_data
        }
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
                "fields": {
                    "Back": f"{back} {audio_field}"
                }
            }
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    return response.json()

# Function to add a new note
def add_note_to_anki(deck_name, front, back, audio_path):
    with open(audio_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")  # Convert to Base64
    
    audio_filename = os.path.basename(audio_path)
    audio_field = f'[sound:{audio_filename}]'
    
    # Upload audio file to Anki
    response = requests.post(ANKI_CONNECT_URL, json={
        "action": "storeMediaFile",
        "version": 6,
        "params": {
            "filename": audio_filename,
            "data": audio_data
        }
    }).json()

    if response.get("error"):
        print(f"❌ Failed to upload {audio_filename}: {response['error']}")
    else:
        print(f"✅ Uploaded {audio_filename} successfully!")

    # Add flashcard with audio
    payload = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": deck_name,
                "modelName": "Basic",
                "fields": {
                    "Front": front,
                    "Back": f"{back} {audio_field}"
                },
                "tags": ["generated"]
            }
        }
    }
    
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    return response.json()

# Process each CSV file
for csv_file in csv_files:
    deck_name = os.path.splitext(csv_file)[0].replace(" ", "_")  # Use filename as deck name, replacing spaces
    check_and_create_deck(deck_name)  # Ensure deck exists
    print(f"Processing file: {csv_file} into deck: {deck_name}")
    flashcards = []
    
    with open(os.path.join(CSV_FOLDER, csv_file), newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row
        for row in reader:
            if len(row) >= 2:
                flashcards.append((row[0], row[1]))
    
    # Process each flashcard
    for index, (front, back) in enumerate(flashcards):
        print(f"Processing card {index + 1}/{len(flashcards)}: {front}")
        audio_filename = f"{deck_name}_audio_{index}.mp3"
        audio_path = generate_audio(back, audio_filename)
        
        if audio_path:
            existing_notes = find_existing_note_id(deck_name, front)
            if existing_notes:
                update_note_in_anki(existing_notes[0], back, audio_path)
            else:
                add_note_to_anki(deck_name, front, back, audio_path)
        
        time.sleep(1)  # Prevent API rate limits

print("✅ All flashcards processed and added/updated in Anki!")
