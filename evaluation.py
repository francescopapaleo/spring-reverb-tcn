import torch
import numpy as np

from model import TCN, causal_crop
from dataloader import SubsetRetriever
from config import *

import torch.nn as nn
import matplotlib.pyplot as plt

print("### Evaluation started...")

# Use GPU if available
if torch.cuda.is_available():
    device = "cuda"
    print("Using GPU")
else:
    device = "cpu"
    print("Using CPU")

print("")
print(f"Name: {model_to_evaluate}")

# Load the subset
subset_retriever = SubsetRetriever(SUBSET)
_, _, x_test_concate , y_test_concate  = subset_retriever.retrieve_data(concatenate=True)

# Load tensors
x = torch.tensor(x_test_concate, dtype=torch.float32)
y = torch.tensor(y_test_concate, dtype=torch.float32)
c = torch.tensor([0.0, 0.0], device=device).view(1,1,-1)

# Instantiate the model
model = TCN(
    n_inputs=input_channels,
    n_outputs=output_channels,
    cond_dim=cond_dim, 
    kernel_size=kernel_size, 
    n_blocks=n_blocks, 
    dilation_growth=dilation_growth, 
    n_channels=n_channels)

# Load the trained model to evaluate
load_this_model = os.path.join(MODELS, model_to_evaluate)
model = torch.load(load_this_model)
model.eval()

# Receptive field
rf = model.compute_receptive_field()

# Pad the input signal
x_pad = torch.nn.functional.pad(x, (rf-1, 0))

with torch.no_grad():
  y_pred = model(x_pad, c)

# Mean squared error
mse = torch.nn.MSELoss()
metric = mse(y_pred, y)

print(f"MSE: {metric.item()}")

# Error to signal 
error = torch.sum(torch.pow(y - y_pred, 2))
signal = torch.sum(torch.pow(y, 2))
esr = error / (signal + 1e-10)

print(f"ESR: {esr.item()}")

# Error to signal 
error_mean = torch.mean((y_pred - y) ** 2)
signal_mean = torch.mean(y ** 2)
esr_mean = error_mean / (signal_mean + 1e-10)

mse_sum = torch.nn.MSELoss(reduction='sum')
error_sum = mse_sum(y_pred, y)
signal_sum = mse_sum(y, torch.zeros_like(y))
esr_sum = error_sum / (signal_sum + 1e-10)

print(str(model_to_evaluate))
print(f"Mean Squared Error: {mse}")
print(f"Error-to-Signal Ratio (mean): {esr_mean}")
print(f"Error-to-Signal Ratio (sum): {esr_sum}")
print("")


print("")
print("### Evaluation by chunks...")

# Creating n chunks
x_parts = torch.chunk(x_pad, n_parts)
y_parts = torch.chunk(y, n_parts)

# Mean squared error
mse = torch.nn.MSELoss()
total_mse = 0
total_esr = 0

for x_part, y_part in zip(x_parts, y_parts):
    with torch.no_grad():
        y_pred = model(x_part, c)
    
    # Mean squared error
    metric = mse(y_pred, y_part)
    total_mse += metric.item()

    # Error to signal 
    error = torch.sum(torch.pow(y_part - y_pred, 2))
    signal = torch.sum(torch.pow(y_part, 2))
    esr = error / (signal + 1e-10)
    total_esr += esr.item()

# Average metrics over all parts
average_mse = total_mse / n_parts
average_esr = total_esr / n_parts

# Print results

print(f"Number of chunks: {n_parts}")

print(f"Average MSE: {average_mse}")
print(f"Average ESR: {average_esr}")

