#!/bin/bash
# Project structure cleanup - Move files to proper locations

echo "🧹 F1 PROJECT - STRUCTURE CLEANUP"
echo "=================================="
echo ""

# Create proper directory structure
mkdir -p docs/history
mkdir -p scripts/training
mkdir -p scripts/utilities

echo "📁 Creating directory structure..."
echo "   ✓ docs/history/"
echo "   ✓ scripts/training/"
echo "   ✓ scripts/utilities/"
echo ""

# Move documentation to docs/history/
echo "📄 Moving documentation files..."
for file in *PHASE*.md *SESSION*.md *REVIEW*.md CODE_REVIEW*.md MODEL_VALIDATION*.md FINAL_SUMMARY*.md; do
    if [ -f "$file" ]; then
        mv "$file" docs/history/
        echo "   ✓ $file → docs/history/"
    fi
done
echo ""

# Move training scripts to scripts/training/
echo "🎓 Moving training scripts..."
for file in train_*.py; do
    if [ -f "$file" ]; then
        mv "$file" scripts/training/
        echo "   ✓ $file → scripts/training/"
    fi
done
echo ""

# Move utility scripts to scripts/utilities/
echo "🔧 Moving utility scripts..."
for file in check_*.py test_*.py cleanup_legacy.sh; do
    if [ -f "$file" ]; then
        mv "$file" scripts/utilities/
        echo "   ✓ $file → scripts/utilities/"
    fi
done
echo ""

echo "✅ Cleanup complete!"
echo ""
echo "📊 New structure:"
tree -L 2 docs/ scripts/ 2>/dev/null || ls -R docs/ scripts/
