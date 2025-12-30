#!/bin/bash
# Cleanup script for legacy model files

echo "🗑️  F1 ML PROJECT - LEGACY CLEANUP"
echo "=================================="
echo ""

# Create backup directory
BACKUP_DIR="models/.archive_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup at: $BACKUP_DIR"
echo ""

# Move legacy model files (with timestamps in filename)
echo "🔍 Moving legacy model binaries..."
moved_count=0
for file in models/*_202*.pkl models/*_202*.joblib; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "   ✓ $(basename $file)"
        ((moved_count++))
    fi
done

# Move legacy JSON metadata files (with timestamps)
echo ""
echo "🔍 Moving legacy JSON metadata..."
for file in models/*_202*.json; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "   ✓ $(basename $file)"
        ((moved_count++))
    fi
done

echo ""
echo "📊 Summary:"
echo "   Files archived: $moved_count"
echo "   Location: $BACKUP_DIR"
echo ""
echo "✅ Current structure:"
ls -lh models/

echo ""
echo "💾 Backup size:"
du -sh "$BACKUP_DIR"

echo ""
echo "ℹ️  To permanently delete backup:"
echo "   rm -rf $BACKUP_DIR"
