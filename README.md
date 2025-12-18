# IdiomsSolitaire

高性能中文成语接龙工具。

## 安装

```bash
git clone https://github.com/WangYihang/IdiomsSolitaire.git
cd IdiomsSolitaire
uv pip install .
```

## 使用

```bash
# 查找单个匹配成语
idiomssolitaire 一心一意

# 返回多个结果
idiomssolitaire 一心一意 --top 10

# 指定数据库
idiomssolitaire 一心一意 --db custom.db
```

## 特性

- 汉字匹配优先（首字相同优先显示）
- 支持返回多个结果
- 显示统计信息（匹配总数、耗时等）

## 许可证

MIT License
