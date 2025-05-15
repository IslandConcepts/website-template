#!/bin/bash
# Website Template Setup Script
#
# This script helps you set up a new website using the template.
# It will:
# 1. Ask for basic site information
# 2. Generate config files with your settings
# 3. Set up the directory structure

set -e

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}=================================${NC}"
echo -e "${GREEN}    Website Template Setup    ${NC}"
echo -e "${BLUE}=================================${NC}"
echo

# Find the template root directory (where this script is located)
TEMPLATE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo -e "${BLUE}Template directory: ${TEMPLATE_DIR}${NC}"

# Ask for the new site directory
echo
echo -e "${YELLOW}Where would you like to create your new website?${NC}"
read -p "Directory path: " SITE_DIR

# Check if directory exists
if [ -d "$SITE_DIR" ]; then
    echo -e "${RED}Directory already exists. Please choose a different location or delete the existing directory.${NC}"
    exit 1
fi

# Create the directory
echo -e "${GREEN}Creating directory: ${SITE_DIR}${NC}"
mkdir -p "$SITE_DIR"

# Basic site information
echo
echo -e "${YELLOW}Let's set up your website:${NC}"
read -p "Site Title: " SITE_TITLE
read -p "Site Tagline: " SITE_TAGLINE
read -p "Site Description: " SITE_DESCRIPTION
read -p "Base URL (e.g., https://example.com/): " SITE_URL
read -p "Default Author: " SITE_AUTHOR

# Primary color
echo
echo -e "${YELLOW}Choose a primary color for your site:${NC}"
echo "1. Blue (#005f73)"
echo "2. Green (#2a9d8f)"
echo "3. Red (#e76f51)"
echo "4. Purple (#7209b7)"
echo "5. Custom"
read -p "Selection (1-5): " COLOR_CHOICE

case $COLOR_CHOICE in
    1) PRIMARY_COLOR="#005f73" ;;
    2) PRIMARY_COLOR="#2a9d8f" ;;
    3) PRIMARY_COLOR="#e76f51" ;;
    4) PRIMARY_COLOR="#7209b7" ;;
    5) read -p "Enter custom color hex code (e.g., #ff5500): " PRIMARY_COLOR ;;
    *) PRIMARY_COLOR="#005f73" ;;
esac

# Create directory structure
echo
echo -e "${GREEN}Creating directory structure...${NC}"
mkdir -p "$SITE_DIR/content"
mkdir -p "$SITE_DIR/layouts"
mkdir -p "$SITE_DIR/static/images"
mkdir -p "$SITE_DIR/assets/css"
mkdir -p "$SITE_DIR/config/prompts"
mkdir -p "$SITE_DIR/config/keywords"
mkdir -p "$SITE_DIR/scripts"

# Copy template files
echo -e "${GREEN}Copying template files...${NC}"
cp -r "$TEMPLATE_DIR/layouts" "$SITE_DIR/"
cp -r "$TEMPLATE_DIR/scripts" "$SITE_DIR/"
cp "$TEMPLATE_DIR/README.md" "$SITE_DIR/"

# Create site.xml config
echo -e "${GREEN}Creating site configuration...${NC}"
cat > "$SITE_DIR/config/site.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!-- Site Configuration -->
<site>
  <!-- Basic Site Information -->
  <info>
    <title>${SITE_TITLE}</title>
    <tagline>${SITE_TAGLINE}</tagline>
    <description>${SITE_DESCRIPTION}</description>
    <baseURL>${SITE_URL}</baseURL>
    <languageCode>en-us</languageCode>
    <defaultAuthor>${SITE_AUTHOR}</defaultAuthor>
    <copyrightText>© $(date +%Y) ${SITE_TITLE}. All rights reserved.</copyrightText>
  </info>
  
  <!-- SEO Settings -->
  <seo>
    <metaDescription>${SITE_DESCRIPTION}</metaDescription>
    <keywords>${SITE_TITLE}, ${SITE_TAGLINE}</keywords>
    <twitterCard>summary_large_image</twitterCard>
    <ogType>website</ogType>
    <canonical>true</canonical>
    <robots>index, follow</robots>
    <defaultImage>/images/logo.jpg</defaultImage>
  </seo>
  
  <!-- Analytics and Ads -->
  <analytics>
    <googleAnalyticsID></googleAnalyticsID>
    <googleAdsenseID></googleAdsenseID>
    <googleTagManagerID></googleTagManagerID>
    <facebookPixelID></facebookPixelID>
  </analytics>
  
  <!-- Branding -->
  <branding>
    <logoPath>/images/logo.jpg</logoPath>
    <logoAlt>${SITE_TITLE} Logo</logoAlt>
    <faviconPath>/favicon.ico</faviconPath>
    <mobileTitleSuffix>${SITE_TITLE}</mobileTitleSuffix>
    <mobileDisclaimer>${SITE_TAGLINE}</mobileDisclaimer>
  </branding>
  
  <!-- Design -->
  <design>
    <primaryColor>${PRIMARY_COLOR}</primaryColor>
    <secondaryColor>#94d2bd</secondaryColor>
    <accentColor>#e9d8a6</accentColor>
    <textColor>#001219</textColor>
    <backgroundColor>#ffffff</backgroundColor>
    <linkColor>${PRIMARY_COLOR}</linkColor>
    <headerBackgroundColor>#ffffff</headerBackgroundColor>
    <footerBackgroundColor>#f8f9fa</footerBackgroundColor>
    <font>
      <headings>Inter</headings>
      <body>Roboto</body>
      <monospace>Roboto Mono</monospace>
    </font>
  </design>
  
  <!-- Content Settings -->
  <content>
    <postsPerPage>10</postsPerPage>
    <featuredPostCount>3</featuredPostCount>
    <showRelatedPosts>true</showRelatedPosts>
    <relatedPostCount>3</relatedPostCount>
    <enableComments>false</enableComments>
    <commentsProvider></commentsProvider>
    <showAuthorInfo>true</showAuthorInfo>
    <showPostDate>true</showPostDate>
    <showReadingTime>true</showReadingTime>
  </content>
</site>
EOF

# Create navigation.xml config
echo -e "${GREEN}Creating navigation configuration...${NC}"
cat > "$SITE_DIR/config/navigation.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!-- Navigation Menu Configuration -->
<navigation>
  <menu type="main">
    <item>
      <title>Home</title>
      <url>/</url>
      <visible>true</visible>
    </item>
    <item>
      <title>Posts</title>
      <url>/posts/</url>
      <visible>true</visible>
    </item>
    <item>
      <title>About</title>
      <url>/about/</url>
      <visible>true</visible>
    </item>
    <item>
      <title>Contact</title>
      <url>/contact/</url>
      <visible>true</visible>
    </item>
  </menu>
  
  <menu type="footer">
    <item>
      <title>Privacy Policy</title>
      <url>/privacy/</url>
      <visible>true</visible>
    </item>
    <item>
      <title>Terms of Service</title>
      <url>/terms/</url>
      <visible>true</visible>
    </item>
    <item>
      <title>Contact</title>
      <url>/contact/</url>
      <visible>true</visible>
    </item>
  </menu>
</navigation>
EOF

# Create social.xml config
echo -e "${GREEN}Creating social media configuration...${NC}"
cat > "$SITE_DIR/config/social.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!-- Social Media Configuration -->
<social>
  <accounts>
    <platform>
      <name>X</name>
      <url></url>
      <icon>/images/x-icon.png</icon>
      <username></username>
      <enabled>false</enabled>
    </platform>
    
    <platform>
      <name>BlueSky</name>
      <url></url>
      <icon>/images/bluesky-icon.png</icon>
      <username></username>
      <enabled>false</enabled>
    </platform>
  </accounts>
  
  <sharing>
    <default_hashtags>${SITE_TITLE}</default_hashtags>
    <posts_per_day>3</posts_per_day>
    <best_posting_times>9:00,12:00,17:00</best_posting_times>
  </sharing>
  
  <openai>
    <api_key></api_key>
    <model>gpt-4</model>
  </openai>
</social>
EOF

# Create keywords file
echo -e "${GREEN}Creating keywords configuration...${NC}"
cat > "$SITE_DIR/config/keywords/primary.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!-- Primary Keywords Configuration -->
<keywords>
  <category name="core_topics">
    <keyword>Example Topic 1</keyword>
    <keyword>Example Topic 2</keyword>
    <keyword>Example Topic 3</keyword>
  </category>
  
  <category name="key_people">
    <keyword>Person 1</keyword>
    <keyword>Person 2</keyword>
    <keyword>Person 3</keyword>
  </category>
  
  <category name="hashtags">
    <keyword>${SITE_TITLE}</keyword>
  </category>
</keywords>
EOF

# Create prompts file
echo -e "${GREEN}Creating prompts configuration...${NC}"
cat > "$SITE_DIR/config/prompts/news.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!-- News Generation Prompts -->
<prompts>
  <system_prompt>
    <![CDATA[
    You are a content writer for ${SITE_TITLE}. Your task is to create informative news articles based on the following prompt. 
    The content should be engaging and reflect ${SITE_DESCRIPTION}.
    
    Write in a journalistic style with professional tone. Include quotes from fictional sources and officials when appropriate.
    
    Make sure to:
    - Use proper journalistic structure with a strong headline and lead paragraph
    - Include moderate specific details to make the story believable
    - Maintain ${SITE_TITLE}'s unique voice throughout the article
    - Target an audience that is general readers interested in current events
    - Include a compelling hook and satisfying conclusion
    ]]>
  </system_prompt>
  
  <user_prompt>
    <![CDATA[
    Write a medium news article with the following characteristics:
    
    Topic: {{article_topic}}
    
    Key elements to include:
    - {{key_element_1}}
    - {{key_element_2}}
    - {{key_element_3}}
    
    The article should mention {{key_people}} and focus on {{focus_area}}.
    
    Make the headline attention-grabbing and include the date {{current_date}} in a natural way.
    
    The article should be formatted in Markdown with a clear headline, subheadings, and paragraphs.
    ]]>
  </user_prompt>
</prompts>
EOF

# Create hugo.toml
echo -e "${GREEN}Creating Hugo configuration...${NC}"
cat > "$SITE_DIR/hugo.toml" <<EOF
baseURL = "${SITE_URL}"
languageCode = "en-us"
title = "${SITE_TITLE}"

[params]
  logo = "${SITE_TITLE}"
  slogan = "${SITE_TAGLINE}"
  mission_statement = "${SITE_DESCRIPTION}"

[[params.nav]]
  title = "Home"
  url = "/"

[[params.nav]]
  title = "Posts"
  url = "/posts/"

[[params.nav]]
  title = "About"
  url = "/about/"

[[params.nav]]
  title = "Contact"
  url = "/contact/"

[sitemap]
  changefreq = "weekly"
  priority = 0.5
  filename = "sitemap.xml"

# Enable built-in sitemap generation
[outputs]
  home = ["HTML", "RSS", "SITEMAP"]
EOF

# Create a simple style.css file
echo -e "${GREEN}Creating CSS file...${NC}"
cat > "$SITE_DIR/assets/css/style.css" <<EOF
:root {
  --primary-color: ${PRIMARY_COLOR};
  --secondary-color: #94d2bd;
  --accent-color: #e9d8a6;
  --text-color: #001219;
  --background-color: #ffffff;
  --link-color: ${PRIMARY_COLOR};
  --header-bg-color: #ffffff;
  --footer-bg-color: #f8f9fa;
  
  --font-headings: 'Inter', sans-serif;
  --font-body: 'Roboto', sans-serif;
  --font-mono: 'Roboto Mono', monospace;
}

body {
  font-family: var(--font-body);
  color: var(--text-color);
  background-color: var(--background-color);
  line-height: 1.6;
  margin: 0;
  padding: 0;
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-headings);
  color: var(--primary-color);
}

a {
  color: var(--link-color);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

header {
  background-color: var(--header-bg-color);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 1rem 0;
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1rem;
}

.logo {
  font-weight: bold;
  font-size: 1.5rem;
}

.header-nav {
  display: flex;
  gap: 1.5rem;
}

footer {
  background-color: var(--footer-bg-color);
  padding: 2rem 0;
  margin-top: 2rem;
  text-align: center;
}

main {
  min-height: 70vh;
  padding: 2rem 0;
}

/* Responsive */
@media (max-width: 768px) {
  .header-container {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-nav {
    margin-top: 1rem;
    flex-direction: column;
    gap: 0.5rem;
  }
}
EOF

# Create placeholder images directory
echo -e "${GREEN}Creating placeholder images...${NC}"
# Note: In a real script, you would either copy placeholder images or
# generate them using something like ImageMagick

# Set up git
echo -e "${GREEN}Setting up Git repository...${NC}"
cd "$SITE_DIR"
git init
git add .
git commit -m "Initial commit from website template"

echo
echo -e "${GREEN}===========================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}===========================${NC}"
echo
echo -e "Your new website has been created at: ${BLUE}${SITE_DIR}${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add your content to the content/ directory"
echo "2. Update your keywords in config/keywords/primary.xml"
echo "3. Customize your prompts in config/prompts/"
echo "4. Run 'hugo server' to preview your site locally"
echo "5. Deploy your site using Netlify, GitHub Pages, or similar"
echo
echo -e "${GREEN}Happy website building!${NC}"

exit 0