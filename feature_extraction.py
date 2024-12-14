from transformers import AutoModelForImageClassification, AutoImageProcessor
from peft import LoraConfig, PeftModel
import torch
import pandas as pd
from PIL import Image
from torchvision import transforms
from load_dataset import ImageDataset
import argparse

parser = argparse.ArgumentParser(description='Example')
    
parser.add_argument('--model_path', type=str, required=True, help='Path to .pth file created')
    
parser.add_argument('--dataset_path', type=str, required=True, help='Your path to the dataset')
    
    
args = parser.parse_args()

MODEL_PATH = args.model_path
DATASET_PATH = args.dataset_path

OUTPUT_CSV = "embeddings.csv"

# Device setup
device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.has_mps else "cpu")

# Load the base model
base_model = AutoModelForImageClassification.from_pretrained("google/vit-base-patch16-224")

base_model = base_model.to(device)

# Recreate the PEFT configuration
peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.1,
    target_modules=[
        "encoder.layer.11.attention.attention.query",
        "encoder.layer.11.attention.attention.value",
    ],
    inference_mode=True,
)

# Recreate the PEFT model and load the fine-tuned weights
model = PeftModel(base_model, peft_config)

model.load_state_dict(torch.load(MODEL_PATH, map_location=device))

model.eval()

# Dataset loader
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

dataset = ImageDataset(root_dir=DATASET_PATH, transform=transform)

# DataFrame to store embeddings and labels
embeddings_list = []
labels_list = []

# Extract embeddings
with torch.no_grad():
    
    for image, label in dataset:
        image = image.unsqueeze(0).to(device)  # Add batch dimension
    
        outputs = model(image).logits
    
        embeddings = outputs.cpu().numpy().squeeze()
    
        embeddings_list.append(embeddings.tolist())
    
        labels_list.append(label)

# Save embeddings and labels to CSV for df-analyze run
embeddings_df = pd.DataFrame(embeddings_list)  

labels_df = pd.DataFrame(labels_list, columns=["label"])  

merged_df = pd.concat([embeddings_df, labels_df], axis=1)

merged_df.to_csv(OUTPUT_CSV, index=False)
print(f"\nOutput: {OUTPUT_CSV}")