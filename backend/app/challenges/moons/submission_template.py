"""Template for a DNNLS Live Arena Python bundle submission.

Zip this file (as submission.py) together with any weights it loads, e.g.

    submission.zip
    ├── submission.py
    └── weights.pt

The sandbox calls predict() twice (hidden test features, visualisation grid) with no
network access, 1 CPU, 512 MB RAM and a 30 s time limit. Keep it small and fast.
"""

import numpy as np


def predict(X):
    """
    X: numpy.ndarray of shape (N, 2)

    Returns:
        numpy.ndarray of shape (N,) containing probabilities for class 1.
    """
    # Replace this with your model. Example: load a PyTorch state dict next to this file.
    #
    #   import os, torch
    #   here = os.path.dirname(os.path.abspath(__file__))
    #   model = MyMLP(); model.load_state_dict(torch.load(os.path.join(here, "weights.pt")))
    #   with torch.no_grad():
    #       return torch.sigmoid(model(torch.tensor(X, dtype=torch.float32))).numpy().ravel()
    #
    x1, x2 = X[:, 0], X[:, 1]
    logit = -2.0 * x2 + 0.5 * x1 - 0.2
    return 1.0 / (1.0 + np.exp(-logit))
