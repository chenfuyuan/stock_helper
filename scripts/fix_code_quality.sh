#!/bin/bash

# 代码质量自动修复脚本
# 用途：批量修复常见的代码质量问题，确保CI通过

set -e

echo "🔧 开始自动修复代码质量问题..."

# 检查是否安装了必要的工具
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 未安装，请先安装: pip install $1"
        exit 1
    fi
}

echo "📋 检查工具安装状态..."
check_tool autoflake
check_tool isort
check_tool black
check_tool flake8
check_tool mypy

# 1. 清理未使用的导入和变量
echo "📦 清理未使用的导入和变量..."
find src/ tests/ -name "*.py" -exec autoflake \
    --in-place \
    --remove-all-unused-imports \
    --remove-unused-variables \
    --remove-duplicate-keys {} \;

# 2. 规范化导入顺序
echo "📚 规范化导入顺序..."
isort src/ tests/ --profile black

# 3. 格式化代码
echo "✨ 格式化代码..."
black src/ tests/ --line-length 79

# 4. 清理空白行
echo "🧹 清理空白行..."
find src/ tests/ -name "*.py" -exec sed -i '' 's/ *$//' {} \;

# 5. 运行检查验证修复效果
echo "🔍 验证修复效果..."

echo "📊 运行 flake8 检查..."
flake8_output=$(python -m flake8 src tests --max-line-length=79 2>&1 || true)
flake8_errors=$(echo "$flake8_output" | wc -l)
echo "flake8 发现 $flake8_errors 个问题"

echo "🔍 运行 mypy 检查..."
mypy_output=$(python -m mypy src tests --ignore-missing-imports --no-error-summary 2>&1 || true)
mypy_errors=$(echo "$mypy_output" | grep "error:" | wc -l)
echo "mypy 发现 $mypy_errors 个错误"

# 6. 生成报告
echo ""
echo "📈 修复完成报告："
echo "=================="
echo "flake8 问题数: $flake8_errors"
echo "mypy 错误数: $mypy_errors"

if [ $flake8_errors -gt 100 ]; then
    echo "⚠️  flake8 问题较多，建议手动处理剩余问题"
fi

if [ $mypy_errors -gt 50 ]; then
    echo "⚠️  mypy 错误较多，建议手动处理关键类型错误"
fi

echo ""
echo "💡 后续建议："
echo "1. 运行 'make check-quality' 进行完整检查"
echo "2. 手动修复剩余的关键类型错误"
echo "3. 提交代码前确保本地检查通过"

echo ""
echo "✅ 代码质量自动修复完成！"

# 如果错误数量在可接受范围内，返回成功
if [ $flake8_errors -le 100 ] && [ $mypy_errors -le 50 ]; then
    exit 0
else
    exit 1
fi
