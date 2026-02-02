import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import time
from torch.cuda.amp import autocast, GradScaler

# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# 检查是否支持混合精度训练
if device.type == 'cuda':
    print(f"CUDA device: {torch.cuda.get_device_name()}")
    print(f"CUDA capability: {torch.cuda.get_device_capability()}")
    print("支持混合精度训练" if torch.cuda.get_device_capability()[0] >= 7 else "可能不支持Tensor Cores")

# Hyper-parameters
num_epochs = 5
batch_size = 64
learning_rate = 0.001

# 数据预处理和加载
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

train_dataset = torchvision.datasets.CIFAR10(root='./data', train=True,
                                        download=True, transform=transform)
train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size,
                                          shuffle=True, num_workers=2)

test_dataset = torchvision.datasets.CIFAR10(root='./data', train=False,
                                       download=True, transform=transform)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size,
                                         shuffle=False, num_workers=2)

# 简单的CNN模型
class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(128 * 4 * 4, 512)
        self.fc2 = nn.Linear(512, 10)
        self.dropout = nn.Dropout(0.5)
        
    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))  # -> 32x16x16
        x = self.pool(torch.relu(self.conv2(x)))  # -> 64x8x8
        x = self.pool(torch.relu(self.conv3(x)))  # -> 128x4x4
        x = x.view(-1, 128 * 4 * 4)
        x = self.dropout(torch.relu(self.fc1(x)))
        x = self.fc2(x)
        return x

def train_with_mixed_precision(model, train_loader, criterion, optimizer, scaler, num_epochs=5):
    """使用混合精度训练"""
    model.train()
    total_time = 0
    
    for epoch in range(num_epochs):
        epoch_start = time.time()
        running_loss = 0.0
        
        for i, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            
            # 前向传播使用autocast
            with autocast():
                outputs = model(images)
                loss = criterion(outputs, labels)
            
            # 反向传播
            optimizer.zero_grad()
            # 缩放损失并反向传播
            scaler.scale(loss).backward()
            # 梯度裁剪（可选）
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            # 更新参数
            scaler.step(optimizer)
            # 更新缩放因子
            scaler.update()
            
            running_loss += loss.item()
            
            if (i + 1) % 100 == 0:
                print(f'Epoch [{epoch+1}/{num_epochs}], Step [{i+1}/{len(train_loader)}], Loss: {loss.item():.4f}')
        
        epoch_time = time.time() - epoch_start
        total_time += epoch_time
        print(f'Epoch [{epoch+1}] completed in {epoch_time:.2f}s, Average Loss: {running_loss/len(train_loader):.4f}')
    
    return total_time

def train_standard_precision(model, train_loader, criterion, optimizer, num_epochs=5):
    """使用标准精度训练"""
    model.train()
    total_time = 0
    
    for epoch in range(num_epochs):
        epoch_start = time.time()
        running_loss = 0.0
        
        for i, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            
            # 标准的前向传播
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            if (i + 1) % 100 == 0:
                print(f'Epoch [{epoch+1}/{num_epochs}], Step [{i+1}/{len(train_loader)}], Loss: {loss.item():.4f}')
        
        epoch_time = time.time() - epoch_start
        total_time += epoch_time
        print(f'Epoch [{epoch+1}] completed in {epoch_time:.2f}s, Average Loss: {running_loss/len(train_loader):.4f}')
    
    return total_time

def evaluate_model(model, test_loader):
    """评估模型准确率"""
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    accuracy = 100 * correct / total
    return accuracy

if __name__ == "__main__":
    print("=== 混合精度训练 vs 标准精度训练对比 ===\n")
    
    # 1. 标准精度训练
    print("1. 标准精度训练 (FP32)")
    model_fp32 = SimpleCNN().to(device)
    criterion_fp32 = nn.CrossEntropyLoss()
    optimizer_fp32 = optim.Adam(model_fp32.parameters(), lr=learning_rate)
    
    start_time = time.time()
    time_fp32 = train_standard_precision(model_fp32, train_loader, criterion_fp32, optimizer_fp32, num_epochs)
    accuracy_fp32 = evaluate_model(model_fp32, test_loader)
    
    print(f"标准精度训练完成:")
    print(f"  - 训练时间: {time_fp32:.2f}s")
    print(f"  - 测试准确率: {accuracy_fp32:.2f}%")
    print(f"  - 模型参数内存使用: {sum(p.numel() * p.element_size() for p in model_fp32.parameters()) / 1024**2:.2f} MB\n")
    
    # 2. 混合精度训练
    print("2. 混合精度训练 (FP16)")
    model_amp = SimpleCNN().to(device)
    criterion_amp = nn.CrossEntropyLoss()
    optimizer_amp = optim.Adam(model_amp.parameters(), lr=learning_rate)
    
    # 创建梯度缩放器
    scaler = GradScaler()
    
    time_amp = train_with_mixed_precision(model_amp, train_loader, criterion_amp, optimizer_amp, scaler, num_epochs)
    accuracy_amp = evaluate_model(model_amp, test_loader)
    
    print(f"混合精度训练完成:")
    print(f"  - 训练时间: {time_amp:.2f}s")
    print(f"  - 测试准确率: {accuracy_amp:.2f}%")
    print(f"  - 加速比: {time_fp32/time_amp:.2f}x")
    print(f"  - 准确率差异: {abs(accuracy_fp32 - accuracy_amp):.2f}%")
    
    # 3. 混合精度的好处总结
    print("\n=== 混合精度训练的优势 ===")
    print("1. 内存节省: FP16比FP32节省50%内存")
    print("2. 计算加速: 在支持的GPU上可提升1.5-3x速度")
    print("3. 保持精度: 通过梯度缩放保持训练稳定性")
    print("4. 更大批次: 节省的内存可用于增加批次大小")
    
    # 4. 使用注意事项
    print("\n=== 使用注意事项 ===")
    print("1. 需要CUDA GPU支持（建议Compute Capability >= 7.0）")
    print("2. 某些操作可能不支持FP16，会自动回退到FP32")
    print("3. 需要使用GradScaler处理梯度下溢问题")
    print("4. 模型评估时通常仍使用FP32确保精度")
