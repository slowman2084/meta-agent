#!/bin/bash
# ===================================
# 敏感信息泄露检查脚本
# ===================================
# 用途：在提交代码前自动检查是否有敏感信息即将被提交
# 使用：./scripts/check_secrets.sh
# 
# 建议配置为 Git pre-commit hook：
# ln -s ../../scripts/check_secrets.sh .git/hooks/pre-commit
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 检查敏感信息..."
echo ""

# 1. 检查是否有配置文件被暂存（应该在 .gitignore 中）
echo "📋 检查配置文件..."
IGNORED_FILES=".env .mcp.json platform.yaml"

for file in $IGNORED_FILES; do
    if git diff --cached --name-only | grep -q "$file$"; then
        echo -e "${RED}❌ 错误：检测到 $file 即将被提交！${NC}"
        echo -e "${YELLOW}   这些文件包含敏感信息，不应提交到 Git。${NC}"
        echo -e "${YELLOW}   请运行：git restore --staged $file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ 未检测到敏感配置文件被暂存${NC}"
echo ""

# 2. 检查暂存区中是否有疑似密钥的内容
echo "🔐 检查疑似密钥内容..."

# 常见密钥模式
PATTERNS=(
    "sk-[a-zA-Z0-9]{20,}"           # OpenAI API Key
    "sk-ant-[a-zA-Z0-9-]{20,}"      # Anthropic API Key
    "api_key.*['\"][a-zA-Z0-9]{20,}"  # Generic API Key
    "secret.*['\"][a-zA-Z0-9]{20,}"   # Generic Secret
    "password.*['\"][^'\"]{8,}"       # Password
)

FOUND=0
for pattern in "${PATTERNS[@]}"; do
    # 检查暂存区内容，排除 example 文件
    matches=$(git diff --cached | grep -E "$pattern" | grep -v "example" | grep -v "#" || true)
    
    if [ -n "$matches" ]; then
        echo -e "${RED}❌ 检测到疑似密钥：${NC}"
        echo "$matches" | head -5
        FOUND=1
    fi
done

if [ $FOUND -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  警告：检测到疑似敏感信息即将被提交！${NC}"
    echo -e "${YELLOW}   如果这些是真实的密钥，请立即取消暂存：${NC}"
    echo -e "${YELLOW}   git restore --staged <file>${NC}"
    echo ""
    echo -e "${YELLOW}   如果这些是占位符或示例，请确保：${NC}"
    echo -e "${YELLOW}   1. 文件名包含 'example' 或在注释中说明${NC}"
    echo -e "${YELLOW}   2. 使用明显的占位符（如 'your-key-here'）${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 未检测到疑似密钥内容${NC}"
echo ""

# 3. 检查 .gitignore 是否包含必要的规则
echo "📝 检查 .gitignore 配置..."

REQUIRED_IGNORES=(
    ".env"
    ".env.*"
    "!.env.example"
    ".mcp.json"
    "**/platform.yaml"
)

MISSING=0
for pattern in "${REQUIRED_IGNORES[@]}"; do
    if ! grep -q "^${pattern}$" .gitignore; then
        echo -e "${YELLOW}⚠️  .gitignore 缺少规则：$pattern${NC}"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo -e "${YELLOW}   建议添加缺失的规则到 .gitignore${NC}"
else
    echo -e "${GREEN}✅ .gitignore 配置正确${NC}"
fi

echo ""

# 4. 检查是否有实际的配置文件存在
echo "📁 检查配置文件状态..."

if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env 文件存在${NC}"
    # 检查是否有真实内容
    if grep -qE "(sk-|api_key|secret)" .env && ! grep -q "your-.*-here" .env; then
        echo -e "${GREEN}   包含真实配置${NC}"
    else
        echo -e "${YELLOW}   似乎使用模板内容，请填入真实密钥${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  .env 文件不存在，请从 .env.example 创建${NC}"
    echo -e "${YELLOW}   cp .env.example .env${NC}"
fi

if [ -f ".mcp.json" ]; then
    echo -e "${GREEN}✅ .mcp.json 文件存在${NC}"
else
    echo -e "${YELLOW}ℹ️  .mcp.json 文件不存在（如需 MCP 服务，请创建）${NC}"
fi

echo ""

# 5. 总结
echo "======================================"
if [ $FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ 检查通过，可以安全提交${NC}"
    echo ""
    echo "建议操作："
    echo "  git commit -m \"your message\""
    exit 0
else
    echo -e "${RED}❌ 检查未通过，请先处理敏感信息${NC}"
    exit 1
fi
