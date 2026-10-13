"""
SirenSync Green Corridor - Ambulance Fine-Tuning Script
Fine-tunes a base YOLOv10 (or YOLOv8) model on an emergency ambulance dataset.

Usage:
    python train_ambulance.py --data ambulance_dataset.yaml --epochs 50 --batch 16 --model yolov10n.pt
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("train_ambulance")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune YOLOv10 on an ambulance detection dataset for SirenSync Green Corridor"
    )
    parser.add_argument(
        "--data",
        type=str,
        default="ambulance_dataset.yaml",
        help="Path to dataset YAML file (Open Images or Roboflow export)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov10n.pt",
        help="Base model to fine-tune (e.g., yolov10n.pt, yolov10s.pt, yolov8n.pt)"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs (recommended: 30-100)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Batch size (reduce if GPU out-of-memory occurs)"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Image size for training and validation"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="CUDA device index (e.g. '0', '0,1') or 'cpu'"
    )
    parser.add_argument(
        "--output-weights",
        type=str,
        default="weights/yolov10n_ambulance.pt",
        help="Destination path to store fine-tuned best weights"
    )
    return parser.parse_args()


def train(args: argparse.Namespace) -> None:
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("Ultralytics is not installed. Run: pip install ultralytics")
        sys.exit(1)

    data_path = Path(args.data)
    if not data_path.exists():
        logger.error(f"Dataset configuration file '{args.data}' does not exist.")
        logger.info(
            "Instructions to download an Ambulance Dataset:\n"
            "1. Roboflow Universe: Search 'Ambulance Detection YOLOv8' and export in YOLOv8 PyTorch format.\n"
            "2. Open Images V7: Use fiftyone to download label 'Ambulance'.\n"
            "3. Extract to ./datasets/ambulance_dataset and point ambulance_dataset.yaml to it."
        )
        sys.exit(1)

    logger.info("============================================================")
    logger.info("Starting SirenSync Ambulance Model Fine-Tuning")
    logger.info(f"Base Model:       {args.model}")
    logger.info(f"Dataset Config:   {args.data}")
    logger.info(f"Epochs:           {args.epochs}")
    logger.info(f"Batch Size:       {args.batch}")
    logger.info(f"Device:           {args.device}")
    logger.info(f"Target Output:    {args.output_weights}")
    logger.info("============================================================")

    # Load base model
    logger.info(f"Loading base model '{args.model}'...")
    model = YOLO(args.model)

    # Train model
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project="runs/ambulance_train",
        name="sirensync_exp",
        exist_ok=True,
        plots=True,
        save=True
    )

    logger.info("Training complete. Validating model...")
    metrics = model.val()
    logger.info(f"Validation mAP50-95: {metrics.box.map:.4f}")
    logger.info(f"Validation mAP50:    {metrics.box.map50:.4f}")

    # Copy best weights to the target location for easy runtime ingestion
    best_weights_source = Path("runs/ambulance_train/sirensync_exp/weights/best.pt")
    target_weights_path = Path(args.output_weights)
    target_weights_path.parent.mkdir(parents=True, exist_ok=True)

    if best_weights_source.exists():
        shutil.copy(best_weights_source, target_weights_path)
        logger.info(f"Successfully copied trained weights to: {target_weights_path.resolve()}")
        logger.info("SirenSync Green Corridor can now load these weights automatically via config.yaml!")
    else:
        logger.warning(f"Could not locate best weights at {best_weights_source}. Check runs directory.")


if __name__ == "__main__":
    train(parse_args())
