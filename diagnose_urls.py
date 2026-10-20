"""
Diagnostic script to check for URL issues that might cause 300 (Multiple Choices) errors
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

def check_url_patterns():
    """Check for duplicate or problematic URL patterns"""
    resolver = get_resolver()
    
    patterns = []
    duplicates = {}
    
    def extract_patterns(url_patterns, prefix=''):
        for pattern in url_patterns:
            if isinstance(pattern, URLResolver):
                extract_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
            elif isinstance(pattern, URLPattern):
                full_pattern = prefix + str(pattern.pattern)
                patterns.append({
                    'pattern': full_pattern,
                    'name': pattern.name,
                    'view': pattern.callback.__name__ if hasattr(pattern.callback, '__name__') else str(pattern.callback)
                })
                
                # Check for duplicates
                if full_pattern in duplicates:
                    duplicates[full_pattern].append(pattern.name)
                else:
                    duplicates[full_pattern] = [pattern.name]
    
    extract_patterns(resolver.url_patterns)
    
    print("=" * 80)
    print("URL PATTERN DIAGNOSTIC REPORT")
    print("=" * 80)
    print()
    
    # Check for duplicates
    print("1. CHECKING FOR DUPLICATE URL PATTERNS:")
    print("-" * 80)
    has_duplicates = False
    for pattern, names in duplicates.items():
        if len(names) > 1:
            has_duplicates = True
            print(f"⚠️  DUPLICATE: {pattern}")
            for name in names:
                print(f"   → {name}")
            print()
    
    if not has_duplicates:
        print("✅ No duplicate URL patterns found")
    print()
    
    # Check for trailing slash issues
    print("2. CHECKING FOR TRAILING SLASH ISSUES:")
    print("-" * 80)
    slash_issues = []
    patterns_dict = {}
    
    for p in patterns:
        pattern_str = p['pattern']
        # Remove trailing $ if present
        clean_pattern = pattern_str.rstrip('^$')
        
        # Check if both /path/ and /path exist
        if clean_pattern.endswith('/'):
            no_slash = clean_pattern.rstrip('/')
            if no_slash in patterns_dict:
                slash_issues.append((no_slash, clean_pattern))
        
        patterns_dict[clean_pattern] = p
    
    if slash_issues:
        for no_slash, with_slash in slash_issues:
            print(f"⚠️  POTENTIAL ISSUE:")
            print(f"   Without slash: {no_slash}")
            print(f"   With slash: {with_slash}")
            print()
    else:
        print("✅ No trailing slash conflicts found")
    print()
    
    # List all URL patterns
    print("3. ALL URL PATTERNS:")
    print("-" * 80)
    for p in sorted(patterns, key=lambda x: x['pattern']):
        name = p['name'] if p['name'] else '(unnamed)'
        print(f"Pattern: {p['pattern']:<50} Name: {name:<30}")
    
    print()
    print("=" * 80)
    print(f"Total URL patterns: {len(patterns)}")
    print("=" * 80)

if __name__ == '__main__':
    check_url_patterns()
