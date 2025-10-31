# make_deeplab_onnx.py
import torch, torchvision

# 1) 学習済み DeepLab v3 + MobileNetV3 Large（Cityscapes 21クラス）
model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(weights="DEFAULT")  # PyTorch 2.2 時点で公開[3]
model.eval()

# 2) ダミー入力（513×513 は元論文の標準解像度）
dummy = torch.randn(1, 3, 513, 513)

# 3) ONNX にエクスポート
torch.onnx.export(
    model, dummy, "deeplabv3_mnv3.onnx",
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    opset_version=12                                            # OpenCV 4.7+ が正式対応[3]
)
print("✓ deeplabv3_mnv3.onnx を生成しました")
