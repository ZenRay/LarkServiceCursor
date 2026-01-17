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

# 3. Setup git alias (updated to use script for better workflow)
echo -e "${YELLOW}3. Setting up git aliases...${NC}"

# cadd - checked add (uses the smart script)
git config alias.cadd '!f() { ./scripts/git-add-check.sh "$@"; }; f'
echo -e "${GREEN}✓ Git alias 'git cadd' configured${NC}"
echo -e "   Usage: ${BLUE}git cadd <files>${NC}"

# cfmt - check format only
git config alias.cfmt '!f() { python -m ruff format --check "$@"; }; f'
echo -e "${GREEN}✓ Git alias 'git cfmt' configured${NC}"
echo -e "   Usage: ${BLUE}git cfmt <files>${NC} (check format without modifying)"

# fmt - format files
git config alias.fmt '!f() { python -m ruff format "$@"; }; f'
echo -e "${GREEN}✓ Git alias 'git fmt' configured${NC}"
echo -e "   Usage: ${BLUE}git fmt <files>${NC} (format files)"

# csync - commit with staging sync
git config alias.csync '!f() { ./scripts/git-commit-sync.sh "$@"; }; f'
echo -e "${GREEN}✓ Git alias 'git csync' configured${NC}"
echo -e "   Usage: ${BLUE}git csync -m \"message\"${NC} (auto-sync before commit)"

# check - run all quality checks
git config alias.check '!f() { ./scripts/check-all.sh "$@"; }; f'
echo -e "${GREEN}✓ Git alias 'git check' configured${NC}"
echo -e "   Usage: ${BLUE}git check${NC} (run all quality checks locally)"

echo ""

# 4. Suggest shell alias
echo -e "${YELLOW}4. Shell alias suggestions:${NC}"
echo -e "   Add these lines to your ${BLUE}~/.bashrc${NC} or ${BLUE}~/.zshrc${NC}:"
echo -e "   ${GREEN}alias gadd='./scripts/git-add-check.sh'${NC}"
echo -e "   ${GREEN}alias gac='./scripts/git-add-check.sh'${NC}"
echo -e "   ${GREEN}alias rfmt='python -m ruff format'${NC}"
echo ""

# 5. Make scripts executable
echo -e "${YELLOW}5. Making scripts executable...${NC}"
chmod +x scripts/git-add-check.sh
chmod +x scripts/git-commit-sync.sh
chmod +x scripts/check-all.sh
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
echo -e "     Smart workflow: format → add → check (recommended)"
echo ""
echo -e "  2. ${GREEN}git cadd <files>${NC}"
echo -e "     Same as #1, shorter command"
echo ""
echo -e "  3. ${GREEN}git fmt <files>${NC}"
echo -e "     Format files only (no add/check)"
echo ""
echo -e "  4. ${GREEN}git cfmt <files>${NC}"
echo -e "     Check format only (no modify)"
echo ""
echo -e "  5. ${GREEN}git csync -m \"message\"${NC}"
echo -e "     Commit with auto-sync (prevents staging/working dir mismatch)"
echo ""
echo -e "  6. ${GREEN}git check${NC}"
echo -e "     Run all quality checks (same config as CI/pre-commit)"
echo ""
echo -e "${YELLOW}Workflow improvements:${NC}"
echo -e "  ✅ Auto-format before staging (no surprises)"
echo -e "  ✅ Pre-commit hooks now in --check mode (no auto-modify)"
echo -e "  ✅ Prevents formatting loops"
echo -e "  ✅ Clear 3-step process: format → add → check"
echo -e "  ✅ Tests/ uses relaxed checks (no type annotation warnings)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  • Read ${BLUE}docs/dev-workflow.md${NC} for detailed guide"
echo -e "  • Try: ${GREEN}git check${NC} (run all checks locally)"
echo -e "  • Try: ${GREEN}git cadd src/lark_service/apaas/client.py${NC}"
echo -e "  • Try: ${GREEN}git csync -m \"your message\"${NC}"
echo ""
