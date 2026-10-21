# 多论文结构化对比报告

- 生成时间（UTC）：2026-10-21T14:50:34+00:00
- 抽取模式：`llm`
- 论文数量：3

> **可比性声明**：证据核验只证明引文出现在指定 PDF 页码，不代表事实语义正确。只有数据集、指标、训练比例和补丁尺寸全部一致的数值才会被放入同一可比组；即使如此，数据划分、随机种子和评估代码仍可能不同。训练比例缺失的数值不参与排名。

## 1. 论文概览

| 论文 | 标题 | 年份 | 方法 | 模型家族 | 数据集 | 指标数 |
|---|---|---|---|---|---|---|
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN: Exploring 3D-2D CNN Feature Hierarchy for Hyperspectral Image Classification | 2019 | HybridSN, 3D-CNN, 2D-CNN, PCA | CNN | Indian Pines, Pavia University, Salinas Scene | 102 |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | Spectral–Spatial Residual Network for Hyperspectral Image Classification: A 3-D Deep Learning Framework | 2018 | SSRN, 3-D CNN, SAE, kernel SVM, SPC, SPA, CNNL | CNN | Indian Pines, Kennedy Space Center, University of Pavia | 2 |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | Weighted Feature Fusion of Convolutional Neural Network and Graph Attention Network for Hyperspectral Image Classification | 2022 | WFCG, GAT, CNN, SLIC, SVM, 1D-CNN, JSAN, HybirdSN, GCN, MDGCN, CEGCN | CNN, GNN | Indian Pines, University of Pavia, WHU-Hi-HongHu | 1 |

## 2. 研究方法对比

| 论文 | 方法/模型 | 家族 | 图构建 | 证据状态 |
|---|---|---|---|---|
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | CNN | 未描述 | verified_quote |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | CNN | 未描述 | verified_quote |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | CNN | 未描述 | verified_quote |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | PCA | 未判定 | 未描述 | verified_quote |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | SSRN | CNN | 未描述 | verified_quote |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | 3-D CNN | CNN | 未描述 | verified_quote |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | SAE | 未判定 | 未描述 | verified_quote |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | kernel SVM | CNN | 未描述 | verified_quote |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | SPC | 未判定 | 未描述 | verified_quote |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | SPA | 未判定 | 未描述 | verified_quote |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | CNNL | CNN | 未描述 | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | WFCG | CNN | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | GAT | GNN | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | CNN | CNN | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | SLIC | 未判定 | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | SVM | 未判定 | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | 1D-CNN | CNN | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | JSAN | 未判定 | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | HybirdSN | CNN | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | GCN | GNN | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | MDGCN | 未判定 | superpixel | verified_quote |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | CEGCN | CNN | superpixel | verified_quote |

## 3. 数据集使用矩阵

| 数据集 | HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf |
|---|---|---|---|
| Indian Pines | ✓ p.1 | ✓ p.1 | ✓ p.6 |
| Pavia University | ✓ p.1 | ✓ | ✓ |
| Salinas Scene | ✓ p.1 | ✓ | ✓ |
| Kennedy Space Center | ✓ | ✓ p.1 | ✓ |
| University of Pavia | ✓ | ✓ p.1 | ✓ p.6 |
| WHU-Hi-HongHu | ✓ | ✓ | ✓ p.6 |

## 4. 实验指标与可比性

| 论文 | 方法 | 来源 | 数据集 | 指标 | 数值 | 训练比例 | 补丁 | 证据 | 可比 | 组内排名 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | OA | 85.30 ± 2.8 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | Kappa | 83.10 ± 3.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | AA | 79.03 ± 2.7 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | OA | 94.34 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | Kappa | 92.50 ± 0.7 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | AA | 92.98 ± 0.4 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | OA | 92.95 ± 0.3 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | Kappa | 92.11 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | SVM | text | 未注明 | AA | 94.60 ± 2.3 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | OA | 89.48 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | Kappa | 87.96 ± 0.5 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | AA | 86.14 ± 0.8 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | OA | 97.86 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | Kappa | 97.16 ± 0.5 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | AA | 96.55 ± 0.0 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | OA | 97.38 ± 0.0 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | Kappa | 97.08 ± 0.1 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | text | 未注明 | AA | 98.84 ± 0.1 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | OA | 91.10 ± 0.4 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | Kappa | 89.98 ± 0.5 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | AA | 91.58 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | OA | 96.53 ± 0.1 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | Kappa | 95.51 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | AA | 97.57 ± 1.3 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | OA | 93.96 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | Kappa | 93.32 ± 0.5 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | text | 未注明 | AA | 97.01 ± 0.6 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | M3D-CNN | text | 未注明 | OA | 95.32 ± 0.1 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | M3D-CNN | text | 未注明 | Kappa | 94.70 ± 0.2 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | M3D-CNN | text | 未注明 | AA | 96.41 ± 0.7 | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Indian Pines | OA | 89.48 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Indian Pines | Kappa | 87.96 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Indian Pines | AA | 86.14 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Pavia University | OA | 97.86 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Pavia University | Kappa | 97.16 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Pavia University | AA | 96.55 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Salinas Scene | OA | 97.38 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Salinas Scene | Kappa | 97.08 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Salinas Scene | AA | 98.84 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | OA | 91.10 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | Kappa | 89.98 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | AA | 91.58 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | OA | 96.53 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | Kappa | 95.51 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | AA | 97.57 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | OA | 93.96 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | Kappa | 93.32 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | AA | 97.01 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | OA | 95.32 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | Kappa | 94.70 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | AA | 96.41 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | OA | 95.76 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | Kappa | 94.50 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | AA | 95.08 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | OA | 94.79 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | Kappa | 94.20 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | AA | 96.25 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Indian Pines | OA | 99.75 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Indian Pines | Kappa | 99.71 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Indian Pines | AA | 99.63 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Pavia University | OA | 99.98 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Pavia University | Kappa | 99.98 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Pavia University | AA | 99.97 | 30% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Salinas Scene | OA | 100 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Salinas Scene | Kappa | 100 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Salinas Scene | AA | 100 | 30% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Indian Pines | OA | 80.27 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Indian Pines | Kappa | 78.26 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Indian Pines | AA | 68.32 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Pavia University | OA | 96.63 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Pavia University | Kappa | 95.53 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Pavia University | AA | 94.84 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Salinas Scene | OA | 96.34 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Salinas Scene | Kappa | 95.93 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 2D-CNN | table | Salinas Scene | AA | 94.36 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | OA | 82.62 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | Kappa | 79.25 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | AA | 76.51 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | OA | 96.34 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | Kappa | 94.90 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | AA | 97.03 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | OA | 85.00 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | Kappa | 83.20 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | AA | 89.63 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | OA | 81.39 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | Kappa | 81.20 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Indian Pines | AA | 75.22 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | OA | 95.95 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | Kappa | 93.40 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Pavia University | AA | 97.52 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | OA | 94.20 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | Kappa | 93.61 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | 3D-CNN | table | Salinas Scene | AA | 96.66 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Indian Pines | OA | 98.39 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Indian Pines | Kappa | 98.16 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Indian Pines | AA | 98.01 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Pavia University | OA | 99.72 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Pavia University | Kappa | 99.64 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Pavia University | AA | 99.20 | 10% | 未注明 | verified_quote | 否 | - | 缺少输入补丁尺寸 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Salinas Scene | OA | 99.98 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Salinas Scene | Kappa | 99.98 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf | HybridSN | table | Salinas Scene | AA | 99.98 | 10% | 25x25 | verified_quote | 否 | - | 没有其他论文在完全相同的条件下报告该指标，无法排名 |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | SSRN | text | 未注明 | OA | 99.61% | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf | CNN | text | 未注明 | OA | 97.08% | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |
| Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf | WFCG | text | 未注明 | OA | 90.86% | 未注明 | 未注明 | verified_quote | 否 | - | 指标未关联到具体数据集；缺少训练样本比例；缺少输入补丁尺寸 |

### 不可比项与风险提示

- **metric_dataset_missing**：部分指标没有可靠关联到数据集，不能与其他论文的数值并列比较。
- **patch_size_missing**：输入补丁尺寸缺失，空间上下文不同也会影响指标可比性。
- **protocol_mismatch**：Indian Pines 的 OA 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Indian Pines 的 Kappa 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Indian Pines 的 AA 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Pavia University 的 OA 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Pavia University 的 Kappa 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Pavia University 的 AA 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Salinas Scene 的 OA 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Salinas Scene 的 Kappa 在不同训练比例下被报告（10%, 30%），不可直接排名。
- **protocol_mismatch**：Salinas Scene 的 AA 在不同训练比例下被报告（10%, 30%），不可直接排名。

## 5. 单篇论文画像

### HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf

- 标题：HybridSN: Exploring 3D-2D CNN Feature Hierarchy for Hyperspectral Image Classification
- 年份：2019
- 优势（有证据支撑的事实）：方法名称均能定位到 PDF 原文；报告了 3 个可在原文定位的数据集；报告了 102 条可定位的实验指标；记录了训练样本比例等实验条件
- 局限/缺失：作者信息未可靠抽取；部分指标未关联到数据集；部分指标缺少训练样本比例
- 适用场景：适合作为局部空谱特征提取的基线对照；在这些数据集上有实验记录，可优先做同数据集复现对照：Indian Pines, Pavia University, Salinas Scene；以上为规则生成的阅读提示，不是论文作者的结论

### spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf

- 标题：Spectral–Spatial Residual Network for Hyperspectral Image Classification: A 3-D Deep Learning Framework
- 年份：2018
- 优势（有证据支撑的事实）：方法名称均能定位到 PDF 原文；报告了 3 个可在原文定位的数据集；报告了 2 条可定位的实验指标；记录了训练样本比例等实验条件
- 局限/缺失：作者信息未可靠抽取；部分指标未关联到数据集；部分指标缺少训练样本比例
- 适用场景：适合作为局部空谱特征提取的基线对照；在这些数据集上有实验记录，可优先做同数据集复现对照：Indian Pines, Kennedy Space Center, University of Pavia；以上为规则生成的阅读提示，不是论文作者的结论

### Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf

- 标题：Weighted Feature Fusion of Convolutional Neural Network and Graph Attention Network for Hyperspectral Image Classification
- 年份：2022
- 优势（有证据支撑的事实）：方法名称均能定位到 PDF 原文；报告了 3 个可在原文定位的数据集；报告了 1 条可定位的实验指标；记录了训练样本比例等实验条件；描述了图构建方式：superpixel
- 局限/缺失：作者信息未可靠抽取；部分指标未关联到数据集；部分指标缺少训练样本比例
- 适用场景：适合考察图结构建模、邻接关系构建在空谱分类中的作用；适合作为局部空谱特征提取的基线对照；在这些数据集上有实验记录，可优先做同数据集复现对照：Indian Pines, University of Pavia, WHU-Hi-HongHu；以上为规则生成的阅读提示，不是论文作者的结论

## 6. 方法与结论的人工复核清单

- [ ] 核对每个数值对应的数据划分方式（随机/固定/地理划分）与随机种子。
- [ ] 核对 OA/AA/Kappa 是否在同一评估代码、同一类别集合下计算。
- [ ] 核对训练样本比例与输入补丁尺寸是否确实对应表中数值。
- [ ] 对表格中的数字回到 PDF 原页人工确认，不要只依赖文本抽取。
- [ ] 若论文使用不同数据集，不要用跨数据集均值或单一 OA 排名。

## 证据附录

每条本地引用均可用下方页码与原文片段复核。

### HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf

- 文档 ID：`7993e30c-31b4-43bf-bc5d-cafc7da29714`
- 抽取模式：`llm`；缺失字段：metadata.authors, graph_constructions

| 字段 | 页码 | 状态 | 引用 |
|---|---|---|---|
| metadata.title | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "HybridSN: Exploring 3D-2D CNN Feature Hierarchy for Hyperspectral Image Classiﬁcation"]] |
| metadata.year | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "PUBLISHED IN IEEE GEOSCIENCE AND REMOTE SENSING LETTERS (DOI: 10.1109/LGRS.2019.2918719)"]] |
| metadata.venue | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "PUBLISHED IN IEEE GEOSCIENCE AND REMOTE SENSING LETTERS"]] |
| method:HybridSN | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "This letter proposes a Hybrid Spectral Convolutional Neural Network (HybridSN) for HSI classiﬁcation."]] |
| method:3D-CNN | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "The 3D-CNN facilitates the joint spatial-spectral feature representation from a stack of spectral bands."]] |
| method:2D-CNN | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "The 2D-CNN on top of the 3D-CNN further learns more abstract level spatial representation."]] |
| method:PCA | 2 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.2 "the traditional principal component analysis (PCA) is applied over the original HSI data ( I) along spectral bands."]] |
| dataset:Indian Pines | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "Indian Pines, Pavia University and Salinas Scene remote sensing datasets"]] |
| dataset:Pavia University | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "Indian Pines, Pavia University and Salinas Scene remote sensing datasets"]] |
| dataset:Salinas Scene | 1 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.1 "Indian Pines, Pavia University and Salinas Scene remote sensing datasets"]] |
| condition | 4 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.4 "The 30% and 70% of the data are randomly divided into training and testing groups, respectively"]] |
| condition | 4 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.4 "The 30% and 70% of the data are randomly divided into training and testing groups, respectively"]] |
| condition | 4 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.4 "The 30% and 70% of the data are randomly divided into training and testing groups, respectively"]] |
| condition | 4 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.4 "less amount of training data, i.e., 10% only"]] |
| condition | 4 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.4 "less amount of training data, i.e., 10% only"]] |
| condition | 4 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.4 "less amount of training data, i.e., 10% only"]] |
| metric:OA=85.30 ± 2.8 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:Kappa=83.10 ± 3.2 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:AA=79.03 ± 2.7 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:OA=94.34 ± 0.2 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:Kappa=92.50 ± 0.7 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:AA=92.98 ± 0.4 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:OA=92.95 ± 0.3 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:Kappa=92.11 ± 0.2 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:AA=94.60 ± 2.3 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "SVM 85.30 ± 2.8 83.10 ± 3.2 79.03 ± 2.7 94.34 ± 0.2 92.50 ± 0.7 92.98 ± 0.4 92.95 ± 0.3 92.11 ± 0.2 94.60 ± 2.3"]] |
| metric:OA=89.48 ± 0.2 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:Kappa=87.96 ± 0.5 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:AA=86.14 ± 0.8 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:OA=97.86 ± 0.2 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:Kappa=97.16 ± 0.5 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:AA=96.55 ± 0.0 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:OA=97.38 ± 0.0 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:Kappa=97.08 ± 0.1 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:AA=98.84 ± 0.1 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "2D-CNN 89.48 ± 0.2 87.96 ± 0.5 86.14 ± 0.8 97.86 ± 0.2 97.16 ± 0.5 96.55 ± 0.0 97.38 ± 0.0 97.08 ± 0.1 98.84 ± 0.1"]] |
| metric:OA=91.10 ± 0.4 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "3D-CNN 91.10 ± 0.4 89.98 ± 0.5 91.58 ± 0.2 96.53 ± 0.1 95.51 ± 0.2 97.57 ± 1.3 93.96 ± 0.2 93.32 ± 0.5 97.01 ± 0.6"]] |
| metric:Kappa=89.98 ± 0.5 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "3D-CNN 91.10 ± 0.4 89.98 ± 0.5 91.58 ± 0.2 96.53 ± 0.1 95.51 ± 0.2 97.57 ± 1.3 93.96 ± 0.2 93.32 ± 0.5 97.01 ± 0.6"]] |
| metric:AA=91.58 ± 0.2 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "3D-CNN 91.10 ± 0.4 89.98 ± 0.5 91.58 ± 0.2 96.53 ± 0.1 95.51 ± 0.2 97.57 ± 1.3 93.96 ± 0.2 93.32 ± 0.5 97.01 ± 0.6"]] |
| metric:OA=96.53 ± 0.1 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "3D-CNN 91.10 ± 0.4 89.98 ± 0.5 91.58 ± 0.2 96.53 ± 0.1 95.51 ± 0.2 97.57 ± 1.3 93.96 ± 0.2 93.32 ± 0.5 97.01 ± 0.6"]] |
| metric:Kappa=95.51 ± 0.2 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "3D-CNN 91.10 ± 0.4 89.98 ± 0.5 91.58 ± 0.2 96.53 ± 0.1 95.51 ± 0.2 97.57 ± 1.3 93.96 ± 0.2 93.32 ± 0.5 97.01 ± 0.6"]] |
| metric:AA=97.57 ± 1.3 | 3 | verified_quote | [[doc:7993e30c-31b4-43bf-bc5d-cafc7da29714 p.3 "3D-CNN 91.10 ± 0.4 89.98 ± 0.5 91.58 ± 0.2 96.53 ± 0.1 95.51 ± 0.2 97.57 ± 1.3 93.96 ± 0.2 93.32 ± 0.5 97.01 ± 0.6"]] |
| …… | | | 其余 78 条已省略 |

### spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf

- 文档 ID：`e79a5a51-a47c-48ea-bdc0-261f8101f173`
- 抽取模式：`llm`；缺失字段：metadata.authors, graph_constructions

| 字段 | 页码 | 状态 | 引用 |
|---|---|---|---|
| metadata.title | 1 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.1 "Spectral–Spatial Residual Network for Hyperspectral Image Classiﬁcation: A 3-D Deep Learning Framework"]] |
| metadata.year | 1 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.1 "IEEE TRANSACTIONS ON GEOSCIENCE AND REMOTE SENSING, VOL. 56, NO. 2, FEBRUARY 2018 847"]] |
| metadata.venue | 1 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.1 "IEEE TRANSACTIONS ON GEOSCIENCE AND REMOTE SENSING, VOL. 56, NO. 2, FEBRUARY 2018 847"]] |
| method:SSRN | 1 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.1 "we designed an end-to-end spectral– spatial residual network (SSRN) that takes raw 3-D cubes as input data without feature en gineering for hyperspectral image classiﬁcation."]] |
| method:3-D CNN | 2 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.2 "3-D CNNs were adopted to extract deep spectral–spatial features directly from raw HS Is and delivered promising classiﬁcation outcomes [22]."]] |
| method:SAE | 2 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.2 "the stacked autoen- coders (SAEs) were used as f eature extractors to capture the representative stacked spectral and spatial features with a greedy layerwise pretraining strategy [17]."]] |
| method:kernel SVM | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "We compared the SSRN with the kernel SVM [31] and state-of-the-art deep learning models, such as SAE [17] and 3-D CNN [22]."]] |
| method:SPC | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "we also tested the networks that only contain the spectral feature learning part (SPC) and the ones that only contain spatial feature learning part (SPA)."]] |
| method:SPA | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "we also tested the networks that only contain the spectral feature learning part (SPC) and the ones that only contain spatial feature learning part (SPA)."]] |
| method:CNNL | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "we evaluated the longer versions of 3-D CNN (denote as CNNL) generated from the SPA models without skip connections"]] |
| dataset:Indian Pines | 1 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.1 "Indian Pines, Kennedy Space Center, and University of Pavia."]] |
| dataset:Kennedy Space Center | 1 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.1 "Indian Pines, Kennedy Space Center, and University of Pavia."]] |
| dataset:University of Pavia | 1 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.1 "Indian Pines, Kennedy Space Center, and University of Pavia."]] |
| condition | 6 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.6 "In the IN and KSC data sets, 20%, 10%, and 70% of the labeled data are randomly assigned to training, validation, and testing groups, respectively."]] |
| condition | 6 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.6 "In the IN and KSC data sets, 20%, 10%, and 70% of the labeled data are randomly assigned to training, validation, and testing groups, respectively."]] |
| condition | 6 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.6 "In the UP data sets, the ratio is 10%:10%:80%."]] |
| condition | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "we set the same input volume size of 7 ×7×b for all methods and tuned these competitors to their optimal settings. We randomly selected 20%, 20%, and 10% labeled 3-D HSI cubes as training groups for IN, KSC, and UP data sets, respectively."]] |
| condition | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "we set the same input volume size of 7 ×7×b for all methods and tuned these competitors to their optimal settings. We randomly selected 20%, 20%, and 10% labeled 3-D HSI cubes as training groups for IN, KSC, and UP data sets, respectively."]] |
| condition | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "we set the same input volume size of 7 ×7×b for all methods and tuned these competitors to their optimal settings. We randomly selected 20%, 20%, and 10% labeled 3-D HSI cubes as training groups for IN, KSC, and UP data sets, respectively."]] |
| metric:OA=99.61% | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "in the KSC data set, SSRN (99.61%) delivered a roughly 2.5% increase of mean overall classiﬁcation accuracy compared with CNN (97.08%)."]] |
| metric:OA=97.08% | 8 | verified_quote | [[doc:e79a5a51-a47c-48ea-bdc0-261f8101f173 p.8 "in the KSC data set, SSRN (99.61%) delivered a roughly 2.5% increase of mean overall classiﬁcation accuracy compared with CNN (97.08%)."]] |

### Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf

- 文档 ID：`dfc0c118-efcf-438d-9232-2c72d2a6feff`
- 抽取模式：`llm`；缺失字段：metadata.authors

| 字段 | 页码 | 状态 | 引用 |
|---|---|---|---|
| metadata.title | 1 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.1 "Weighted Feature Fusion of Convolutional Neural Network and Graph Attention Network for Hyperspectral Image Classiﬁcation"]] |
| metadata.year | 1 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.1 "IEEE TRANSACTIONS ON IMAGE PROCESSING, VOL. 31, 2022 1559"]] |
| metadata.venue | 1 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.1 "IEEE TRANSACTIONS ON IMAGE PROCESSING, VOL. 31, 2022 1559"]] |
| method:WFCG | 1 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.1 "we propose Weighted Feature Fusion of Convolutional Neural Network and Graph Attention Network (WFCG) for HSI classi- ﬁcation"]] |
| method:GAT | 1 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.1 "We ﬁrst establish GAT with the help of superpixel-based encoder and decoder modules."]] |
| method:CNN | 1 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.1 "Then we combined the attention mechanism to construct CNN."]] |
| method:SLIC | 4 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.4 "we adopt Simple Linear Iterative Clustering (SLIC) [42] to group pixels into perceptually meaningful superpixels."]] |
| method:SVM | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "including machine learning-based method, i.e., support vector machine (SVM)"]] |
| method:1D-CNN | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "CNN-based methods, i.e., 1D-CNN [49]"]] |
| method:JSAN | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "Joint Spatial–Spectral Atten- tion Network (JSAN) [50]"]] |
| method:HybirdSN | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "3D-2D SN spectral CNN (HybirdSN) [26]"]] |
| method:GCN | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "GNN-based methods, i.e., Graph Convolu- tion Network (GCN) [32]"]] |
| method:MDGCN | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "Multi-scale Dynamic Graph Convo- lutional Network (MDGCN) [33]"]] |
| method:CEGCN | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "CNN-Enhanced Graph Convolutional Network (CEGCN) [34]"]] |
| dataset:Indian Pines | 6 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.6 "the Indian Pines dataset, the University of Pavia dataset, and the WHU-Hi-HongHu dataset."]] |
| dataset:University of Pavia | 6 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.6 "the Indian Pines dataset, the University of Pavia dataset, and the WHU-Hi-HongHu dataset."]] |
| dataset:WHU-Hi-HongHu | 6 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.6 "the Indian Pines dataset, the University of Pavia dataset, and the WHU-Hi-HongHu dataset."]] |
| graph:superpixel | 4 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.4 "we adopt Simple Linear Iterative Clustering (SLIC) [42] to group pixels into perceptually meaningful superpixels."]] |
| condition | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "For the University of Pavia dataset and the WHU-Hi-HongHu dataset, because they have more labels, 0.1% the labels are selected as the training set an d the validation set."]] |
| condition | 7 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.7 "For the University of Pavia dataset and the WHU-Hi-HongHu dataset, because they have more labels, 0.1% the labels are selected as the training set an d the validation set."]] |
| metric:OA=90.86% | 8 | verified_quote | [[doc:dfc0c118-efcf-438d-9232-2c72d2a6feff p.8 "the OA of the proposed WFCG still achieved 90.86%"]] |
