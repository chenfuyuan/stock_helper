.PHONY: install test lint format fix-quality check-quality run clean

install:
	pip install -r requirements.txt

export-deps:
	pip freeze > requirements.txt

test:
	pytest tests/ --cov=src --cov-report=term-missing

lint:
	flake8 src tests --max-line-length=79
	mypy src tests --ignore-missing-imports

format:
	black src tests --line-length=79
	isort src tests --profile black

fix-quality:
	@echo "🔧 开始自动修复代码质量问题..."
	# 清理未使用的导入和变量
	find src/ tests/ -name "*.py" -exec autoflake \
		--in-place \
		--remove-all-unused-imports \
		--remove-unused-variables \
		--remove-duplicate-keys {} \;
	# 规范化导入顺序
	isort src tests --profile black
	# 格式化代码
	black src tests --line-length=79
	# 清理空白行
	find src/ tests/ -name "*.py" -exec sed -i '' 's/ *$//' {} \;
	@echo "✅ 代码质量修复完成！"

check-quality: lint test
	@echo "✅ 所有质量检查通过！"

ci-check:
	@echo "🚀 运行CI检查..."
	flake8 src tests --max-line-length=79
	mypy src tests --ignore-missing-imports
	pytest tests/ --cov=src --cov-report=term-missing
	@echo "✅ CI检查完成！"

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
