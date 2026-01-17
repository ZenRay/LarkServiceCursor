#!/bin/bash
# Git add with pre-commit checks
# Usage: ./scripts/git-add-check.sh <files...>
#
# This script adds files to git staging area and immediately runs
# pre-commit checks on them. If format issues are detected, it auto-formats
# and re-checks to ensure a smooth workflow.

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
echo -e "${YELLOW}📝 Step 1: Format check & auto-fix (Python files only)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Check if files need formatting (only for .py files)
FORMAT_NEEDED=false
PYTHON_FILES=()

for file in "$@"; do
    if [[ "$file" == *.py ]]; then
        PYTHON_FILES+=("$file")
        if python -m ruff format --check "$file" >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $file - already formatted"
        else
            echo -e "${YELLOW}⚠${NC} $file - needs formatting"
            FORMAT_NEEDED=true
        fi
    else
        echo -e "${BLUE}⊘${NC} $file - skipped (not a Python file)"
    fi
done

# Auto-format if needed
if [ "$FORMAT_NEEDED" = true ] && [ ${#PYTHON_FILES[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}🔧 Auto-formatting Python files...${NC}"
    python -m ruff format "${PYTHON_FILES[@]}"
    echo -e "${GREEN}✓ Formatting complete${NC}"
elif [ ${#PYTHON_FILES[@]} -eq 0 ]; then
    echo -e "${BLUE}No Python files to format${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📝 Step 2: Adding files to staging area${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Add files to staging
git add "$@"

# Get list of staged files for display
STAGED_FILES=$(git diff --cached --name-only "$@" 2>/dev/null || echo "")
if [ -n "$STAGED_FILES" ]; then
    echo -e "${GREEN}✓ Staged files:${NC}"
    echo "$STAGED_FILES" | sed 's/^/  • /'
else
    echo -e "${YELLOW}⚠ No changes to stage (files may be unchanged)${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🔍 Step 3: Running code quality checks${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Run pre-commit checks on staged files
# Note: ruff-format is now in --check mode, so it won't modify files
if pre-commit run --files "$@"; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ All checks passed! Ready to commit.${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "   ${GREEN}git commit -m \"your message\"${NC}"
    exit 0
else
    # Check if any files were modified by hooks (e.g., ruff --fix)
    MODIFIED_FILES=$(git diff --name-only "$@" 2>/dev/null || echo "")

    if [ -n "$MODIFIED_FILES" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Some hooks auto-fixed the files (e.g., import sorting)${NC}"
        echo -e "${GREEN}Modified files:${NC}"
        echo "$MODIFIED_FILES" | sed 's/^/  • /'

        # Re-add the modified files
        git add "$@"

        echo ""
        echo -e "${YELLOW}🔄 Running checks again on fixed files...${NC}"

        # Run checks again (final attempt)
        if pre-commit run --files "$@"; then
            echo ""
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${GREEN}✅ All checks passed after auto-fix! Ready to commit.${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${YELLOW}Next steps:${NC}"
            echo -e "   ${GREEN}git commit -m \"your message\"${NC}"
            exit 0
        else
            # Still failing - likely a real error that needs manual fix
            echo ""
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${RED}❌ Checks still failing after auto-fix${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${YELLOW}This indicates a real issue that needs manual fixing:${NC}"
            echo -e "  • Check the error messages above"
            echo -e "  • Fix the issues in your code"
            echo -e "  • Run this script again: ${GREEN}$0 $FILES${NC}"
            exit 1
        fi
    else
        # No files were modified by hooks - real errors exist
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
        echo -e "${RED}❌ Checks failed! Manual fixes required.${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}Common issues:${NC}"
        echo -e "  • Mypy type errors"
        echo -e "  • Bandit security warnings"
        echo -e "  • Code style violations"
        echo ""
        echo -e "${YELLOW}After fixing the issues:${NC}"
        echo -e "  • Run: ${GREEN}$0 $FILES${NC}"
        echo ""
        echo -e "${YELLOW}To unstage and start over:${NC}"
        echo -e "  • Run: ${BLUE}git reset HEAD $FILES${NC}"
        exit 1
    fi
fi
