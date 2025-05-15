# Modular Website Template

This repository provides a highly modular template for quickly creating new websites using Hugo. It's designed to make it easy to spin up multiple websites while keeping the core functionality consistent.

## Key Features

- **XML-Based Configuration**: All content and settings stored in structured, easy-to-update XML files
- **Content Generation**: Automated content creation using OpenAI for articles and social media posts
- **Social Media Integration**: Built-in support for X/Twitter and Bluesky posting
- **SEO Optimization**: Comprehensive SEO settings and structured data
- **Analytics Support**: Easily configure Google Analytics, Tag Manager, AdSense, Facebook Pixel, and more
- **Mobile-Responsive Design**: Modern, responsive layouts that work on all devices

## How It Works

The template separates structure from content by using XML configuration files:

1. **Structure**: Layouts, templates, and scripts provide the framework
2. **Content**: All site-specific content lives in XML files for easy updates
3. **Generation**: Python scripts can generate new content using the configuration

## Getting Started

```bash
# Clone the template repository
git clone https://github.com/yourusername/website-template.git

# Run the setup script
cd website-template
chmod +x setup.sh
./setup.sh

# Follow the interactive prompts to configure your new site
```

## Directory Structure

```
website-template/
├── layouts/            # Hugo templates
│   ├── _default/       # Base templates
│   └── partials/       # Reusable template parts
├── assets/             # CSS & shared static assets
├── scripts/            # Content generation scripts
│   ├── config_loader.py  # XML configuration parser
│   └── generate_content.py  # Content generation tool
├── config/             # Configuration templates
│   ├── site.xml        # Core site settings
│   ├── navigation.xml  # Menu structure
│   ├── social.xml      # Social accounts & settings
│   ├── prompts/        # OpenAI prompt templates
│   └── keywords/       # Topic-specific keywords
└── setup.sh            # Setup script
```

## XML Configuration

All site-specific content is stored in XML files for easy updates:

### Site Configuration (site.xml)

```xml
<site>
  <info>
    <title>Your Site Title</title>
    <tagline>Your Tagline</tagline>
    <description>Site description...</description>
  </info>
  
  <analytics>
    <googleAnalyticsID>G-XXXXXXXXXX</googleAnalyticsID>
    <!-- Other analytics settings -->
  </analytics>
  
  <!-- Design, branding, content settings -->
</site>
```

### Navigation (navigation.xml)

```xml
<navigation>
  <menu type="main">
    <item>
      <title>Home</title>
      <url>/</url>
    </item>
    <!-- More menu items -->
  </menu>
</navigation>
```

### Content Generation

The template includes Python scripts for generating:

- News articles
- Blog posts
- Social media content

These scripts use OpenAI's API with prompt templates stored in XML files, making it easy to customize the content generation to your site's tone and style.

## Customization

1. **Design**: Modify CSS variables and template files
2. **Content**: Update XML files with your site's specific content
3. **Generation**: Customize the prompt templates to match your content style

## Deployment

Standard Hugo deployment options are supported:
- Netlify
- GitHub Pages
- AWS Amplify
- Manual deployment

## License

MIT