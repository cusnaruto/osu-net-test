import numpy as np
import pandas as pd
import torch.nn as nn

class OsuAimModel(nn.Module):
    def __init__(self, input_size=10, hidden_size=512, num_layers=3):
        super(OsuAimModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.embedding = nn.Sequential(
            nn.Linear(input_size, 128), nn.ReLU(),
            nn.Linear(128, hidden_size), nn.ReLU()
        )
        self.lstm = nn.LSTM(input_size=hidden_size, hidden_size=hidden_size, num_layers=num_layers, batch_first=True, dropout=0.2)
        self.aim_head = nn.Linear(hidden_size, 2)
        self.click_head = nn.Linear(hidden_size, 1)

    def forward(self, x, hidden=None):
        emb = self.embedding(x)
        lstm_out, new_hidden = self.lstm(emb, hidden)
        vel = self.aim_head(lstm_out)
        click_logits = self.click_head(lstm_out)
        return vel, click_logits, new_hidden