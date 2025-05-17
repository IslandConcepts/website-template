# Modular Homepage Template Documentation

This document explains how to configure and customize the modular homepage template for your website.

## Overview

The homepage template is designed to be highly customizable while maintaining a consistent structure:
- Three banner sections with video/image support
- Text sections between banners
- Customizable headings and content
- Mobile-responsive design

## Basic Configuration

The template pulls content from your site's configuration. Add these parameters to your `config.toml` file:

```toml
[params]
  # Banner videos - set the paths to your video files
  videos = { 
    banner1 = "/videos/your-first-video.mp4", 
    banner2 = "/videos/your-second-video.mp4", 
    banner3 = "/videos/your-third-video.mp4" 
  }
  
  # Fallback images (used when videos don't load or on mobile)
  images = { 
    banner1 = "/images/banner1-fallback.jpg", 
    banner2 = "/images/banner2-fallback.jpg", 
    banner3 = "/images/banner3-fallback.jpg" 
  }
  
  # Banner headings
  bannerTagline = "Your custom tagline goes here"
  banner2Heading = "SECONDARY HEADLINE"
  banner3Heading = "CALL TO ACTION"
  
  # Text content sections
  intro = "This is your site's introduction paragraph. Customize this text to describe your site's mission and purpose."
  
  midContent = "This is your site's middle content section. Use this area to expand on your site's purpose, highlight key content areas, or explain what makes your site unique."
  
  conclusion = "This is your site's conclusion paragraph. Use this to summarize your site's value proposition, invite users to explore further, or provide a final compelling message."
  
  # Disclaimer text (supports HTML)
  disclaimer = "Disclaimer: Customize this disclaimer text as needed. You can <a href='/about/' class='fiction-link'>link to your about page</a> or include any other necessary legal or contextual information."
```

## Media Requirements

### Videos

- **Format**: MP4 is recommended for maximum compatibility
- **Resolution**: 1920x1080 or 1280x720 recommended
- **Duration**: 10-30 seconds looping videos work best
- **File Size**: Keep files under 5MB if possible for faster loading
- **Hosting**: Videos can be hosted on your own server or a CDN
- **Storage Location**: Place videos in your site's `static/videos/` directory

### Fallback Images

- **Format**: JPG or PNG
- **Resolution**: 1920x1080 or similar aspect ratio
- **File Size**: Keep files under 500KB if possible
- **Storage Location**: Place images in your site's `static/images/` directory

## Customization Options

### Direct Template Editing

You can also edit the template directly:

1. Copy the `_default/index.html` file to your site's `layouts/index.html` to override the default
2. Modify HTML, CSS, or text directly in the template

### CSS Customization

The template uses CSS classes that can be styled in your site's CSS files:

- `.splash-section` - Banner containers
- `.splash-image` - Video/image containers
- `.splash-overlay` - Text overlay containers
- `.text-block` - Text section containers
- `.disclaimer-white` - Disclaimer text styling

## Adding Content Blocks

To add more content blocks, copy and paste existing sections in the template:

```html
<!-- Additional Banner Section -->
<div class="splash-section">
  <div class="splash-image">
    <video autoplay muted loop class="splash-video">
      <source src="{{ .Site.Params.videos.banner4 }}" type="video/mp4">
    </video>
    <img src="{{ .Site.Params.images.banner4 }}" alt="Additional banner" class="splash-fallback">
  </div>
  <div class="splash-overlay">{{ .Site.Params.banner4Heading }}</div>
</div>

<!-- Additional Text Block -->
<section class="text-block">
  <p>
    {{ .Site.Params.additionalContent }}
  </p>
</section>
```

Then add the corresponding parameters to your site configuration.

## Mobile Considerations

The template is designed to be mobile-responsive:

- Videos are replaced with static images on mobile
- Text size adjusts for smaller screens
- Banner heights are reduced on mobile

Be sure to test your homepage on both desktop and mobile devices.

## Performance Tips

1. Optimize video files (compress them with tools like HandBrake)
2. Use WebM format in addition to MP4 for better compression
3. Lazy-load videos to improve page load time
4. Keep text content concise for better readability

## Example Configuration

Here's a complete example configuration:

```toml
[params]
  videos = { 
    banner1 = "/videos/cityscape.mp4", 
    banner2 = "/videos/nature-scene.mp4", 
    banner3 = "/videos/people-working.mp4" 
  }
  
  images = { 
    banner1 = "/images/cityscape.jpg", 
    banner2 = "/images/nature-scene.jpg", 
    banner3 = "/images/people-working.jpg" 
  }
  
  bannerTagline = "Delivering insights on technology, business, and culture"
  banner2Heading = "EXPERT ANALYSIS"
  banner3Heading = "JOIN OUR COMMUNITY"
  
  intro = "Welcome to our platform, where we explore the intersection of technology and society. Our team of researchers and journalists works tirelessly to bring you the most relevant and insightful content on the topics that matter most."
  
  midContent = "In a world of information overload, we believe in quality over quantity. Our carefully curated articles, investigations, and reports are designed to provide you with deeper understanding and actionable insights, not just headlines."
  
  conclusion = "Whether you're a tech enthusiast, industry professional, or curious mind, our content is crafted to inform, challenge, and inspire. Explore our latest articles, subscribe to our newsletter, or join the conversation in our community forums."
  
  disclaimer = "All content on this site is for informational purposes only. Our articles are thoroughly researched, but we recommend consulting with professionals before making important decisions based on our content. <a href='/about/' class='fiction-link'>Learn more about our editorial process</a>."
```