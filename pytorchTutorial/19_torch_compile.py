import torch
import time

def train(model, input_data):
    return model(input_data)

class SimpleModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(1024, 1024),
            torch.nn.ReLU(),
            torch.nn.Linear(1024, 1024),
            torch.nn.ReLU(),
            torch.nn.Linear(1024, 1024),
        )

    def forward(self, x):
        return self.layers(x)

if __name__ == "__main__":
    # Check for PyTorch 2.0+
    if int(torch.__version__.split(".")[0]) < 2:
        print("This tutorial requires PyTorch 2.0+")
        exit()

    device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
    print(f"Using device: {device}")
    
    model = SimpleModel().to(device)
    
    # Create random input
    input_data = torch.randn(1024, 1024).to(device)
    
    # 1. Eager Mode (Standard)
    print("Running in Eager mode...")
    start_time = time.time()
    for _ in range(100):
        _ = train(model, input_data)
        if device.type == 'cuda': torch.cuda.synchronize()
        if device.type == 'mps': torch.mps.synchronize()
    eager_duration = time.time() - start_time
    print(f"Eager mode time: {eager_duration:.4f}s")
    
    # 2. Compile Mode
    # torch.compile allows for JIT compilation of the model
    print("Compiling model...")
    compiled_model = torch.compile(model)
    
    # Warmup
    _ = train(compiled_model, input_data)
    
    print("Running in Compiled mode...")
    start_time = time.time()
    for _ in range(100):
        _ = train(compiled_model, input_data)
        if device.type == 'cuda': torch.cuda.synchronize()
        if device.type == 'mps': torch.mps.synchronize()
    compile_duration = time.time() - start_time
    print(f"Compiled mode time: {compile_duration:.4f}s")
    
    print(f"Speedup: {eager_duration / compile_duration:.2f}x")
