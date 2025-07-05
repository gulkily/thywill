#!/bin/bash
# ThyWill Template Static Analysis Script
# Quick commands to find common template field issues

echo "🔍 ThyWill Template Field Analysis"
echo "=================================="

# Check for user.id references (should be user.display_name)
echo "1. Checking for incorrect user.id references..."
user_id_issues=$(rg "user.*\.id" --type html | grep -v "prayer\.id\|#.*id\|session\.id\|token\.id\|request\.id")
if [ -n "$user_id_issues" ]; then
    echo "❌ Found user.id references (should use user.display_name):"
    echo "$user_id_issues"
    echo
else
    echo "✅ No user.id issues found"
    echo
fi

# Check for author_id in Prayer contexts  
echo "2. Checking for author_id field usage..."
author_id_issues=$(rg "author_id" --type html)
if [ -n "$author_id_issues" ]; then
    echo "⚠️  Found author_id references (Prayer model uses author_username):"
    echo "$author_id_issues"
    echo
else
    echo "✅ No author_id issues found"
    echo
fi

# Check for inconsistent field patterns
echo "3. Checking for field consistency patterns..."
echo "User field patterns:"
rg "user.*\.(id|display_name)" --type html | head -10
echo

echo "Prayer field patterns:"
rg "prayer.*\.(id|author_username|author_id)" --type html | head -10
echo

echo "PrayerMark field patterns:"
rg "mark.*\.(id|username|user_id)" --type html | head -10
echo

# Check for template comparison issues
echo "4. Checking for field comparison issues..."
comparison_issues=$(rg "== .*\.id" --type html | grep -v "prayer\.id\|session\.id\|token\.id")
if [ -n "$comparison_issues" ]; then
    echo "⚠️  Found potential comparison issues:"
    echo "$comparison_issues"
    echo
else
    echo "✅ No obvious comparison issues found"
    echo
fi

# Check for href patterns
echo "5. Checking for user link patterns..."
user_links=$(rg 'href="/user/\{\{.*\}\}"' --type html)
if [ -n "$user_links" ]; then
    echo "User links found:"
    echo "$user_links"
    echo
else
    echo "✅ No user links found"
    echo
fi

# Summary
echo "📊 Summary:"
echo "- Run './validate_templates.py' for detailed validation"
echo "- Check that user links use display_name, not id"
echo "- Verify Prayer model uses author_username, not author_id"
echo "- Ensure PrayerMark model uses username, not user_id"
echo
echo "💡 Common fixes:"
echo "- user.id → user.display_name"
echo "- me.id → me.display_name"  
echo "- prayer.author_id → prayer.author_username"
echo "- mark.user_id → mark.username"