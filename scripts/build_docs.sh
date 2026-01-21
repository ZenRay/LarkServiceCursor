#!/bin/bash
# Build Sphinx documentation

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
DOCS_DIR="$PROJECT_ROOT/docs"
BUILD_DIR="$DOCS_DIR/_build"

echo "📚 Building Lark Service Documentation..."

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

# Generate API documentation
echo "📋 Generating API documentation..."
cd "$PROJECT_ROOT"
sphinx-apidoc -f -o "$DOCS_DIR/api" src/lark_service --separate --module-first

# Build HTML documentation
echo "🏗️  Building HTML documentation..."
cd "$DOCS_DIR"
sphinx-build -b html . "$BUILD_DIR/html" --keep-going

# Check for warnings
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Documentation built successfully!"
    echo "📂 Location: $BUILD_DIR/html/index.html"
    echo ""
    echo "To view the documentation:"
    echo "  cd $BUILD_DIR/html && python -m http.server 8080"
    echo "  Then open: http://localhost:8080"
else
    echo ""
    echo "❌ Documentation build failed!"
    exit 1
fi
