import os
import joblib


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "priority_model.pkl"
)

VECTORIZER_PATH = os.path.join(
    BASE_DIR,
    "models",
    "tfidf_vectorizer.pkl"
)


# Load model
model = joblib.load(MODEL_PATH)

# Load TF-IDF vectorizer
vectorizer = joblib.load(VECTORIZER_PATH)


def predict_priority(complaint_text):

    # Convert complaint text to vector
    complaint_vector = vectorizer.transform([complaint_text])

    # Predict priority
    prediction = model.predict(complaint_vector)[0]

    # Get confidence
    probabilities = model.predict_proba(complaint_vector)[0]

    confidence = max(probabilities) * 100

    return prediction, round(confidence, 2)