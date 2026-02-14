import pickle
import face_recognition

# image = face_recognition.load_image_file("face.jpg")
# face_locations = face_recognition.face_locations(image)
# face_encodings = face_recognition.face_encodings(image, face_locations)

# encoding = face_encodings[0]

# with open("face_embeddings.pkl", "wb") as f:
#     pickle.dump(encoding, f)

# Load a new image to compare

with open("face_embeddings.pkl", "rb") as f:
    loaded_encoding = pickle.load(f)

new_image = face_recognition.load_image_file("face.jpg")
new_encoding = face_recognition.face_encodings(new_image)[0]

# Compare
results = face_recognition.compare_faces([loaded_encoding], new_encoding)
print(results)  # True if match, False otherwise