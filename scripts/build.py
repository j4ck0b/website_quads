#!/usr/bin/env python3
import os
import re
import json

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATIONS_PATH = os.path.join(BASE_DIR, "js", "translations.js")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")
PRIVACY_PATH = os.path.join(BASE_DIR, "privacy.html")
TERMS_PATH = os.path.join(BASE_DIR, "terms.html")

def load_translations():
    """Parses js/translations.js into a Python dictionary."""
    with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Locate the translations object in the JS file
    # Format is: const translations = { ... };
    match = re.search(r"const\s+translations\s*=\s*(\{.*\});", content, re.DOTALL)
    if not match:
        raise ValueError("Could not find translations object in js/translations.js")
    
    js_obj = match.group(1)
    
    # We will clean the JS object to make it valid JSON
    # Remove trailing commas before closing braces/brackets
    js_obj = re.sub(r",\s*([\]}])", r"\1", js_obj)
    # Remove JS style comments
    js_obj = re.sub(r"//.*?\n", "", js_obj)
    
    # Keys in JS can be unquoted or single/double quoted. Let's convert them to double quotes.
    # Fortunately in our translations file, all keys and values are double-quoted.
    # Let's clean up key-value pairs so it parses cleanly.
    # Replace key definitions (e.g., en: { to "en": {)
    js_obj = re.sub(r"(^|\s+)([a-zA-Z0-9_]+)\s*:", r'\1"\2":', js_obj)
    
    try:
        data = json.loads(js_obj)
        return data
    except Exception as e:
        # Fallback manual parser line-by-line if json.loads fails
        print(f"JSON parsing failed ({e}), falling back to regex parser...")
        
        translations = {}
        current_lang = None
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Check for language starter: en: {, pl: {, es: {
            lang_match = re.match(r"^([a-z]{2})\s*:\s*\{", line)
            if lang_match:
                current_lang = lang_match.group(1)
                translations[current_lang] = {}
                continue
            
            # Check for end of lang block
            if line == "}," or line == "}":
                current_lang = None
                continue
            
            if current_lang:
                # Matches "key": "value" or "key": "value",
                pair_match = re.match(r'^"([^"]+)"\s*:\s*"(.*)"\s*,?$', line)
                if pair_match:
                    key = pair_match.group(1)
                    val = pair_match.group(2)
                    # Unescape quotes
                    val = val.replace('\\"', '"')
                    translations[current_lang][key] = val
                    
        return translations

def translate_html(html_content, lang, translations):
    """Replaces data-i18n and data-i18n-placeholder elements with translated text."""
    lang_dict = translations.get(lang, {})
    if not lang_dict:
        return html_content
    
    # Update <html lang="en"> to lang
    html_content = re.sub(r'<html\s+lang="[^"]+"', f'<html lang="{lang}"', html_content)
    
    # Translate regular tags with data-i18n="key"
    # Match: <tag ... data-i18n="key" ...>Original Text</tag>
    # We will use regex to find tags with data-i18n
    def repl_tag(match):
        full_tag = match.group(0)
        i18n_key_match = re.search(r'data-i18n="([^"]+)"', full_tag)
        if not i18n_key_match:
            return full_tag
        key = i18n_key_match.group(1)
        translated_text = lang_dict.get(key)
        if translated_text is None:
            return full_tag
            
        # Reconstruct the tag with the new inner content
        # Check if it has a closing tag matching the opening one
        tag_name_match = re.match(r'^<([a-zA-Z0-9\-]+)', full_tag)
        if not tag_name_match:
            return full_tag
        tag_name = tag_name_match.group(1)
        
        # Replace the inner text between opening tag and closing tag
        # e.g., <h2 data-i18n="key">...</h2>
        # We need to find where the opening tag ends (after >) and where the closing tag starts (before </tag_name>)
        opening_tag_end = full_tag.find('>') + 1
        closing_tag_start = full_tag.rfind(f'</{tag_name}>')
        
        if opening_tag_end > 0 and closing_tag_start > opening_tag_end:
            # Check if there are nested tags we shouldn't overwrite, but normally data-i18n is for text
            return full_tag[:opening_tag_end] + translated_text + full_tag[closing_tag_start:]
        
        return full_tag

    # Matches `<tag ... data-i18n="key" ...>...</tag>` across newlines
    # We use non-greedy matching for the tag body and contents
    pattern = r'<([a-zA-Z0-9\-]+)[^>]*?data-i18n="[^"]+"[^>]*?>.*?</\1>'
    html_content = re.sub(pattern, repl_tag, html_content, flags=re.DOTALL)
    
    # Translate self-closing or empty elements with data-i18n (e.g. inputs, strong)
    # Match: <tag ... data-i18n="key" ... /> or <tag ... data-i18n="key" ...>
    # Translate placeholders
    def repl_placeholder(match):
        full_tag = match.group(0)
        i18n_key_match = re.search(r'data-i18n-placeholder="([^"]+)"', full_tag)
        if not i18n_key_match:
            return full_tag
        key = i18n_key_match.group(1)
        translated_text = lang_dict.get(key)
        if translated_text is None:
            return full_tag
            
        # Replace placeholder="..." attribute or inject it
        if 'placeholder=' in full_tag:
            return re.sub(r'placeholder="[^"]+"', f'placeholder="{translated_text}"', full_tag)
        else:
            return full_tag.replace('data-i18n-placeholder=', f'placeholder="{translated_text}" data-i18n-placeholder=')

    html_content = re.sub(r'<[^>]*?data-i18n-placeholder="[^"]+"[^>]*?>', repl_placeholder, html_content)
    
    # Update Page Title
    if "seo.title" in lang_dict:
        html_content = re.sub(r'<title>.*?</title>', f'<title>{lang_dict["seo.title"]}</title>', html_content)
        
    # Update Meta Description
    if "seo.description" in lang_dict:
        html_content = re.sub(
            r'<meta\s+name="description"\s+content="[^"]+"',
            f'<meta name="description" content="{lang_dict["seo.description"]}"',
            html_content
        )
        # Update Open Graph / Twitter descriptions too
        html_content = re.sub(
            r'<meta\s+property="og:description"\s+content="[^"]+"',
            f'<meta property="og:description" content="{lang_dict["seo.description"]}"',
            html_content
        )
        html_content = re.sub(
            r'<meta\s+property="twitter:description"\s+content="[^"]+"',
            f'<meta property="twitter:description" content="{lang_dict["seo.description"]}"',
            html_content
        )

    # Update Open Graph Titles
    if "seo.title" in lang_dict:
        html_content = re.sub(
            r'<meta\s+property="og:title"\s+content="[^"]+"',
            f'<meta property="og:title" content="{lang_dict["seo.title"]}"',
            html_content
        )
        html_content = re.sub(
            r'<meta\s+property="twitter:title"\s+content="[^"]+"',
            f'<meta property="twitter:title" content="{lang_dict["seo.title"]}"',
            html_content
        )

    return html_content

def update_relative_paths(html_content, lang):
    """Prepends '../' to css, js, img, and multimedia paths for subdirectory HTML pages, and fixes language switch links."""
    # 1. Update css/ js/ multimedia/ img/ paths
    html_content = re.sub(r'(href|src)="((css|js|multimedia|img)/[^"]+)"', r'\1="../\2"', html_content)
    
    # 2. Update legal links (privacy.html -> ../privacy.html, terms.html -> ../terms.html)
    html_content = re.sub(r'href="(privacy\.html|terms\.html)"', r'href="../\1"', html_content)
    
    # 3. Update language switcher links
    # For a subdirectory like /pl/, the parent is ../
    # So:
    # - en: href="index.html" -> href="../index.html"
    # - pl: href="pl/index.html" -> href="index.html" (current folder)
    # - es: href="es/index.html" -> href="../es/index.html"
    if lang == "pl":
        html_content = html_content.replace('href="index.html"', 'href="../index.html"')
        html_content = html_content.replace('href="pl/index.html"', 'href="index.html"')
        html_content = html_content.replace('href="es/index.html"', 'href="../es/index.html"')
    elif lang == "es":
        html_content = html_content.replace('href="index.html"', 'href="../index.html"')
        html_content = html_content.replace('href="pl/index.html"', 'href="../pl/index.html"')
        html_content = html_content.replace('href="es/index.html"', 'href="index.html"')
        
    return html_content

def update_seo_metadata(html_content, lang):
    """Updates Canonical, hreflangs, and OG URLs for the specific language subdirectory."""
    lang_path = "" if lang == "en" else f"{lang}/"
    base_url = f"https://primequads.com/{lang_path}"
    
    # Canonical link
    html_content = re.sub(r'<link\s+rel="canonical"\s+href="[^"]+"', f'<link rel="canonical" href="{base_url}"', html_content)
    
    # OG URL
    html_content = re.sub(r'<meta\s+property="og:url"\s+content="[^"]+"', f'<meta property="og:url" content="{base_url}"', html_content)
    html_content = re.sub(r'<meta\s+property="twitter:url"\s+content="[^"]+"', f'<meta property="twitter:url" content="{base_url}"', html_content)
    
    # OG Locale
    locale_map = {"en": "en_US", "pl": "pl_PL", "es": "es_ES"}
    target_locale = locale_map.get(lang, "en_US")
    html_content = re.sub(r'<meta\s+property="og:locale"\s+content="[^"]+"', f'<meta property="og:locale" content="{target_locale}"', html_content)
    
    return html_content

def build_pages():
    translations = load_translations()
    print("Loaded languages:", list(translations.keys()))
    
    # Read core files
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_html = f.read()
    with open(PRIVACY_PATH, "r", encoding="utf-8") as f:
        privacy_html = f.read()
    with open(TERMS_PATH, "r", encoding="utf-8") as f:
        terms_html = f.read()
        
    for lang in ["en", "pl", "es"]:
        print(f"\nProcessing lang: {lang}...")
        
        # Statically translate content
        t_index = translate_html(index_html, lang, translations)
        t_privacy = translate_html(privacy_html, lang, translations)
        t_terms = translate_html(terms_html, lang, translations)
        
        # Update SEO URL canonicals and hreflangs
        t_index = update_seo_metadata(t_index, lang)
        t_privacy = update_seo_metadata(t_privacy, lang)
        t_terms = update_seo_metadata(t_terms, lang)
        
        if lang == "en":
            # English goes directly in the root directory
            with open(INDEX_PATH, "w", encoding="utf-8") as f:
                f.write(t_index)
            with open(PRIVACY_PATH, "w", encoding="utf-8") as f:
                f.write(t_privacy)
            with open(TERMS_PATH, "w", encoding="utf-8") as f:
                f.write(t_terms)
            print("Successfully updated root EN files.")
        else:
            # Polish and Spanish go into their respective subdirectories
            lang_dir = os.path.join(BASE_DIR, lang)
            os.makedirs(lang_dir, exist_ok=True)
            
            # Update paths to point to root directories (../../ or ../)
            t_index = update_relative_paths(t_index, lang)
            t_privacy = update_relative_paths(t_privacy, lang)
            t_terms = update_relative_paths(t_terms, lang)
            
            with open(os.path.join(lang_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(t_index)
            with open(os.path.join(lang_dir, "privacy.html"), "w", encoding="utf-8") as f:
                f.write(t_privacy)
            with open(os.path.join(lang_dir, "terms.html"), "w", encoding="utf-8") as f:
                f.write(t_terms)
            print(f"Successfully created files in /{lang}/ subdirectory.")

if __name__ == "__main__":
    build_pages()
    print("\nPre-rendering build complete!")
