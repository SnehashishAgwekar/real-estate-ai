import os
import torch
import torch.nn as nn
from torchvision import models, transforms
import pillow_avif
from PIL import Image
import io

# Define paths relative to this file (app/services/room_classifier.py -> app/models/places365)
MODEL_DIR = os.path.join(os.path.dirname(__file__), "../models/places365")
WEIGHTS_PATH = os.path.join(MODEL_DIR, "resnet18_places365.pth.tar")
CLASSES_PATH = os.path.join(MODEL_DIR, "categories_places365.txt")

# Load classes
def load_classes():
    classes = []
    if os.path.exists(CLASSES_PATH):
        with open(CLASSES_PATH) as f:
            for line in f:
                classes.append(line.strip().split(" ")[0][3:]) # remove prefix like '/b/bedroom'
    return classes

CLASSES = load_classes()

# Load Model once at module import
def load_model():
    model = models.resnet18(num_classes=365)
    checkpoint = torch.load(WEIGHTS_PATH, map_location=lambda storage, loc: storage)
    state_dict = {str(k).replace('module.', ''): v for k, v in checkpoint['state_dict'].items()}
    model.load_state_dict(state_dict)
    model.eval()
    return model

MODEL = load_model()

# Image Preprocessing Pipeline for Places365
preprocess = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Category Mapping Logic to Real Estate Categories
def map_category(raw_category: str) -> str:
    cat = raw_category.lower()
    if any(k in cat for k in [
        "bedroom", "bedchamber", "dormitory", "hotel_room",
        "berth", "youth_hostel", "alcove", "nursery","waiting_room"
    ]):
        return "bedroom"
    elif any(k in cat for k in ["bathroom", "washroom", "restroom", "shower", "tub", "jacuzzi"]):
        return "bathroom"
    elif any(k in cat for k in ["kitchen", "scullery", "dinette", "pantry"]):
        return "kitchen"
    elif any(k in cat for k in [
        "living_room", "lounge", "sitting_room", "family_room",
        "television_room", "home_theater", "waiting_room", "parlor"
    ]):
        return "living_room"
    elif any(k in cat for k in ["dining_room", "cafeteria", "restaurant", "banquet_hall"]):
        return "dining_room"
    elif any(k in cat for k in ["closet", "wardrobe"]):
        return "closet"
    else:
        return "other"

def classify_room(image_bytes: bytes) -> dict:
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Invalid image file: {e}")
    
    input_tensor = preprocess(image).unsqueeze(0)
    
    with torch.no_grad():
        output = MODEL(input_tensor)
        probabilities = nn.functional.softmax(output[0], dim=0)
        
    top3_prob, top3_idx = torch.topk(probabilities, 3)
    
    top3_list = []
    for i in range(3):
        raw_cat = CLASSES[top3_idx[i].item()] if CLASSES else "unknown"
        top3_list.append({
            "raw_category": raw_cat,
            "mapped_category": map_category(raw_cat),
            "confidence": round(top3_prob[i].item(), 4)
        })
        
    best_match = next(
        (item for item in top3_list if item["mapped_category"] != "other"),
        top3_list[0]  # fallback to top-1 if nothing in top3 maps
    )

    
    return {
        "room_type": best_match["mapped_category"],
        "raw_category": best_match["raw_category"],
        "confidence": best_match["confidence"],
        "top3": top3_list
    }