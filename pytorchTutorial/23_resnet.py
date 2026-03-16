import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import torch.nn.functional as F
import time

# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Hyper-parameters
num_epochs = 10
batch_size = 64
learning_rate = 0.001

# 数据预处理
transform = transforms.Compose([
    transforms.Resize(224),  # ResNet通常使用224x224输入
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

train_dataset = torchvision.datasets.CIFAR10(root='./data', train=True,
                                        download=True, transform=transform)
train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size,
                                          shuffle=True, num_workers=2)

test_dataset = torchvision.datasets.CIFAR10(root='./data', train=False,
                                       download=True, transform=transform)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size,
                                         shuffle=False, num_workers=2)

# 残差块 (Residual Block)
class BasicBlock(nn.Module):
    """基础残差块，用于ResNet18和ResNet34"""
    expansion = 1
    
    def __init__(self, in_channels, out_channels, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, 
                              stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                              stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        # 快捷连接 (shortcut connection)
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != self.expansion * out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, self.expansion * out_channels,
                         kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion * out_channels)
            )
    
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)  # 残差连接
        out = F.relu(out)
        return out

class Bottleneck(nn.Module):
    """瓶颈块，用于ResNet50, ResNet101, ResNet152"""
    expansion = 4
    
    def __init__(self, in_channels, out_channels, stride=1):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                              stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.conv3 = nn.Conv2d(out_channels, out_channels * self.expansion,
                              kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(out_channels * self.expansion)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels * self.expansion:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels * self.expansion,
                         kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels * self.expansion)
            )
    
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

# ResNet模型
class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(ResNet, self).__init__()
        self.in_channels = 64
        
        # 初始卷积层
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        # 残差层
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        
        # 全局平均池化和分类层
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)
    
    def _make_layer(self, block, out_channels, num_blocks, stride):
        """创建残差层"""
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_channels, out_channels, stride))
            self.in_channels = out_channels * block.expansion
        return nn.Sequential(*layers)
    
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.maxpool(out)
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.avgpool(out)
        out = out.view(out.size(0), -1)
        out = self.fc(out)
        return out

# 创建不同版本的ResNet
def ResNet18(num_classes=10):
    return ResNet(BasicBlock, [2, 2, 2, 2], num_classes)

def ResNet34(num_classes=10):
    return ResNet(BasicBlock, [3, 4, 6, 3], num_classes)

def ResNet50(num_classes=10):
    return ResNet(Bottleneck, [3, 4, 6, 3], num_classes)

def ResNet101(num_classes=10):
    return ResNet(Bottleneck, [3, 4, 23, 3], num_classes)

def ResNet152(num_classes=10):
    return ResNet(Bottleneck, [3, 8, 36, 3], num_classes)

def train_model(model, train_loader, test_loader, criterion, optimizer, num_epochs=10):
    """训练模型"""
    model.train()
    train_losses = []
    test_accuracies = []
    
    for epoch in range(num_epochs):
        running_loss = 0.0
        
        for i, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            
            # 前向传播
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            # 反向传播和优化
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            if (i + 1) % 100 == 0:
                print(f'Epoch [{epoch+1}/{num_epochs}], Step [{i+1}/{len(train_loader)}], Loss: {loss.item():.4f}')
        
        # 计算测试准确率
        test_accuracy = evaluate_model(model, test_loader)
        train_losses.append(running_loss / len(train_loader))
        test_accuracies.append(test_accuracy)
        
        print(f'Epoch [{epoch+1}/{num_epochs}] completed:')
        print(f'  - Average Loss: {running_loss / len(train_loader):.4f}')
        print(f'  - Test Accuracy: {test_accuracy:.2f}%')
    
    return train_losses, test_accuracies

def evaluate_model(model, test_loader):
    """评估模型"""
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
    
    return 100 * correct / total

def compare_models():
    """比较不同深度的ResNet模型"""
    models = {
        'ResNet18': ResNet18(),
        'ResNet34': ResNet34(),
        'ResNet50': ResNet50()
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n=== 训练 {name} ===")
        model = model.to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        
        # 计算参数数量
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"{name} 参数数量:")
        print(f"  - 总参数: {total_params:,}")
        print(f"  - 可训练参数: {trainable_params:,}")
        
        # 训练模型
        start_time = time.time()
        train_losses, test_accuracies = train_model(model, train_loader, test_loader, criterion, optimizer, num_epochs)
        training_time = time.time() - start_time
        
        results[name] = {
            'params': total_params,
            'final_accuracy': test_accuracies[-1],
            'training_time': training_time,
            'losses': train_losses,
            'accuracies': test_accuracies
        }
    
    # 打印比较结果
    print("\n=== 模型比较结果 ===")
    for name, result in results.items():
        print(f"{name}:")
        print(f"  - 参数数量: {result['params']:,}")
        print(f"  - 最终准确率: {result['final_accuracy']:.2f}%")
        print(f"  - 训练时间: {result['training_time']:.2f}s")

if __name__ == "__main__":
    print("=== ResNet 残差网络教程 ===\n")
    
    # 1. 演示单个模型训练
    print("1. 训练 ResNet18")
    model = ResNet18().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # 计算模型参数
    total_params = sum(p.numel() for p in model.parameters())
    print(f"ResNet18 总参数数量: {total_params:,}")
    
    # 训练模型
    train_losses, test_accuracies = train_model(model, train_loader, test_loader, criterion, optimizer, num_epochs)
    
    # 2. 解释残差连接的重要性
    print("\n=== 残差连接的重要性 ===")
    print("1. 解决梯度消失问题: 残差连接提供直接的梯度路径")
    print("2. 允许训练更深的网络: 理论上可以训练任意深度的网络")
    print("3. 身份映射: 当不需要某个层时，可以学会跳过它")
    print("4. 更好的优化: 使损失景观更平滑")
    
    # 3. ResNet架构演进
    print("\n=== ResNet架构演进 ===")
    print("ResNet18: 11.7M 参数 - 轻量级，适合快速实验")
    print("ResNet34: 21.8M 参数 - 平衡性能和效率")
    print("ResNet50: 25.6M 参数 - 使用瓶颈块，更深的网络")
    print("ResNet101: 44.5M 参数 - 用于需要更高精度的任务")
    print("ResNet152: 60.2M 参数 - 最深的ResNet，最高精度")
    
    # 4. 实际应用建议
    print("\n=== 实际应用建议 ===")
    print("1. 数据集较小时: 使用ResNet18或ResNet34")
    print("2. 需要高精度时: 使用ResNet50或ResNet101")
    print("3. 计算资源有限时: 使用预训练模型进行迁移学习")
    print("4. 自定义数据集时: 修改最后的全连接层类别数")
    print("5. 训练技巧: 使用学习率调度、数据增强、正则化")
