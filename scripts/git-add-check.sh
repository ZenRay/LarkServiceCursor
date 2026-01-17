#!/bin/bash
# Git add with pre-commit checks
# Usage: ./scripts/git-add-check.sh <files...>
#
# This script adds files to git staging area and immediately runs
# pre-commit checks on them. If checks fail, files remain staged
# for easy fixing and re-checking.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if files are provided
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: No files specified${NC}"
    echo -e "${YELLOW}Usage: $0 <files...>${NC}"
    echo -e "${YELLOW}Example: $0 src/lark_service/apaas/client.py${NC}"
    exit 1
fi

# Store files for later use
FILES="$@"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📝 Adding files to staging area...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Add files to staging
git add "$@"

# Get list of staged files for display
STAGED_FILES=$(git diff --cached --name-only)
echo -e "${GREEN}✓ Staged files:${NC}"
echo "$STAGED_FILES" | sed 's/^/  • /'
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🔍 Running code quality checks...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Run pre-commit checks on staged files
if pre-commit run --files "$@"; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ All checks passed! Ready to commit.${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "   ${GREEN}git commit -m \"your message\"${NC}"
    exit 0
else
    # Check if files were auto-fixed by pre-commit hooks (e.g., ruff-format)
    MODIFIED_FILES=$(git diff --name-only "$@" 2>/dev/null)

    if [ -n "$MODIFIED_FILES" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Some hooks auto-fixed the files. Re-staging changes...${NC}"
        echo -e "${GREEN}Modified files:${NC}"
        echo "$MODIFIED_FILES" | sed 's/^/  • /'

        # Re-add the modified files
        git add "$@"

        echo ""
        echo -e "${YELLOW}🔄 Running checks again on fixed files...${NC}"

        # Run checks again
        if pre-commit run --files "$@"; then
            echo ""
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${GREEN}✅ All checks passed after auto-fix! Ready to commit.${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${YELLOW}Next steps:${NC}"
            echo -e "   ${GREEN}git commit -m \"your message\"${NC}"
            exit 0
        else
            echo ""
            echo -e "${RED}❌ Checks still failing after auto-fix.${NC}"
            echo -e "${YELLOW}💡 Please manually fix the remaining issues and run:${NC}"
            echo -e "   ${GREEN}$0 $FILES${NC}"
            exit 1
        fi
    else
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
        echo -e "${RED}❌ Checks failed! Please fix the issues.${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}💡 Files are still staged. After fixing, run:${NC}"
        echo -e "   ${GREEN}$0 $FILES${NC}"
        echo ""
        echo -e "${YELLOW}Or to unstage and start over:${NC}"
        echo -e "   ${BLUE}git reset HEAD $FILES${NC}"
        exit 1
    fi
fi
