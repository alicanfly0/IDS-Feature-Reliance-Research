"""PyTorch port of the Fang et al. DCNN + self-attention binary classifier (D-009).

Source: the authors' Keras `build_dcnn_sa` (repository ZHF123775838/WSN-DCNN-SHAP, models.py).
This is an ADAPTATION, not a reproduction. Kept from the code:
  input (F,) -> (F, 1); Conv1D 32 (k=3, same) + BN + ReLU; Conv1D 64 (k=3, same) + BN + ReLU;
  4-head self-attention (key_dim 16) added residually, then LayerNorm; Flatten;
  Dense 128 ReLU -> Dropout 0.3 -> Dense 64 ReLU -> Dense 1 sigmoid; L2 1e-3 on the conv and
  hidden-dense kernels; Adam(lr 5e-4); binary cross-entropy.
Keras defaults matched explicitly: Glorot-uniform kernels with zero biases, BatchNorm eps 1e-3 and
momentum 0.99 (PyTorch momentum 0.01), LayerNorm eps 1e-3, Adam eps 1e-7.
Documented differences: the paper's text describes 3x3 kernels and 64 first-layer maps; we follow
the released code (1-D kernels, 32 maps). PyTorch replaces Keras/TensorFlow.
"""
from __future__ import annotations

import torch
from torch import nn

L2 = 1e-3


class DCNNSA(nn.Module):
    def __init__(self, n_features: int, heads: int = 4, use_attention: bool = True):
        super().__init__()
        self.n_features = n_features
        self.use_attention = use_attention
        self.conv1 = nn.Conv1d(1, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(32, eps=1e-3, momentum=0.01)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(64, eps=1e-3, momentum=0.01)
        self.attn = nn.MultiheadAttention(64, heads, batch_first=True)   # head dim 64/4 = 16 = Keras key_dim
        self.norm = nn.LayerNorm(64, eps=1e-3)
        self.fc1 = nn.Linear(n_features * 64, 128)
        self.drop = nn.Dropout(0.3)
        self.fc2 = nn.Linear(128, 64)
        self.out = nn.Linear(64, 1)
        for m in self.modules():
            if isinstance(m, (nn.Conv1d, nn.Linear)):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
        nn.init.xavier_uniform_(self.attn.in_proj_weight)
        nn.init.zeros_(self.attn.in_proj_bias)

    def logits(self, x: torch.Tensor) -> torch.Tensor:
        h = x.unsqueeze(1)                                   # (N, 1, F)
        h = torch.relu(self.bn1(self.conv1(h)))
        h = torch.relu(self.bn2(self.conv2(h)))              # (N, 64, F)
        h = h.transpose(1, 2)                                # (N, F, 64), Keras channels-last layout
        if self.use_attention:
            a, _ = self.attn(h, h, h, need_weights=False)
            h = self.norm(h + a)
        h = h.flatten(1)                                     # feature-major, as Keras Flatten
        h = self.drop(torch.relu(self.fc1(h)))
        h = torch.relu(self.fc2(h))
        return self.out(h).squeeze(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.logits(x))

    def l2_penalty(self) -> torch.Tensor:
        """Keras kernel_regularizer=l2(1e-3): 1e-3 * sum(w^2) per regularised kernel, added to the loss."""
        return L2 * sum((m.weight ** 2).sum() for m in (self.conv1, self.conv2, self.fc1, self.fc2))
