# Template Modules Documentation

This document explains how to use the modular templates included in the website-template repository. These templates provide a flexible, configurable system for creating different types of websites with consistent styling and functionality.

## Available Templates

The modular template system includes:

1. **News Section**: A multi-column layout ideal for news sites or blogs with high content volume
2. **Editorial Section**: An alternating layout for long-form content, opinion pieces, or features
3. **Shared Components**: News ticker, social sharing, related posts, and tag systems

## Implementation Steps

### 1. Include Required CSS

Add the template-modules.css file to your site's header:

```html
<link rel="stylesheet" href="/css/template-modules.css">
```

Make sure you have CSS variables defined for your site:

```css
:root {
  --primary-color: #0f0f0f;
  --secondary-color: #404040;
  --accent-color: #ff4a4a;
  --text-color: #e5e5e5;
  --background-color: #1a1a1a;
  --font-heading: 'Anton', sans-serif;
  --font-body: 'Roboto', sans-serif;
}
```

### 2. Set Up Content Sections

Create the appropriate section directories in your content folder:

```
content/
├── news/           # For news-style content
│   └── _index.md   # Section front matter
└── editorial/      # For editorial-style content
    └── _index.md   # Section front matter
```

Example front matter for `content/news/_index.md`:

```yaml
---
title: "News & Updates"
description: "The latest news and updates"
---
```

### 3. Configure Site Parameters

Add the following configuration options to your site's config.toml:

```toml
[params]
  # News Ticker Settings
  tickerSections = ["news", "editorial"]
  tickerItemCount = 8
  
  # News Section Settings
  featuredCount = 3
  mediumCount = 18
  showNewsTicker = true
  
  # Editorial Section Settings
  editorialTitle = "Analysis & Insight"
  
  # Decorative Icons Settings
  decorativeIcons = [
    "icon1.jpg",
    "icon2.jpg",
    "icon3.jpg"
  ]
  paragraphsBetweenIcons = 3
  
  # Tag Settings
  previewTagSections = ["news", "editorial"]
  previewTagCount = 1
  articleTagSections = ["news", "editorial"]
  
  # Social Share Settings
  enabledSharePlatforms = ["twitter", "facebook", "bluesky", "email", "copy"]
  
  # Related Posts Settings
  relatedPostsCount = 5
  relatedPostsTitle = "More Articles"
  relatedSection = "news"
  relatedEditorialSection = "editorial"
```

### 4. Prepare Required Images

1. **Decorative Icons**: Place your decorative icon images in `/static/images/`
2. **Social Sharing Icons**: Add these standard icons to `/static/images/`:
   - `facebook_Logo.png`
   - `bluesky-icon-black.png`

### 5. Content Front Matter

For content to display correctly, use the following front matter for your pages:

```yaml
---
title: "Article Title"
date: 2023-01-01T12:00:00-05:00
lastmod: 2023-01-02T15:30:00-05:00
author: "Author Name"
image: "/images/article-featured-image.jpg"
image_credit: "Photographer Name"
summary: "A short summary of the article."
tags: ["tag1", "tag2"]
---
```

### 6. Set Up Author Data

For author thumbnail display, create a `data/authors.yaml` file:

```yaml
authors:
  - name: "Author Name"
    thumbnail: "/images/authors/author-thumbnail.jpg"
    bio: "Short author bio."
  - name: "Another Author"
    thumbnail: "/images/authors/another-author.jpg"
    bio: "Short author bio."
```

## Customizing For Different Sites

### Renaming Sections

You can change the section names by copying the templates to directories matching your preferred names:

1. Copy `/layouts/news/` to `/layouts/your-section-name/`
2. Copy `/layouts/editorial/` to `/layouts/your-other-section/`
3. Update configuration to reference your new section names

### Changing the Appearance

You can customize the appearance by:

1. **Modifying CSS**: Override specific styles in your site's stylesheet
2. **Changing Icons**: Use different decorative icons in your site parameters
3. **Adjusting Layout**: Modify the number of featured items, medium items, etc.

### Multi-Site Support

For multi-site setups:

1. Create separate config files for each site (`config.site1.toml`, `config.site2.toml`, etc.)
2. Define site-specific parameters in each config file
3. Use the same shared templates for all sites

## Troubleshooting

### CSS Issues

If styling doesn't appear correctly:

1. Verify that `template-modules.css` is correctly linked in your header
2. Check that CSS variables are defined in your site's stylesheet
3. Inspect elements with browser developer tools to identify styling issues

### Template Errors

If templates aren't rendering correctly:

1. Check Hugo console for error messages
2. Verify that all partials are correctly referenced in templates
3. Ensure all required directories exist in your site structure

### Missing Images

If images aren't displaying:

1. Verify that image paths are correct in your content front matter
2. Check that required social icons exist in the correct directory
3. Ensure decorative icons are available at the paths specified in your configuration