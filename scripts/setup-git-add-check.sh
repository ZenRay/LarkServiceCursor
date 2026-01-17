#!/bin/bash
# Quick setup for git-add-check workflow
# This script configures git aliases and shell aliases for convenient code checking

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🚀 Setting up Git Add with Checks workflow${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# 1. Ensure pre-commit is installed
echo -e "${YELLOW}1. Checking pre-commit installation...${NC}"
if command -v pre-commit &> /dev/null; then
    echo -e "${GREEN}✓ pre-commit is installed${NC}"
    pre-commit --version
else
    echo -e "${RED}✗ pre-commit is not installed${NC}"
    echo -e "${YELLOW}Installing pre-commit...${NC}"
    pip install pre-commit
fi
echo ""

# 2. Install pre-commit hooks
echo -e "${YELLOW}2. Installing pre-commit hooks...${NC}"
pre-commit install
echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
echo ""

# 3. Setup git alias
echo -e "${YELLOW}3. Setting up git alias 'cadd' (checked add)...${NC}"
git config alias.cadd '!f() { git add "$@" && pre-commit run --files "$@"; }; f'
echo -e "${GREEN}✓ Git alias 'git cadd' configured${NC}"
echo -e "   Usage: ${BLUE}git cadd <files>${NC}"
echo ""

# 4. Suggest shell alias
echo -e "${YELLOW}4. Shell alias suggestions:${NC}"
echo -e "   Add these lines to your ${BLUE}~/.bashrc${NC} or ${BLUE}~/.zshrc${NC}:"
echo -e "   ${GREEN}alias gadd='./scripts/git-add-check.sh'${NC}"
echo -e "   ${GREEN}alias gac='./scripts/git-add-check.sh'${NC}"
echo ""

# 5. Make scripts executable
echo -e "${YELLOW}5. Making scripts executable...${NC}"
chmod +x scripts/git-add-check.sh
chmod +x scripts/setup-git-add-check.sh
echo -e "${GREEN}✓ Scripts are now executable${NC}"
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Available commands:${NC}"
echo -e "  1. ${GREEN}./scripts/git-add-check.sh <files>${NC}"
echo -e "     Add files and run checks immediately"
echo ""
echo -e "  2. ${GREEN}git cadd <files>${NC}"
echo -e "     Git alias for add + check (shorter command)"
echo ""
echo -e "  3. ${GREEN}git add <files> && pre-commit run${NC}"
echo -e "     Manual workflow (most flexible)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  • Read ${BLUE}docs/dev-workflow.md${NC} for detailed guide"
echo -e "  • Try: ${GREEN}./scripts/git-add-check.sh src/lark_service/apaas/client.py${NC}"
echo -e "  • Try: ${GREEN}git cadd src/lark_service/apaas/client.py${NC}"
echo ""
