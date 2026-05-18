# backend/train.py

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
print("🌐 已切换至 Hugging Face 国内镜像源")
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from transformers import ViTForImageClassification, ViTImageProcessor
from tqdm import tqdm  # 进度条库，需 pip install tqdm

# 1. 配置参数
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'dataset')
MODEL_NAME = 'google/vit-base-patch16-224' # 必须和 detector.py 用的一样
BATCH_SIZE = 16          # 一次训练多少张 (显存不够就改小，比如 8 或 16)
LEARNING_RATE = 2e-5     # 学习率 (微调通常要很小)
EPOCHS = 3               # 训练几轮 (演示用3轮，正式训练建议 10+)
SAVE_PATH = './best_model.pth' # 训练好的权重保存位置

# 自动选择设备 (优先 GPU)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🔥 使用设备: {device}")

def main():
    # 2. 数据预处理
    # ==========================================
    # 使用 ViT 自带的处理器来标准化图片
    processor = ViTImageProcessor.from_pretrained(MODEL_NAME)
    
    # 定义 PyTorch 的转换流
    data_transforms = {
        'train': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(), # 数据增强：随机翻转
            transforms.ToTensor(),
            transforms.Normalize(mean=processor.image_mean, std=processor.image_std)
        ]),
        'test': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=processor.image_mean, std=processor.image_std)
        ]),
    }

    # 加载数据集
    image_datasets = {x: datasets.ImageFolder(os.path.join(DATA_DIR, x), data_transforms[x])
                      for x in ['train', 'test']}
    
    dataloaders = {x: DataLoader(image_datasets[x], batch_size=BATCH_SIZE, shuffle=True)
                   for x in ['train', 'test']}
    
    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'test']}
    print(f"📦 数据加载完成: 训练集 {dataset_sizes['train']} 张, 验证集 {dataset_sizes['test']} 张")

    # 3. 初始化模型
    # ==========================================
    model = ViTForImageClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        ignore_mismatched_sizes=True
    )
    model.to(device)

    # 定义优化器 (AdamW) 和 损失函数 (交叉熵)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()

    # 4. 训练循环
    # ==========================================
    best_acc = 0.0

    for epoch in range(EPOCHS):
        print(f'\nEpoch {epoch+1}/{EPOCHS}')
        print('-' * 10)

        for phase in ['train', 'test']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            # 进度条
            pbar = tqdm(dataloaders[phase], desc=f"{phase} Phase")
            
            for inputs, labels in pbar:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                # 前向传播
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    logits = outputs.logits
                    _, preds = torch.max(logits, 1)
                    loss = criterion(logits, labels)

                    # 反向传播 (只在训练时)
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # 统计
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                
                # 更新进度条显示的 loss
                pbar.set_postfix({'loss': loss.item()})

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            # 保存最佳模型
            if phase == 'test' and epoch_acc > best_acc:
                best_acc = epoch_acc
                torch.save(model.state_dict(), SAVE_PATH)
                print(f"✅ 发现新高分模型 ({best_acc:.4f})，已保存到 {SAVE_PATH}")

    print(f'\n🎉 训练结束! 最佳准确率: {best_acc:.4f}')
    print(f'💾 权重文件已保存: {os.path.abspath(SAVE_PATH)}')

if __name__ == '__main__':
    main()