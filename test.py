# # import requests

# # response = requests.post("http://localhost:8765", json={
# #     "action": "deckNames",
# #     "version": 6
# # })

# # print(response.json())

# # # import requests

# # # for deck in ["Test_Deck_1", "Test_Deck_2"]:
# # #     response = requests.post("http://localhost:8765", json={
# # #         "action": "createDeck",
# # #         "version": 6,
# # #         "params": {
# # #             "deck": deck
# # #         }
# # #     })
# # #     print(response.json())



# response = requests.post("http://localhost:8765", json={
#     "action": "getMediaFilesNames",
#     "version": 6
# })

# print(response.json())

import requests

upload_response = requests.post(ANKI_CONNECT_URL, json={
    "action": "storeMediaFile",
    "version": 6,
    "params": {
        "filename": audio_filename,
        "data": audio_data.hex()
    }
})
print(f"Audio Upload Response for {audio_filename}:", upload_response.json())  # Debug print
