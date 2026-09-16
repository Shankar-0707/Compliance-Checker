"""
extraction/ocr/model/cnn.py
────────────────────────────
Small convolutional neural network (CNN) for single-character image classification.

Architecture
────────────
Input:  (N, 1, 28, 28)  — single-channel 28×28 grayscale image

Block 1: Conv(1→32, 3×3, pad=1) → BatchNorm → ReLU → MaxPool(2×2)  → (N,32,14,14)
Block 2: Conv(32→64, 3×3, pad=1) → BatchNorm → ReLU → MaxPool(2×2) → (N,64, 7, 7)
Block 3: Conv(64→128, 3×3, pad=1) → BatchNorm → ReLU               → (N,128,7, 7)
Flatten                                                               → (N,6272)
Dropout(0.4)
Linear(6272 → 512) → ReLU → Dropout(0.3)
Linear(512  → n_classes)  — raw logits (no softmax; use CrossEntropyLoss)

Design rationale
────────────────
- Three conv blocks provide enough receptive field to distinguish similar-looking
  characters like 'O'/'0', 'l'/'1'/'I', '5'/'S'.
- BatchNorm after each conv accelerates training and acts as light regularisation.
- Two dropout layers reduce overfitting to EMNIST handwriting style, helping
  the model generalise to synthetic printed-font characters.
- ~1.5M parameters — trains in minutes on CPU, seconds on GPU.

Usage
─────
    from extraction.ocr.model.cnn import CharCNN
    from extraction.ocr.charset import NUM_CLASSES
    model = CharCNN(n_classes=NUM_CLASSES)
"""

import torch
import torch.nn as nn


class CharCNN(nn.Module):
    """
    Small CNN for character classification.

    Parameters
    ----------
    n_classes : int
        Number of output classes (length of the charset).
    """

    def __init__(self, n_classes: int) -> None:
        super().__init__()

        # ── Convolutional feature extractor ──────────────────────────────────
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # 28 → 14

            # Block 2
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # 14 → 7

            # Block 3 — no pooling; preserve spatial resolution for small chars
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

        # After Block 3: spatial size = 7×7, channels = 128
        _flat_size = 128 * 7 * 7  # = 6272

        # ── Classifier head ───────────────────────────────────────────────────
        self.classifier = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(_flat_size, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(512, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape (N, 1, 28, 28), dtype float32, values in [0, 1].

        Returns
        -------
        torch.Tensor
            Raw logits, shape (N, n_classes).
        """
        x = self.features(x)
        x = x.view(x.size(0), -1)   # flatten
        x = self.classifier(x)
        return x
