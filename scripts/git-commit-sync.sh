#!/bin/bash
# Git commit with auto-sync staging area
# This script ensures that staged files are re-added before commit
# to prevent working directory and staging area mismatches

set -e

# Colors
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 Syncing staging area with working directory...${NC}"

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${YELLOW}⚠ No files in staging area${NC}"
    echo -e "${YELLOW}Usage: git csync (or git commit directly)${NC}"
    exit 1
fi

# Re-add all staged files to ensure they're up-to-date
echo -e "${BLUE}Re-adding staged files:${NC}"
echo "$STAGED_FILES" | sed 's/^/  • /'

# Convert newlines to spaces for xargs
echo "$STAGED_FILES" | xargs git add

echo -e "${GREEN}✓ Staging area synced${NC}"
echo ""
echo -e "${BLUE}Now running git commit with your arguments...${NC}"
echo ""

# Run git commit with all provided arguments
git commit "$@"
