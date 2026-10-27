"""Checkpoint-compatible legacy battery model architectures."""

import torch
from torch import nn


class LSTMRegressor(nn.Module):
    def __init__(self, input_dim=11, hidden_dim=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.regressor = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.regressor(lstm_out[:, -1, :])


class BiLSTMAttention(nn.Module):
    def __init__(self, input_dim=11, hidden_dim=64, num_layers=2, dropout=0.2, attention_dim=32):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        lstm_out_dim = hidden_dim * 2
        self.attention_w = nn.Sequential(
            nn.Linear(lstm_out_dim, attention_dim),
            nn.Tanh(),
            nn.Linear(attention_dim, 1),
        )
        self.regressor = nn.Linear(lstm_out_dim, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_scores = self.attention_w(lstm_out).squeeze(-1)
        attn_weights = torch.softmax(attn_scores, dim=1)
        weighted = torch.bmm(attn_weights.unsqueeze(1), lstm_out).squeeze(1)
        return self.regressor(weighted)
