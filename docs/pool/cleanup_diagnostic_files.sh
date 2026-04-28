#!/bin/bash
# Cleanup Trade History Diagnostic Files
# Run this after the trade history issue has been resolved
# Usage: bash cleanup_diagnostic_files.sh

echo "🧹 Cleaning up trade history diagnostic files..."

# Files to remove (diagnostic only, not needed after fixing)
DIAGNOSTIC_FILES=(
  "docs/pool/TRADE_HISTORY_DIAGNOSTIC.md"
  "docs/pool/DIAGNOSTIC_ENHANCEMENTS.md"
  "docs/pool/NEXT_STEPS.md"
  "docs/pool/DEPLOYMENT_CHECKLIST.md"
)

REMOVED=0
NOT_FOUND=0

for file in "${DIAGNOSTIC_FILES[@]}"; do
  if [ -f "$file" ]; then
    rm "$file"
    echo "✅ Removed: $file"
    REMOVED=$((REMOVED + 1))
  else
    echo "⏭️  Not found: $file (already deleted?)"
    NOT_FOUND=$((NOT_FOUND + 1))
  fi
done

echo ""
echo "📊 Summary:"
echo "  Removed: $REMOVED files"
echo "  Not found: $NOT_FOUND files"
echo ""
echo "✨ Cleanup complete!"
echo ""
echo "📝 NOTE: Keep these files if you still need them for reference"
echo "    - TRADES_SETUP.md (implementation guide)"
echo "    - TRADES_SCHEMA.sql (database schema)"

