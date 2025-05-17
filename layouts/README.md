# Modular Hugo Templates

This directory contains modular Hugo templates that can be easily adapted for different types of websites. These templates are designed to be configurable through your site's configuration file, making them adaptable without changing the template code.

## Features

- News ticker at the top of all list pages
- Multi-column layout for news section
- Alternating layout for editorial section
- Responsive design with mobile-specific headings
- Social sharing functionality
- Decorative elements between paragraphs
- Related content suggestions
- Tag support

## Directory Structure

```
layouts/
├── partials/
│   ├── news_ticker.html       # Scrolling ticker with recent content
│   ├── preview_tags.html      # Tags on content previews in list views
│   ├── article_tags.html      # Tags at the bottom of single article views
│   ├── social_share.html      # Social media sharing buttons
│   └── related_posts.html     # Related content at the bottom of articles
├── news/
│   ├── list.html              # Multi-column layout for news lists
│   └── single.html            # Single article view for news
└── editorial/
    ├── list.html              # Alternating layout for editorial lists
    └── single.html            # Single article view for editorial
```

## Implementation Guide

### Required CSS

For the modular templates to work correctly, include the template-modules.css file in your site's header:

```html
<link rel="stylesheet" href="/css/template-modules.css">
```

### Customizing Sections

You can rename these sections to match your specific site needs. For example:

- The "news" section could be renamed to "articles", "posts", "updates", etc.
- The "editorial" section could be renamed to "features", "opinion", "analysis", etc.

To do this, simply copy the templates to directories matching your section names.

### Configuration Options

These templates can be customized via your site's configuration file (`config.toml`):

#### News Ticker Settings

```toml
[params]
  # Sections to include in the ticker
  tickerSections = ["news", "editorial"]
  
  # Number of items to show in the ticker
  tickerItemCount = 8
  
  # Whether to use headline processor for titles
  useHeadlineProcessor = true
```

#### News Section Settings

```toml
[params]
  # Number of featured stories to show
  featuredCount = 3
  
  # Number of medium-sized previews to show
  mediumCount = 18
  
  # Whether to show the news ticker
  showNewsTicker = true
```

#### Editorial Section Settings

```toml
[params]
  # Title for the editorial section
  editorialTitle = "Analysis"
  
  # Section to pull related content from for editorial
  relatedEditorialSection = "editorial"
```

#### Decorative Icons Settings

```toml
[params]
  # Icons to use between paragraphs
  decorativeIcons = [
    "icon1.jpg",
    "icon2.jpg",
    "icon3.jpg"
  ]
  
  # Number of paragraphs between icons
  paragraphsBetweenIcons = 3
```

#### Tag Settings

```toml
[params]
  # Sections where tags should be shown in previews
  previewTagSections = ["news", "editorial"]
  
  # Number of tags to show in previews
  previewTagCount = 1
  
  # Sections where article tags should be shown
  articleTagSections = ["news", "editorial"]
```

#### Social Share Settings

```toml
[params]
  # Platforms to enable for sharing
  enabledSharePlatforms = ["twitter", "facebook", "bluesky", "email", "copy"]
```

#### Related Posts Settings

```toml
[params]
  # Number of related posts to show
  relatedPostsCount = 5
  
  # Title for the related posts section
  relatedPostsTitle = "More Articles"
  
  # Section to pull related content from for news
  relatedSection = "news"
```

## Required Images

The templates reference several types of images:

- Content featured images (specified in frontmatter)
- Author thumbnails (from site data)
- Decorative icons (configured in site params)
- Social sharing icons:
  - `/images/facebook_Logo.png`
  - `/images/bluesky-icon-black.png`

Make sure these images are available in your site's static directory.