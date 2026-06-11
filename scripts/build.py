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

def translate_html(html_content, lang, translations, filename="index.html"):
    """Replaces data-i18n, data-i18n-placeholder and data-i18n-alt elements with translated text."""
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
        
        if opening_tag_end > 0 and closing_tag_start >= opening_tag_end:
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

    # Translate image alt tags with data-i18n-alt="key"
    def repl_alt(match):
        full_tag = match.group(0)
        i18n_key_match = re.search(r'data-i18n-alt="([^"]+)"', full_tag)
        if not i18n_key_match:
            return full_tag
        key = i18n_key_match.group(1)
        translated_text = lang_dict.get(key)
        if translated_text is None:
            return full_tag
        
        # Replace the alt="..." attribute or inject it
        if re.search(r'(?<!data-i18n-)alt="[^"]+"', full_tag):
            return re.sub(r'(?<!data-i18n-)alt="[^"]+"', f'alt="{translated_text}"', full_tag)
        else:
            return full_tag.replace('data-i18n-alt=', f'alt="{translated_text}" data-i18n-alt=')

    html_content = re.sub(r'<img[^>]*?data-i18n-alt="[^"]+"[^>]*?>', repl_alt, html_content)
    
    # Update Page Title
    if f"seo.title.{filename}" in lang_dict:
        html_content = re.sub(r'<title>.*?</title>', f'<title>{lang_dict[f"seo.title.{filename}"]}</title>', html_content)
    elif "seo.title" in lang_dict:
        html_content = re.sub(r'<title>.*?</title>', f'<title>{lang_dict["seo.title"]}</title>', html_content)
        
    # Update Meta Description
    target_desc_key = f"seo.description.{filename}" if f"seo.description.{filename}" in lang_dict else "seo.description"
    if target_desc_key in lang_dict:
        html_content = re.sub(
            r'<meta\s+name="description"\s+content="[^"]+"',
            f'<meta name="description" content="{lang_dict[target_desc_key]}"',
            html_content
        )
        # Update Open Graph / Twitter descriptions too
        html_content = re.sub(
            r'<meta\s+property="og:description"\s+content="[^"]+"',
            f'<meta property="og:description" content="{lang_dict[target_desc_key]}"',
            html_content
        )
        html_content = re.sub(
            r'<meta\s+property="twitter:description"\s+content="[^"]+"',
            f'<meta property="twitter:description" content="{lang_dict[target_desc_key]}"',
            html_content
        )

    # Update Open Graph Titles
    target_title_key = f"seo.title.{filename}" if f"seo.title.{filename}" in lang_dict else "seo.title"
    if target_title_key in lang_dict:
        html_content = re.sub(
            r'<meta\s+property="og:title"\s+content="[^"]+"',
            f'<meta property="og:title" content="{lang_dict[target_title_key]}"',
            html_content
        )
        html_content = re.sub(
            r'<meta\s+property="twitter:title"\s+content="[^"]+"',
            f'<meta property="twitter:title" content="{lang_dict[target_title_key]}"',
            html_content
        )

    # Pre-render FAQPage JSON-LD schema dynamically
    if filename == "index.html" and "faq.q1" in lang_dict:
        main_entity = []
        i = 1
        while f"faq.q{i}" in lang_dict:
            main_entity.append({
                "@type": "Question",
                "name": lang_dict.get(f"faq.q{i}", ""),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": lang_dict.get(f"faq.a{i}", "")
                }
            })
            i += 1
            
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": main_entity
        }
        faq_schema_str = json.dumps(faq_schema, ensure_ascii=False, indent=2)
        faq_script = f'<script id="faq-schema" type="application/ld+json">\n{faq_schema_str}\n</script>'
        html_content = re.sub(r'<script\s+id="faq-schema"\s+type="application/ld\+json"\s*>.*?</script>', faq_script, html_content, flags=re.DOTALL)

    # Pre-render LocalBusiness / TouristAttraction schema for Polish
    if filename == "index.html" and lang == "pl":
        pl_business_schema = {
            "@context": "https://schema.org",
            "@type": "TouristAttraction",
            "name": "Prime Quads Tenerife",
            "description": "Wycieczki na quadach na Teneryfie do Parku Narodowego Teide. Quady 550cc XL, kameralne grupy do 5 quadów, trasy powyżej 2000 m n.p.m. Wyjazdy popołudniowe i o zachodzie słońca z Las Américas.",
            "url": "https://primequads.com/pl/",
            "telephone": "+34711075369",
            "priceRange": "€120–€140",
            "currenciesAccepted": "EUR",
            "openingHours": "Mo-Su 09:00-20:00",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "Las Américas",
                "addressLocality": "Adeje",
                "addressRegion": "Tenerife",
                "addressCountry": "ES"
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": "28.0565",
                "longitude": "-16.7232"
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "4.9",
                "reviewCount": "480",
                "bestRating": "5",
                "worstRating": "1"
            },
            "hasOfferCatalog": {
                "@type": "OfferCatalog",
                "name": "Wycieczki na quadach",
                "itemListElement": [
                    {
                        "@type": "Offer",
                        "name": "Quad jednoosobowy – wycieczka na Teide",
                        "price": "120",
                        "priceCurrency": "EUR",
                        "description": "3,5-godzinna wyprawa quadem 550cc XL z Las Américas do Parku Narodowego Teide.",
                        "availability": "https://schema.org/InStock"
                    },
                    {
                        "@type": "Offer",
                        "name": "Quad dwuosobowy – wycieczka na Teide",
                        "price": "140",
                        "priceCurrency": "EUR",
                        "description": "3,5-godzinna wyprawa quadem dwuosobowym 550cc XL z Las Américas do Parku Narodowego Teide.",
                        "availability": "https://schema.org/InStock"
                    }
                ]
            },
            "tourBookingPage": "https://primequads.com/pl/#booking",
            "inLanguage": ["pl", "en", "es", "de", "it", "pt"],
            "sameAs": [
                "https://www.tripadvisor.com/",
                "https://www.google.com/maps/place/Extreme+Prime+Tours+SL"
            ]
        }
        pl_schema_str = json.dumps(pl_business_schema, ensure_ascii=False, indent=2)
        business_script = f'<script id="local-business-schema" type="application/ld+json">\n{pl_schema_str}\n</script>'
        html_content = re.sub(
            r'<script\s+id="local-business-schema"\s+type="application/ld\+json"\s*>.*?</script>',
            business_script,
            html_content,
            flags=re.DOTALL
        )

    # Pre-render BreadcrumbList JSON-LD schema dynamically
    if filename == "guides.html":
        breadcrumb_names = {
            "en": ("Home", "Guides"),
            "pl": ("Strona główna", "Poradniki"),
            "es": ("Inicio", "Guías")
        }
        name_home, name_guides = breadcrumb_names.get(lang, ("Home", "Guides"))
        
        lang_path = "" if lang == "en" else f"{lang}/"
        home_url = f"https://primequads.com/{lang_path}"
        guides_url = f"https://primequads.com/{lang_path}guides.html"
        
        breadcrumb_schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": name_home,
                    "item": home_url
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": name_guides,
                    "item": guides_url
                }
            ]
        }
        breadcrumb_str = json.dumps(breadcrumb_schema, ensure_ascii=False, indent=2)
        breadcrumb_script = f'<script id="breadcrumb-schema" type="application/ld+json">\n{breadcrumb_str}\n</script>'
        html_content = re.sub(
            r'<script\s+id="breadcrumb-schema"\s+type="application/ld\+json"\s*>.*?</script>',
            breadcrumb_script,
            html_content,
            flags=re.DOTALL
        )

    return html_content

def update_relative_paths(html_content, lang):
    """Prepends '../' to css, js, img, and multimedia paths for subdirectory HTML pages."""
    # 1. Update css/ js/ multimedia/ img/ paths
    html_content = re.sub(r'(href|src)="((css|js|multimedia|img)/[^"]+)"', r'\1="../\2"', html_content)
    # Update favicon paths
    html_content = re.sub(r'(href)="(favicon\.(ico|png))"', r'\1="../\2"', html_content)
    
    # 2. Fix the blog post URL path for subdirectories
    if lang == "pl":
        html_content = html_content.replace('href="pl/quady-na-teneryfie-przewodnik/index.html"', 'href="quady-na-teneryfie-przewodnik/index.html"')
    elif lang == "es":
        html_content = html_content.replace('href="pl/quady-na-teneryfie-przewodnik/index.html"', 'href="../pl/quady-na-teneryfie-przewodnik/index.html"')
        
    return html_content

def update_language_switcher(html_content, current_lang, filename):
    """Specifically updates class="lang-dropdown-item" links so they point to correct relative directories without affecting navigation links."""
    def repl(match):
        attrs = match.group(1)
        lang_match = re.search(r'data-lang="([^"]+)"', attrs)
        href_match = re.search(r'href="([^"]+)"', attrs)
        if not lang_match or not href_match:
            return match.group(0)
            
        target_lang = lang_match.group(1)
        
        # Determine target href
        if current_lang == "en":
            # We are in the root directory.
            # - en: href="filename"
            # - pl: href="pl/filename"
            # - es: href="es/filename"
            if target_lang == "en":
                new_href = filename
            else:
                new_href = f"{target_lang}/{filename}"
        elif current_lang == target_lang:
            # We are in the subdirectory, pointing to the same language page.
            # e.g. current_lang="pl", target_lang="pl" -> href="filename"
            new_href = filename
        else:
            # We are in a subdirectory, pointing to another language.
            # e.g. current_lang="pl", target_lang="en" -> href="../filename"
            # e.g. current_lang="pl", target_lang="es" -> href="../es/filename"
            if target_lang == "en":
                new_href = f"../{filename}"
            else:
                new_href = f"../{target_lang}/{filename}"
                
        # Reconstruct the tag
        new_attrs = re.sub(r'href="[^"]+"', f'href="{new_href}"', attrs)
        return f'<a {new_attrs}>'
        
    pattern = r'<a\s+([^>]*?class="lang-dropdown-item"[^>]*?)>'
    return re.sub(pattern, repl, html_content)

def update_seo_metadata(html_content, lang, filename="index.html"):
    """Updates Canonical, hreflangs, and OG URLs for the specific language subdirectory and filename."""
    lang_path = "" if lang == "en" else f"{lang}/"
    page_path = "" if filename == "index.html" else filename
    base_url = f"https://primequads.com/{lang_path}{page_path}"
    
    # Canonical link
    if re.search(r'<link\s+rel="canonical"\s+href="[^"]+"', html_content):
        html_content = re.sub(r'<link\s+rel="canonical"\s+href="[^"]+"', f'<link rel="canonical" href="{base_url}"', html_content)
    else:
        # insert before </head>
        html_content = html_content.replace('</head>', f'    <link rel="canonical" href="{base_url}">\n</head>')
    
    # Generate matching alternate hreflang tags for this page
    en_url = f"https://primequads.com/{page_path}"
    pl_url = f"https://primequads.com/pl/{page_path}"
    es_url = f"https://primequads.com/es/{page_path}"
    
    hreflangs_html = f"""    <!-- Multilingual Alternate SEO Links -->
    <link rel="alternate" hreflang="en" href="{en_url}">
    <link rel="alternate" hreflang="pl" href="{pl_url}">
    <link rel="alternate" hreflang="es" href="{es_url}">
    <link rel="alternate" hreflang="x-default" href="{en_url}">"""
    
    # Check if there is already an alternate links block or alternate tags
    if '<!-- Multilingual Alternate SEO Links -->' in html_content:
        pattern = r'<!-- Multilingual Alternate SEO Links -->.*?<link rel="alternate"[^>]+>.*?<link rel="alternate"[^>]+>.*?<link rel="alternate"[^>]+>.*?<link rel="alternate"[^>]+>'
        html_content = re.sub(pattern, hreflangs_html, html_content, flags=re.DOTALL)
    elif '<link rel="alternate"' in html_content:
        # remove old ones first, then insert new one
        html_content = re.sub(r'<link\s+rel="alternate"\s+hreflang="[^"]+"\s+href="[^"]+"\s*/?>\s*', '', html_content)
        html_content = html_content.replace('</head>', f'{hreflangs_html}\n</head>')
    else:
        html_content = html_content.replace('</head>', f'{hreflangs_html}\n</head>')
    
    # OG URL
    if 'property="og:url"' in html_content:
        html_content = re.sub(r'<meta\s+property="og:url"\s+content="[^"]+"', f'<meta property="og:url" content="{base_url}"', html_content)
    else:
        html_content = html_content.replace('</head>', f'    <meta property="og:url" content="{base_url}">\n</head>')
        
    if 'property="twitter:url"' in html_content:
        html_content = re.sub(r'<meta\s+property="twitter:url"\s+content="[^"]+"', f'<meta property="twitter:url" content="{base_url}"', html_content)
    else:
        html_content = html_content.replace('</head>', f'    <meta property="twitter:url" content="{base_url}">\n</head>')
    
    # OG Locale
    locale_map = {"en": "en_US", "pl": "pl_PL", "es": "es_ES"}
    target_locale = locale_map.get(lang, "en_US")
    if 'property="og:locale"' in html_content:
        html_content = re.sub(r'<meta\s+property="og:locale"\s+content="[^"]+"', f'<meta property="og:locale" content="{target_locale}"', html_content)
    else:
        html_content = html_content.replace('</head>', f'    <meta property="og:locale" content="{target_locale}">\n</head>')
    
    return html_content

def build_pages():
    translations = load_translations()
    print("Loaded languages:", list(translations.keys()))
    
    # Define file mappings
    templates = {
        "index.html": INDEX_PATH,
        "privacy.html": PRIVACY_PATH,
        "terms.html": TERMS_PATH
    }
    
    # Check if guides.html exists in root and include it if it does
    GUIDES_PATH = os.path.join(BASE_DIR, "guides.html")
    if os.path.exists(GUIDES_PATH):
        templates["guides.html"] = GUIDES_PATH
        print("Including guides.html in build templates.")
    else:
        print("guides.html template not found yet, will skip until it's created.")

    # Check if success.html and cancel.html exist
    SUCCESS_PATH = os.path.join(BASE_DIR, "success.html")
    if os.path.exists(SUCCESS_PATH):
        templates["success.html"] = SUCCESS_PATH
        print("Including success.html in build templates.")
    CANCEL_PATH = os.path.join(BASE_DIR, "cancel.html")
    if os.path.exists(CANCEL_PATH):
        templates["cancel.html"] = CANCEL_PATH
        print("Including cancel.html in build templates.")
        
    for lang in ["en", "pl", "es"]:
        print(f"\nProcessing lang: {lang}...")
        
        for name, path in templates.items():
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Statically translate content
            translated = translate_html(content, lang, translations, filename=name)
            
            # Update SEO URL canonicals and hreflangs
            translated = update_seo_metadata(translated, lang, filename=name)
            
            # Pre-render default expanded FAQ items for Polish index.html
            if lang == "pl" and name == "index.html":
                translated = translated.replace('class="faq-item"', 'class="faq-item active"')
                translated = translated.replace('class="faq-icon" style="color: var(--primary); font-size: 1.25rem; transition: transform 0.3s ease;">+', 'class="faq-icon" style="color: var(--primary); font-size: 1.25rem; transition: transform 0.3s ease;">−')
                translated = translated.replace('class="faq-panel" style="max-height: 0;', 'class="faq-panel" style="max-height: none;')
            
            if lang == "en":
                # English goes directly in the root directory
                translated = update_language_switcher(translated, lang, filename=name)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(translated)
                print(f"Successfully updated root EN file: {name}")
            else:
                # Polish and Spanish go into their respective subdirectories
                lang_dir = os.path.join(BASE_DIR, lang)
                os.makedirs(lang_dir, exist_ok=True)
                
                # Update paths to point to root directories
                translated = update_relative_paths(translated, lang)
                # Update language switcher dropdown links specifically
                translated = update_language_switcher(translated, lang, filename=name)
                
                dest_path = os.path.join(lang_dir, name)
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(translated)
                print(f"Successfully created /{lang}/{name}")

if __name__ == "__main__":
    build_pages()
    print("\nPre-rendering build complete!")
