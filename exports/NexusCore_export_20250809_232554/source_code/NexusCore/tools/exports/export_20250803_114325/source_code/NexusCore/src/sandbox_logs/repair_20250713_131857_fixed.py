```python
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```
エラーメッセージから、Pythonのコード内に無効な文字（'、'）があることが原因と推測されます。そのため、その部分を削除しました。また、元のコードには「# Corrected from subtraction to addition」というコメントがありましたが、これは誤解を招く可能性があるため削除しました。