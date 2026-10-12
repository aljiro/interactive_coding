"""Template for a DNNLS Live Arena Python bundle submission (small-data MNIST).

Zip this file (as submission.py) together with any weights it loads, e.g.

    submission.zip
    ├── submission.py
    └── weights.pt

The sandbox calls predict() twice (hidden test digits, public training digits) with no
network access, 1 CPU, 512 MB RAM and a 30 s time limit. Keep it small and fast.
"""

import numpy as np

N_CLASSES = 10


def preprocess(X):
    """Raw pixels (N, 784) in 0..255 -> whatever your model was trained on.

    Keep training and inference in sync: use this same function in both places.
    """
    return np.array(X, dtype=np.float32)


def predict(X):
    """
    X: numpy.ndarray of shape (N, 784), raw pixel values 0..255

    Returns:
        numpy.ndarray of shape (N, 10) with class probabilities (each row sums to 1).
    """
    # Replace this with your model. Example: load a PyTorch state dict next to this file.
    #
    #   import os, torch
    #   here = os.path.dirname(os.path.abspath(__file__))
    #   model = MyMLP(); model.load_state_dict(torch.load(os.path.join(here, "weights.pt")))
    #   model.eval()
    #   with torch.no_grad():
    #       logits = model(torch.as_tensor(preprocess(X)))
    #       return torch.softmax(logits, dim=1).numpy().astype(np.float64)
    #
    # Placeholder: a uniform distribution (10 % accuracy).
    return np.full((len(X), N_CLASSES), 1.0 / N_CLASSES)
