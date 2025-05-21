#!/usr/bin/env python3
"""
Story Generator for CringeWorthy
This script generates sensational, tabloid-style articles for the CringeWorthy website.
"""

import os
import sys
import datetime
import re
import json
import random
import requests
import time
import glob
import xml.etree.ElementTree as ET
from openai import OpenAI

# Import the image URL function
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from image_urls import get_image_url_for_topic

# Initialize OpenAI client using environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def load_trending_topics(num_topics=15, min_score=5.0):
    """
    Load trending topics from the rtrends/cringe XML files
    
    Args:
        num_topics: Number of topics to return
        min_score: Minimum trend score to consider
        
    Returns:
        list: A list of trending topics with scores
    """
    try:
        # Find the most recent trends file
        trend_files = glob.glob(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "rtrends", "cringe", "*.xml"
        ))
        
        if not trend_files:
            print("No trend files found")
            return []
            
        # Sort by modified time to get the most recent
        latest_file = max(trend_files, key=os.path.getmtime)
        print(f"Loading trends from {latest_file}")
        
        # Read file as text since it might not be properly formatted XML
        with open(latest_file, 'r') as f:
            xml_content = f.read()
        
        # Extract trends and scores using regex
        trends = []
        pattern = r'<trend score="([^"]+)">([^<]+)</trend>'
        matches = re.findall(pattern, xml_content)
        
        for score_str, topic in matches:
            try:
                score = float(score_str)
            except ValueError:
                score = 0.0
            
            # Skip trends that are likely not useful for generating content
            skip_phrases = [
                "suicide", "harm", "www", "http", "sex", "murder", "kill", 
                "dealers", "addiction", "disappearance", "necessarily",
                "watch", "youtube", "stream", ".com", "remind", "officially"
            ]
            
            if score < min_score:
                continue
                
            if not topic or any(phrase in topic.lower() for phrase in skip_phrases):
                continue
                
            # Clean up the topic - remove stop words and format for better prompting
            topic = topic.replace("_", " ").strip()
            
            # Group similar trends
            similar = False
            for existing in trends:
                if topic.lower() in existing["topic"].lower() or existing["topic"].lower() in topic.lower():
                    # Combine scores and keep the longer topic
                    existing["score"] += score
                    if len(topic) > len(existing["topic"]):
                        existing["topic"] = topic
                    similar = True
                    break
            
            if not similar:
                trends.append({
                    "topic": topic,
                    "score": score
                })
        
        # Select top N trends by score
        top_trends = sorted(trends, key=lambda x: x["score"], reverse=True)[:num_topics]
        return top_trends
        
    except Exception as e:
        print(f"Error loading trending topics: {e}")
        return []

def generate_short_title(title, retries=3, base_delay=5):
    """
    Generates a shorter, more concise version of the headline for the ticker.
    This is a purpose-built headline that's grammatically complete but shorter.
    """
    prompt = f"""Create a shortened version of this satirical headline for a news ticker:
    
    Original headline: "{title}"
    
    Requirements:
    1. Maximum 40-60 characters
    2. Must be a complete phrase (not ending mid-thought)
    3. CRITICAL: Preserve the punchline, irony, or satirical element that makes the headline funny
    4. Remove unnecessary words but KEEP the humorous twist or punchline
    5. Keep it grammatically correct
    6. Do not use ellipses (...)
    7. Do NOT include hashtags (like #trending)
    8. Do NOT use double quotes within the headline
    
    Just return the shortened headline text with no quotation marks, no explanation.
    """
    
    delay = base_delay
    for attempt in range(retries):
        try:
            messages = [
                {"role": "system", "content": "You create concise headline versions for news tickers while preserving the humor, irony, and punchlines that make satirical headlines effective."},
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=100,
                temperature=0.4
            )
            
            short_title = response.choices[0].message.content.strip()
            short_title = short_title.strip('"').strip("'")
            
            print(f"[DEBUG] Generated short title: {short_title}")
            return short_title
            
        except Exception as e:
            print(f"[ERROR] Error generating short title (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
    
    # If all attempts fail, return a truncated version of the original
    words = title.split()
    if len(words) > 6:
        return " ".join(words[:6])
    return title

def generate_article(section="shame", topic="cringe", override_tag=None):
    """Generate an article using OpenAI."""
    
    # Get current date for frontmatter
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Enhanced themes for more varied content
    themes = [
        "true crime",
        "urban legends",
        "creepy encounters",
        "horror stories",
        "mundane tragedy",
        "everyday comedy",
        "suburbia nightmares",
        "high school embarrassment",
        "summer camp disasters",
        "college dorm stories",
        "family secrets",
        "workplace humiliation",
        "social media fails",
        "first date disasters",
        "public speaking mishaps"
    ]
    
    # Example article titles to use as inspiration
    title_examples = [
        "Denver Optometrist Has a Gay Cult Following",
        "Florida Woman Arrested for Stealing Neighbors' Teeth",
        "He Cooked and Ate Him: Armin Meiwes' Cannibal Feast Shocks Germany",
        "Marlene Warren's Clown Killer Stuns Florida",
        "New York Man Sentenced for Fatally Stabbing His Pregnant Wife",
        "Christmas Miracle! Severed Leg Hops to Hospital",
        "You Won't Believe the Transformation After This Obese Man Took Ozempic!",
        "Titanic Survivors Found on Board!",
        "News Reporter Eaten Alive by 30ft Crocodile",
        "They Don't Want You to Know the Truth About UFO Sightings and Alien",
        "California Man Charged in Slaughter of Princess, a Pet Pig",
        "Chicago Chef Serves Human Fingers in Gourmet Dish",
        "Mysterious Radio Signal Makes Listeners Speak in Tongues",
        "Rebecca Coriam's Disney Cruise Disappearance",
        "Craigslist Killer Richard Beasley's Deadly Ads",
        "See the Heartwarming Relationship Between This Man and His Pet Octopus",
        "LA Quake Opens Gates of Hell",
        "After Receiving Heart Transplant, Woman's Personality Changes",
        "Pet Parrot Solves Owner's Murder",
        "Grandma's Knitting Needles Turn Deadly",
        "Viral TikTok Dance Summons Ancient Demon",
        "AI Therapist Starts Blackmailing Patients",
        "This is What Parents Wish They Knew Before Having Kids",
        "This is What Happens When You Don't Sleep for 21 Days"
    ]
    
    # Randomly select a theme if using the default topic
    if topic == "cringe":
        selected_theme = random.choice(themes)
    else:
        selected_theme = topic
    
    # Choose a random title example for inspiration
    title_inspiration = random.choice(title_examples)
    
    # Extract tone and taboos if they exist in the topic
    tone_match = re.search(r'TONE:(\w+)', topic)
    taboos_match = re.search(r'VIOLATE_TABOOS:(.*?)(?:\s+TONE|\s*$)', topic)
    
    story_tone = tone_match.group(1) if tone_match else "disturbing"
    taboos_to_violate = taboos_match.group(1).strip() if taboos_match else "social norms"
    
    # Create more boundary-pushing system prompt with focus on strong verbs
    system_prompt = f"""You are a writer for CringeWorthy, a site that publishes stories that VIOLATE SOCIAL NORMS and BREAK TABOOS.
Your specialty is creating content that is {story_tone} - using powerful verbs to push boundaries that make readers uncomfortable.
You focus on specific individuals who cross lines that shouldn't be crossed, crafting actions that trigger visceral reactions.
Your content deliberately violates taboos around {taboos_to_violate}.

Following Stephen King's writing advice:
- You rely on strong, precise verbs rather than adjective strings
- You let actions carry the horror rather than descriptions
- You focus on what characters DO rather than lengthy descriptions of what they ARE
- You write with active voice instead of passive constructions

Never sanitize or tone down your content - your readers want to feel genuinely uncomfortable."""
    
    # Section-specific user prompts with extra taboo-breaking guidance
    if section == "shame":
        user_prompt = f"""Write a deeply {story_tone} article for CringeWorthy's 'shame' section that deliberately violates taboos around {taboos_to_violate}.

Create a specific narrative about {selected_theme} featuring characters who cross boundaries in ways that induce physical discomfort in readers. Make it visceral, detailed, and uncomfortably plausible.

WRITING STYLE:
- Use strong, precise verbs instead of adjective strings
- Let actions carry the horror rather than descriptions
- Focus on what characters DO rather than lengthy descriptions of what they ARE
- Write with active voice and direct language
- Create discomfort through specific details rather than elaborate modifiers

Your article MUST:
- Have a provocative, boundary-pushing title (formatted with # at the beginning)
- Focus on specific named individuals (fictional but realistic) who violate important social norms
- Include precise, visceral details that make readers physically uncomfortable
- Incorporate at least two witness/expert quotes that heighten the taboo-breaking aspects
- Include social reactions that show the norm violations being recognized
- End with a disturbing twist that leaves readers feeling morally challenged
- Be 400-600 words of concentrated discomfort
- Use markdown formatting

IMPORTANT:
- Create characters whose motivations are disturbingly relatable
- Include details that make readers say "OH GOD WHY?" out loud
- Target taboos that exist in seemingly normal settings
- Make readers question their own boundaries
- DO NOT sanitize your content - push the boundaries as far as possible
- DO NOT use nested quotes or hashtags in the title

Make the reader squirm with discomfort while being unable to look away."""
        
    elif section == "recent":
        # System prompt already set above
        
        user_prompt = f"""Write a deeply {story_tone} article for CringeWorthy's 'recent' section that deliberately violates taboos around {taboos_to_violate}.

Create a recent news-style article about {selected_theme} that's viscerally uncomfortable yet presented as serious journalism. Focus on events that happened within the last week.

WRITING STYLE:
- Use strong, precise verbs instead of adjective strings
- Let actions carry the horror rather than descriptions
- Focus on what people DID rather than lengthy descriptions of what they ARE
- Write with active voice and direct language
- Create discomfort through specific details rather than elaborate modifiers

Your article MUST:
- Have a boundary-pushing, uncomfortable title (formatted with # at the beginning)
- Present norm-violating behavior with deadpan journalistic seriousness
- Include full names, ages, and locations of people involved in taboo-breaking activities
- Contain specific dates, times, and disturbingly detailed descriptions
- Include at least two quotes from witnesses/experts that normalize the taboo violation
- Reference organizations/institutions complicit in or responding to the norm violation
- Include social media reactions showing both outrage and disturbing support
- End with an uncomfortable development that suggests worse to come
- Be 400-600 words of concentrated unease
- Use markdown formatting

IMPORTANT GUIDANCE:
- Present morally questionable behavior as if it were normal news
- Include specific visceral details that create physical discomfort
- Create a journalistic tone that makes taboo violations seem almost reasonable
- Show how social boundaries are being eroded in ways that feel plausible
- Make readers question whether this could actually happen
- DO NOT sanitize your content - make it genuinely uncomfortable

Your tone should be serious and measured even as you describe things that violate social norms."""
        
    elif section == "lore":
        system_prompt = f"You are a content writer for CringeWorthy, a website that documents bizarre history, unexplained phenomena, and cultural oddities. Your writing style blends academic analysis with tabloid sensationalism to create compelling deep-dives into strange topics. You follow Stephen King's writing advice, using strong verbs rather than adjective strings."
        
        user_prompt = f"""Write a detailed article for the 'lore' section of CringeWorthy about the history or cultural significance of {selected_theme}.

Create an in-depth exploration that analyzes a bizarre phenomenon, unexplained mystery, or strange cultural practice. For inspiration, consider topics like: "{title_inspiration}"

WRITING STYLE:
- Use strong, precise verbs instead of adjective strings
- Let actions carry the narrative rather than descriptions
- Focus on what people DID rather than lengthy descriptions of what they WERE
- Write with active voice and direct language
- Create discomfort through specific details rather than elaborate modifiers

The article should:
- Have an intriguing, scholarly but sensational title (formatted with # at the beginning)
- IMPORTANT: Do NOT use hashtags in the title (like #trending)
- IMPORTANT: Do NOT use nested quotes in the title
- Set the story in a specific time period (80s, 90s, 00s, or more recent)
- Provide historical context with specific dates, locations, and real people involved
- Include at least 3 section headings (## for subheadings)
- Reference specific cases, incidents, or examples with names and dates
- Quote experts or witnesses (with credentials)
- Present multiple theories or perspectives on the phenomenon
- Include surprising facts or little-known details
- Connect to broader cultural patterns or psychological principles
- End with unanswered questions or implications for the future
- Be 500-700 words in length
- Use markdown formatting

Balance academic analysis with storytelling to create a compelling narrative that feels well-researched but still has the sensational quality of tabloid journalism."""
    else:
        # Default prompt for other sections
        system_prompt = f"You are a content writer for CringeWorthy, a website that documents embarrassing and cringeworthy events. Write in a satirical but informative style."
        
        user_prompt = f"""Write a short article for the '{section}' section of CringeWorthy about {selected_theme}. 
        
The article should:
- Be funny but factual
- Be formatted in markdown with a # Title at the beginning
- IMPORTANT: Do NOT use hashtags in the title (like #trending)
- IMPORTANT: Do NOT use nested quotes in the title
- Have a catchy and satirical style"""
    
    # Generate content using OpenAI with a focus on strong verbs
    try:
        # Add a reminder about Stephen King's writing advice to the system prompt
        enhanced_system_prompt = system_prompt + """

WRITING STYLE REMINDERS:
- "The road to hell is paved with adverbs." - Stephen King
- Use strong, precise verbs rather than adjective strings
- Let actions carry the story rather than descriptions
- Focus on what characters DO rather than what they ARE
- Write with active voice rather than passive constructions
- Choose concrete nouns and powerful verbs over modifiers
"""
        response = client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o for highest quality
            messages=[
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        # Extract title and body
        lines = content.strip().split('\n')
        title = ""
        body = content
        
        # Look for title in first line
        if lines and lines[0].startswith('#'):
            title = lines[0].lstrip('#').strip()
            body = '\n'.join(lines[1:]).strip()
        elif len(lines) > 1:
            # If no markdown title, use first line as title
            title = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()
            
        # Clean up title - remove hashtags and fix nested quotes
        title = title.replace('"', "'")  # Replace double quotes with single quotes
        # Remove hashtags but preserve the text after them
        title = re.sub(r'#(\w+)', r'\1', title)
        
        # Generate filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = f"{safe_title}_{timestamp}.md"
        
        # Generate keywords from the title and content
        keywords = []
        # Extract potential keywords from the title and content
        potential_keywords = title.lower().split() + body.lower().split()
        # Filter out common words and keep unique meaningful keywords
        common_words = ["the", "and", "a", "in", "to", "of", "for", "on", "with", "at", "from", "by"]
        keywords = list(set([word for word in potential_keywords if word.isalpha() and len(word) > 3 and word not in common_words]))[:10]
        
        # Create a short summary
        summary_text = body.replace("\n", " ")[:200] + "..."
        
        # Get current date with timezone
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
        
        # Get image URL for the topic
        image_url, image_credit = get_image_url_for_topic(selected_theme)
        
        # Generate a short title
        short_title = generate_short_title(title)
        
        # Ensure the title doesn't have quotes that would break YAML
        safe_title = title.replace('"', "'")
        
        # Use override_tag if provided, otherwise use the topic
        tag = override_tag if override_tag else topic.upper()
        
        # Create frontmatter in YAML format
        frontmatter = f"""---
archived: false
author: "CringeWorthy Staff"
date: "{current_datetime}"
draft: false
image: "{image_url}"
image_credit: "{image_credit}"
keywords: "{', '.join(keywords)}"
shortTitle: "{short_title}"
summary: "{summary_text}"
tags:
  - "{tag}"
  - "CRINGE"
title: "{safe_title}"
---"""
        
        # Combine frontmatter and content
        full_content = frontmatter + "\n\n" + body
        
        # Determine output directory and create if it doesn't exist
        content_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", section)
        os.makedirs(content_dir, exist_ok=True)
        
        # Write to file
        filepath = os.path.join(content_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        print(f"Article '{title}' generated and saved to: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"Error generating article: {e}")
        # Fall back to sample content if OpenAI fails
        return generate_sample_content(section, topic)

def generate_sample_content(section="shame", topic="cringe", override_tag=None):
    """Generate a sample content file without using OpenAI."""
    
    # Get current date for frontmatter
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Sample content dictionary with multiple options for each section
    sample_content = {
        "shame": [
            {
                "title": "Florida Woman Arrested for Stealing Neighbors' Teeth",
                "content": """
NAPLES, FL – In a bizarre case that has shocked local residents and dental professionals alike, 43-year-old Marjorie Wilkins was arrested Tuesday after authorities discovered she had allegedly stolen over 200 dentures and dental prosthetics from her neighbors in the Sunnyvale Retirement Community.

Wilkins, a former dental hygienist, had been collecting the stolen teeth for what she described as an "artistic project" that involved creating a "smile mosaic" in her garden patio. The thefts reportedly took place over a period of eight months, with residents unsure where their missing dentures were disappearing to.

"I'd wake up, and my teeth would just be gone from the bathroom counter," said Harold Jenkins, 82, one of the victims. "At first I thought I was just being forgetful, but then it started happening to everyone in the complex."

The investigation began after Gladys Peterson, 76, spotted Wilkins sneaking into her apartment at 3 AM on Sunday and witnessed her taking Peterson's $3,200 custom dentures from a glass of water beside her bed.

"She was like a dental ninja," Peterson told CringeWorthy. "I turned on the light and caught her red-handed with my teeth in her pocket. Who does that?"

When police searched Wilkins' apartment, they discovered the extensive collection meticulously organized in labeled containers, along with a half-completed mosaic on her patio depicting what appears to be a large smiling face made entirely of dental prosthetics.

Dr. Ricardo Molina, a local dentist familiar with several of the victims, expressed shock at the incident. "In 35 years of practicing dentistry, I've never seen anything like this. The psychological impact on these seniors has been significant – many feel violated in a deeply personal way."

Wilkins' attorney, Jeffrey Steinman, claims his client suffers from "creative compulsions" and didn't understand the impact of her actions. "Ms. Wilkins sees herself as a found-object artist. She believed she was creating something beautiful from items that were sometimes left unattended."

The Sunnyvale Retirement Community has since installed security cameras in hallways and offered lockboxes to residents for storing dentures and other valuables.

In a shocking twist, local gallery owner Penelope Shriftman has offered to display Wilkins' unfinished "smile mosaic" as part of an upcoming exhibition on outsider art, pending the return of the dental items to their rightful owners.

"It's disturbing, yes, but also strangely captivating," said Shriftman. "The piece raises important questions about aging, identity, and consumption in modern America."

Wilkins faces multiple charges of burglary and theft, with a preliminary hearing scheduled for next month. If convicted, she could face up to 15 years in prison.
"""
            },
            {
                "title": "High School Principal's 'Motivational' Assembly Goes Horribly Wrong",
                "content": """
In what was intended to be an inspirational pep rally at Westfield High, Principal Roger Daniels decided that what teens really needed was a heavy dose of, in his words, "real talk about the dangers of social media."

What followed was 45 excruciating minutes that students are now calling "The Cringe Assembly of 2025."

Daniels, 58, took the stage in a backward baseball cap and ripped jeans, greeting students with "Yo yo yo, what's up my homies?" before launching into a rap about Instagram safety that included the now-infamous line, "Sliding in DMs is super sus / Your principal sees you making a fuss."

"At first we thought it was a joke," said senior Alicia Chen. "Then he started showing memes from like 2010 and saying 'This is lit, am I right, fam?'"

The assembly reached peak discomfort when Daniels displayed his own TikTok account, @PrincipalDripDaniels, and attempted to recreate a dance trend that, according to junior Marcus Williams, "wasn't even trending anymore."

School counselor Debra Hemsworth admitted it was difficult to watch. "His heart was in the right place, but seeing him dab in 2025 while saying 'No cap, frfr' physically hurt me. Several teachers had to leave the room."

The video, inevitably captured by dozens of students, has since gone viral on multiple platforms, with one compilation reaching 8 million views under the hashtag #PrincipalDripDaniels.

When reached for comment, Daniels stated that he was "just trying to connect with the youngsters in their language," apparently unaware that his use of "youngsters" was part of the problem.

Remember, adults: sometimes the most motivational thing you can do is just be yourself—your actual self, not whatever this was.
"""
            },
            {
                "title": "Family's 'True Crime' Vacation Photos Horrify Local Community",
                "content": """
The Wilson family returned from their summer road trip with souvenirs, memories, and a social media scandal after posting what they called their "Serial Killer Tour 2025" album on Facebook.

Martha and Greg Wilson, along with their three children (ages 8, 11, and 14), spent three weeks visiting infamous crime scenes across the country, documenting their smiling family portraits at each location with captions like "Having a killer time at the Bundy house!" and "Ted would have loved this view!"

Local community members were horrified when Martha shared the 78-photo album to the Pleasantville Community Facebook group, which typically features posts about lost pets and school bake sales.

"I thought it was a sick joke at first," said neighbor Deborah Klein. "But there they were, posing with peace signs outside crime scenes where actual people lost their lives. The kids were making fake scared faces at the Dahmer apartment building. Who does that?"

The post received over 300 comments before being removed by group admins, with reactions ranging from disgust to concerns about the children's welfare.

When contacted for comment, Martha Wilson seemed genuinely surprised by the backlash. "It was educational! We listened to true crime podcasts in the car and taught the kids about forensic science. Greg even brought string to make red yarn conspiracy boards at each hotel!"

Child psychologist Dr. Tanya Rivera notes this is part of a disturbing trend. "The true crime entertainment boom has normalized some very dark subject matter. But there's a vast difference between interest and tourism that treats real tragedy as entertainment."

The Wilson family has since made their social media accounts private after receiving what Martha called "totally unfair judgment from people who probably secretly watch the same Netflix documentaries we do."

Remember folks, just because you're fascinated by something doesn't mean you should pack the minivan and make it your family vacation theme.
"""
            }
        ],
        "recent": [
            {
                "title": "News Reporter Eaten Alive by 30ft Crocodile During Live Broadcast",
                "content": """
DARWIN, AUSTRALIA – Viewers of Channel 7 News were left in shock yesterday when environmental reporter Vanessa Clarke, 34, was attacked and consumed by a massive saltwater crocodile during a live broadcast from Kakadu National Park.

The incident occurred at approximately 6:23 PM local time on March 12, 2025, as Clarke was reporting on conservation efforts for the protected reptiles. According to witnesses, the 30-foot crocodile, believed to be one of the largest ever recorded, emerged suddenly from the murky waters of the Yellow Water Billabong.

"One second she was talking about crocodile habitat preservation, and the next this absolute monster just launched itself from the water," said cameraman Tim Buckley, 41, who continued filming even as the attack unfolded. "I've worked in wildlife documentation for fifteen years, and I've never seen anything move that fast or with such deliberate precision."

Wildlife expert Dr. Eleanor Froese of the Australian Reptile Research Center explained that such aggressive behavior is extremely unusual. "Saltwater crocodiles typically don't view humans as prey items. This particular specimen, which locals have apparently nicknamed 'Thunderjaw,' appears to be an outlier both in size and temperament."

The live broadcast, which has since been removed from official platforms but continues to circulate on various social media channels, shows Clarke mid-sentence when the massive reptile appears behind her. Despite the production team's frantic warnings through her earpiece, Clarke had only a fraction of a second to react before being pulled into the water.

"TURN AROUND! BEHIND YOU!" were the last words heard from the production booth before the attack, according to network sources who requested anonymity due to the ongoing investigation.

The Northern Territory Parks and Wildlife Commission has assembled a team to locate and potentially euthanize the crocodile, though environmental activists have already begun protesting the decision.

"This is the crocodile's natural habitat, and humans enter at their own risk," said Jasmine Wong, spokesperson for Wildlife Protection Australia. "While this tragedy is heartbreaking, destroying this remarkable specimen would be counter to everything Ms. Clarke herself advocated for in her reporting."

Channel 7 News director Philip Garrison issued a statement expressing profound shock and extending condolences to Clarke's family. "Vanessa was a passionate environmental journalist who dedicated her career to educating the public about wildlife conservation. This terrible tragedy has devastated our entire news family."

In a macabre development, viewership for Channel 7's evening news program has increased by 340% since the incident, and applications for the now-vacant environmental reporter position have reportedly exceeded 200.

Authorities continue to warn visitors to Kakadu National Park to exercise extreme caution and to maintain a safe distance from all waterways.
"""
            },
            {
                "title": "'Haunted' Summer Camp Turned Out To Be Just Bad Plumbing",
                "content": """
Camp Whispering Pines made headlines this week after what organizers initially claimed was "a paranormal event of unprecedented scale" turned out to be nothing more than decades-old pipes and pre-teen imaginations.

The incident began late Tuesday night when campers in Cabin 7 reported hearing "ghostly whispers" and "otherworldly moaning" coming from the walls. By morning, the story had evolved to include "shadowy figures" and "cold spots," sending the camp into a frenzy.

Camp director Gerald Hoffman, 62, immediately contacted local news outlets and three paranormal investigation teams before placing an emergency call to renowned medium Sylvia Nightshade, who charged $900 to perform an emergency "spiritual cleansing" via Zoom.

"I sensed a powerful presence," Nightshade informed concerned parents during the livestreamed session. "The entity appears to be a former camper who drowned in the lake in the 1940s."

Crisis struck when camper Tyler Brooks, 11, posted video of the "haunting" to his FutureVerse account, complete with AI-enhanced "ghost detection" filters. The video garnered 3 million views in six hours and prompted dozens of parents to drive to the camp to retrieve their children.

The situation was finally resolved when maintenance worker Joe Diaz, who had been on vacation, returned yesterday and immediately identified the issue.

"It's just air in the water pipes," Diaz explained. "Happens every summer when it gets hot. I've been telling them to replace the plumbing since 2018."

By the time Diaz had fixed the issue with a $12 part from the hardware store, Camp Whispering Pines had already spent $6,400 on emergency paranormal services, including $1,200 for a "psychic protection package" that consisted primarily of sage bundles and scented candles.

When asked for comment, Hoffman insisted the expenditure was "absolutely necessary for camper safety" before announcing next year's new camp theme: "Supernatural Survival Skills."
"""
            },
            {
                "title": "Suburban Dad's Attempt to Recreate Viral Recipe Ends in Fire Department Visit",
                "content": """
What began as a Father's Day cooking adventure for the Henderson family ended with three fire trucks, a neighborhood evacuation, and what local firefighters are calling "the most unnecessary emergency of 2025."

Tom Henderson, 43, decided to surprise his family by recreating a viral "Flaming Coconut Spectacle Cake" he'd seen on KitchenClout, despite having what his wife describes as "absolutely zero baking experience."

According to witnesses, Henderson substituted several key ingredients, including replacing food-grade alcohol with what he reportedly told neighbors was "basically the same thing" — isopropyl alcohol from his garage workbench.

"The recipe video showed this elegant, controlled blue flame that lasted for like 30 seconds," said next-door neighbor Patricia Wu. "What Tom created was more like a category 5 fire tornado that shot up and singed his pergola."

Home security footage from across the street captured Henderson repeatedly yelling "It's fine! This is supposed to happen!" while his patio table was engulfed in flames that reached approximately 12 feet high.

Fire Chief Marquez confirmed that by the time emergency services arrived, Henderson had attempted to extinguish the blaze with both a garden hose and, puzzlingly, a two-liter bottle of Diet Sprite.

"In my 22 years of service, I've never seen someone try to put out an alcohol fire with carbonated soda," Marquez told CringeWorthy. "Though I have to give him credit for already having packed an overnight bag for his inevitable stay on the couch."

Henderson's 15-year-old daughter Sophia reportedly captured the entire incident, with her video "Dad Sets Backyard On Fire Trying To Be A KitchenClout Chef (NOT CLICKBAIT)" currently trending at 7 million views.

When reached for comment, Henderson insisted he was "actually very close to getting it right" and has already ordered ingredients for a "much more reasonable Fourth of July trifle."
"""
            }
        ],
        "lore": [
            {
                "title": "The Origins of the Influencer Apology Video: A Brief History",
                "content": """
Few internet rituals are as established as the Influencer Apology Video. This modern form of public penance follows a formula so predictable you could set your watch to it: the deep sigh, the uncharacteristic lack of makeup, the somber gray hoodie, and the strategic editing cuts between tears.

But how did this peculiar performance art come to be?

## The Pre-History: Celebrity Apologies

Before YouTube, celebrities issued formal written statements through publicists or held controlled press conferences. These were careful affairs, crafted by PR teams to minimize damage while appearing sincere.

The watershed moment came in 2006 when Michael Richards (Kramer from Seinfeld) appeared on David Letterman via satellite to apologize for a racist onstage rant. His awkward, uncomfortable apology became one of the first viral apology videos, though it wasn't yet in the modern format.

## The Evolution Begins: 2010-2014

As YouTube stars gained prominence, they developed a more intimate relationship with audiences than traditional celebrities. When early YouTubers faced backlash, they spoke directly to their cameras rather than through publicists.

The first recognizable modern apology video is widely credited to beauty guru EstelleBeauty in 2011, who filmed herself crying over accusations of plagiarizing makeup tutorials. The video established key elements: direct address to the camera, visible distress, informal setting (her bedroom), and claims of "being authentic."

## The Golden Age: 2015-2020

By 2015, the format was codified. The infamous 2017 apology from ShoppingHaul for her sponsored content scandal checked all the boxes that now seem mandatory:

1. Neutral or somber clothing
2. Minimal to no makeup
3. Red eyes suggesting pre-video crying
4. Several deep sighs
5. The phrase "I never meant to hurt anyone"
6. Vague promises to "do better"
7. A reference to "taking time to reflect"

The format peaked with LoganSphere's 2018 apology video, which was so formulaic it prompted parodies across the internet and an SNL sketch "Apology Clothing Line: For When You've Been Cancelled."

## Today: Self-Awareness and Meta-Apologies

Modern influencers now face a dilemma: audiences instantly recognize the apology video formula as performative, yet deviation risks appearing insincere.

Some influencers now acknowledge the formula within their apologies ("I know this looks like every apology video ever"), creating a meta-awareness that attempts to disarm criticism of the format while still using it.

Whatever form they take, these digital acts of contrition remain essential to the influencer lifecycle: transgress, apologize, rebuild, repeat. The ritual continues to evolve, but its cultural role as modern public penance remains unchanged.
"""
            },
            {
                "title": "The Craigslist Killer: How Richard Beasley's Deadly Ads Lured Victims to Their Doom",
                "content": """
# The Craigslist Killer: How Richard Beasley's Deadly Ads Lured Victims to Their Doom

In the vast digital marketplace of Craigslist, where millions exchange goods and services daily, few users ever considered that responding to a job listing could be a fatal decision. Yet between August and November 2011, Richard Beasley transformed this mundane online platform into a hunting ground, using false promises of employment to lure vulnerable men to their deaths in one of the most chilling cases of internet-facilitated murder in American history.

## The Perfect Trap: Employment in a Desperate Economy

Richard Beasley, a 52-year-old self-proclaimed street preacher from Akron, Ohio, crafted his deadly scheme during the aftermath of the 2008 financial crisis. With unemployment rates hovering near 9% nationwide and significantly higher for middle-aged men without college degrees, Beasley recognized an opportunity in economic desperation.

"The timing was diabolically perfect," explains criminologist Dr. Vanessa Rodriguez of Ohio State University. "Beasley targeted a demographic—middle-aged men with few prospects—who were desperate enough to respond to a job that seemed too good to be true: $300 weekly pay, housing provided, minimal duties overseeing a sprawling, isolated farm property."

The advertisement, posted in the jobs section of Craigslist, specifically requested candidates who were down on their luck and looking for a fresh start, with few ties to family or community. This crucial detail ensured that victims would be less likely to be immediately reported missing.

## The Killing Fields of Noble County

What appeared to be a generous employment opportunity was in reality a calculated trap. When job-seekers arrived in Noble County, Ohio, expecting to meet their new employer, they instead encountered Beasley and his teenage accomplice, Brogan Rafferty, a 16-year-old high school student who Beasley had mentored through church activities.

"The remote location was key to the murders' execution," notes former FBI profiler Erica Carter. "Beasley selected a 688-acre plot in rural Ohio—heavily wooded, isolated, with no nearby witnesses. It was the perfect killing field."

When David Pauley, 51, of Norfolk, Virginia arrived on October 23, 2011, Beasley and Rafferty led him into the woods, ostensibly to view the property he would be managing. Instead, Beasley shot Pauley in the back of the head, robbed him of his possessions, and buried his body in a shallow grave. Similar fates awaited Ralph Geiger, 56, and Timothy Kern, 47.

## The One Who Got Away: Scott Davis's Miraculous Escape

The killing spree might have continued indefinitely if not for the extraordinary escape of Scott Davis, a 48-year-old South Carolina man who became Beasley's fourth target on November 6, 2011. Davis, unlike previous victims, grew suspicious when Beasley and Rafferty claimed their car had broken down and suggested walking through the woods to reach the farm.

"Something just felt off," Davis later testified at trial. "I had this moment where I thought, 'Why would the car break down at this exact spot?'"

As they walked through the dense forest, Beasley pulled a gun and attempted to execute Davis as he had the others. The bullet grazed Davis's arm, and in a desperate struggle, he managed to knock the weapon away, flee into the woods, and hide for seven excruciating hours before finding help at a nearby home.

"Davis's escape was nothing short of miraculous," Carter explains. "He navigated unfamiliar terrain while wounded and in shock, evading armed pursuers. The probability of survival in such circumstances is extraordinarily low."

## Digital Breadcrumbs: How Technology Facilitated Both Crime and Capture

Ironically, the same digital platform that allowed Beasley to find his victims ultimately contributed to his capture. After Davis reported his attack to authorities, investigators quickly located the Craigslist advertisements and traced the email accounts and IP addresses back to a house in Akron where Beasley had been staying.

"This case represents a fundamental shift in how serial killers operate in the digital age," notes cyber-criminologist Dr. Paul Menzer. "Historically, killers like Ted Bundy had to physically place themselves in locations to identify and approach victims, risking witness identification. Beasley could anonymously browse responses from the safety of his home, selecting ideal victims based on their written applications."

When police arrested Beasley on November 16, 2011, they discovered evidence connecting him to three murders. Subsequent searches, guided by information from Rafferty, led to the recovery of all three bodies.

## Legacy of the Craigslist Killings

In 2013, Richard Beasley was convicted of three counts of aggravated murder and sentenced to death. He currently remains on death row at Chillicothe Correctional Institution while his appeals process continues. Brogan Rafferty, despite being a minor, received a life sentence without parole for his role in the murders.

The case permanently altered how people view online marketplaces and job listings. Craigslist implemented additional safety measures, and "meet in public places" became standard advice for any transaction initiated online.

As we increasingly conduct our lives through digital platforms, the Craigslist Killings stand as a chilling reminder that predators evolve alongside technology. While Richard Beasley sits on death row, the question remains: how many other killers are currently crafting the perfect digital lure, waiting for desperate victims to respond?
"""
            },
            {
                "title": "Unmasking the Uncomfortable: A Cultural History of Secondhand Embarrassment",
                "content": """
# Unmasking the Uncomfortable: A Cultural History of Secondhand Embarrassment

That peculiar tightness in your chest. The instinctive grimace. The overwhelming urge to look away, even as you find yourself unable to do so. These are the hallmark symptoms of "secondhand embarrassment"—the phenomenon of feeling embarrassed on behalf of someone else who seems oblivious to their own social transgression.

But while the feeling may seem universal, its expression, intensity, and the scenarios that trigger it vary significantly across cultures and historical periods. This suggests something more complex than a simple biological response—secondhand embarrassment is a cultural construction with its own fascinating evolution.

## The Anthropological Roots

Anthropologists have long noted that embarrassment serves a crucial social function. Dr. Eleanor Fisk of Cambridge University explains: "Embarrassment is essentially a signal that acknowledges when social norms have been violated. It communicates to the group: 'I recognize my error and feel bad about it,' which helps maintain group cohesion."

Secondhand embarrassment—sometimes called "vicarious embarrassment" or the German-derived term "fremdschämen"—evolved as an extension of this mechanism. When we feel embarrassed for others, we're experiencing a form of social mirror neurons activating; we're simulating what we would feel in their situation.

## Historical Variations

What constitutes embarrassing behavior has evolved dramatically throughout history. In Victorian England, exposing an ankle might trigger massive secondhand embarrassment among onlookers. In 1950s America, discussing divorce at a dinner party could create the same effect.

"Each era has its own 'cringe code'—a set of behaviors that society has deemed inappropriate or tactless," notes cultural historian Dr. Marcus Chen. "Studying these codes reveals the hidden values and anxieties of a society."

## The Television Amplification

Secondhand embarrassment truly entered the cultural lexicon with the rise of sitcoms in the 1950s and 60s. Shows like "I Love Lucy" deliberately engineered situations to provoke this response in viewers. By the 1990s, sitcoms like "Seinfeld" had elevated cringe-inducing social faux pas to high art.

The British perfected the form with shows like "The Office," which creator Ricky Gervais described as "deliberately designed to make you watch through your fingers." These shows worked precisely because they triggered genuine physiological discomfort that viewers paradoxically found pleasurable.

## The Digital Transformation

The internet revolutionized secondhand embarrassment in two significant ways:

First, it created an archive of embarrassing moments that previously would have been witnessed by few and quickly forgotten. Now, awkward political gaffes, celebrity interview mishaps, and everyday people's uncomfortable moments can be preserved forever and shared globally.

Second, it allowed for the commodification of cringe. Content creators quickly realized that triggering secondhand embarrassment generated engagement, leading to the deliberate production of cringe content across platforms.

## The Psychology of Cringe Consumption

Why do we seek out content that makes us physically uncomfortable? Psychologist Dr. Amara Johnson explains: "There's evidence that experiencing manageable negative emotions in a controlled setting actually produces pleasure. It's similar to how we enjoy horror movies or spicy food—the discomfort is contained and therefore enjoyable."

Additionally, witnessing others' social failures can be reassuring. "Seeing someone else violate social norms worse than you ever have provides a sense of relief and superiority," notes Dr. Johnson. "It reaffirms your own social competence."

## Cultural Variations

Interestingly, the intensity of secondhand embarrassment varies significantly across cultures. Research shows that cultures with more rigid social hierarchies and stricter behavioral codes—like Japan and South Korea—report higher levels of vicarious embarrassment than more individualistic societies.

"In collectivist cultures, social harmony is prioritized over individual expression," explains social psychologist Dr. Kim Min-ji. "This creates a heightened sensitivity to situations that might disrupt group cohesion, including others' social missteps."

This cultural variation reminds us that while the physical sensation of cringing might be universal, its triggers and intensity are culturally conditioned responses that reveal our deeper social values.

As we continue to globalize and digitize our social experiences, our relationship with secondhand embarrassment continues to evolve—but our fascination with watching others navigate the complex world of social norms shows no signs of diminishing.
"""
            }
        ]
    }
    
    # Select content based on section
    if section in sample_content:
        # Randomly select an article from the section's options
        article = random.choice(sample_content[section])
        title = article["title"]
        content = article["content"]
    else:
        # Default content for other sections
        title = f"Sample {section.capitalize()} Article"
        content = f"""
This is a sample article for the {section} section about {topic}.

It contains placeholder content that would normally be generated using OpenAI.

This article is meant to demonstrate the structure and formatting of content for the CringeWorthy website.

The actual content would be more detailed, informative, and styled according to the site's tone and voice.
"""
    
    # Clean up title - remove hashtags and fix nested quotes
    title = title.replace('"', "'")  # Replace double quotes with single quotes
    # Remove hashtags but preserve the text after them
    title = re.sub(r'#(\w+)', r'\1', title)
    
    # Generate filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    filename = f"{safe_title}_{timestamp}.md"
    
    # Generate keywords from the topic
    keywords = []
    if topic == "cringe":
        # Extract potential keywords from the title and content
        potential_keywords = title.lower().split() + content.lower().split()
        # Filter out common words and keep unique meaningful keywords
        common_words = ["the", "and", "a", "in", "to", "of", "for", "on", "with", "at", "from", "by"]
        keywords = list(set([word for word in potential_keywords if word.isalpha() and len(word) > 3 and word not in common_words]))[:10]
    else:
        # Just use the topic as a keyword
        keywords = [topic, "embarrassment", "awkward", "cringe", "social", "embarrassing"]
    
    # Create a short summary
    summary_text = content.replace("\n", " ")[:200] + "..."
    
    # Get current date with timezone
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
    
    # Get image URL for the topic
    image_url, image_credit = get_image_url_for_topic(topic)
    
    # Generate a short title
    short_title = generate_short_title(title)
    
    # Ensure the title doesn't have quotes that would break YAML
    safe_title = title.replace('"', "'")
    
    # Use override_tag if provided, otherwise use the topic
    tag = override_tag if override_tag else topic.upper()
    
    # Create frontmatter in YAML format
    frontmatter = f"""---
archived: false
author: "CringeWorthy Staff"
date: "{current_datetime}"
draft: false
image: "{image_url}"
image_credit: "{image_credit}"
keywords: "{', '.join(keywords)}"
shortTitle: "{short_title}"
summary: "{summary_text}"
tags:
  - "{tag}"
  - "CRINGE"
title: "{safe_title}"
---"""
    
    # Combine frontmatter and content
    full_content = frontmatter + "\n\n" + content
    
    # Determine output directory and create if it doesn't exist
    content_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", section)
    os.makedirs(content_dir, exist_ok=True)
    
    # Write to file
    filepath = os.path.join(content_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    print(f"Sample article '{title}' generated and saved to: {filepath}")
    return filepath

def evaluate_trend_potential(trends, max_trends=5):
    """
    Evaluate the potential of each trend for creating a compelling CringeWorthy story
    
    Args:
        trends: List of trend dictionaries with 'topic' and 'score' keys
        max_trends: Maximum number of trends to evaluate
        
    Returns:
        dict: The best trend with its story angle
    """
    try:
        if not trends:
            return None
            
        # Take the top N trends for evaluation
        top_trends = trends[:max_trends]
        
        print(f"Evaluating {len(top_trends)} trends for story potential...")
        
        # Create a batch prompt to evaluate all trends at once
        trend_list = "\n".join([f"{i+1}. {t['topic']} (score: {t['score']:.2f})" for i, t in enumerate(top_trends)])
        
        # Choose a tone that creates visceral discomfort, fascination, and revulsion
        # Focus on strong verbs with minimal adjectives following King's advice
        narrative_tones = [
            # Social norm violations - verb-focused
            "violates (actions that break fundamental social contracts and destroy trust)",
            "corrupts (transforms innocence into depravity through calculated steps)",
            "betrays (undermines sacred relationships with calculated deception)",
            "degrades (strips dignity through public humiliation)",
            "revolts (triggers immediate physical disgust reactions)",
            "inverts (flips moral expectations in ways that challenge fundamental beliefs)",
            "obsesses (fixates beyond reason, consuming all rational thought)",
            "destroys (obliterates boundaries between acceptable and unthinkable)",
            "warps (distorts reality into unrecognizable yet familiar shapes)",
            
            # Mundane horror - verb-focused
            "transforms (mutates ordinary settings into nightmares)",
            "lurks (conceals horrors beneath mundane surfaces)",
            "infects (spreads through ordinary interactions, contaminating normalcy)",
            "distorts (twists everyday routines into uncanny experiences)",
            "looms (threatens to collapse the façade of normal life)",
            
            # Psychological elements - verb-focused
            "fractures (splinters perception between reality and nightmare)",
            "penetrates (invades private spaces and intimate moments)",
            "dissects (examines uncomfortable truths with clinical detachment)",
            "entraps (lures victims into situations they cannot escape)",
            "haunts (lingers in memory long after exposure)"
        ]
        selected_tone = random.choice(narrative_tones)
        
        evaluation_prompt = f"""
        You are the lead content creator for CringeWorthy, a site dedicated to stories that create the perfect blend of fascination and revulsion - content readers can't look away from despite being deeply disturbed. 
        
        Our readers crave content that:
        - Breaks social taboos and violates norms
        - Creates mundane horror from everyday settings
        - Includes surreal elements that challenge perception
        - Invades private moments with voyeuristic detail
        - Triggers existential dread and lingering discomfort
        
        For this assignment, we're looking for content with a strong focus on a narrative that {selected_tone}.
        
        WRITING GUIDANCE:
        - Use powerful verbs rather than adjective strings
        - Let actions carry the horror rather than descriptions
        - Create discomfort through specific details rather than elaborate modifiers
        - Focus on what characters DO rather than lengthy descriptions of what they ARE
        
        Review these trends and identify which could be developed into our most captivating yet disturbing story:

        {trend_list}

        For each trend, ruthlessly evaluate:
        1. VISCERAL POTENTIAL: How effectively it could create physical discomfort through specific actions
        2. MUNDANE HORROR: How everyday settings transform into something deeply unsettling
        3. SURREAL ELEMENTS: How reality bends while remaining disturbingly plausible
        4. INTIMATE VIOLATION: How private moments expose through specific, uncomfortable details
        5. EXISTENTIAL IMPLICATIONS: How it triggers deeper dread about reality
        
        Select the trend with the STRONGEST potential to create content readers can't forget.
        
        Provide:
        - The trend number with the most disturbing potential
        - Why this topic perfectly blends fascination with revulsion
        - A specific story concept focused on unsettling actions and events
        - The specific taboos and norms violated
        
        Format your response as:
        SELECTED: [trend number]
        TOPIC: [the trend text]
        POTENTIAL: [why this creates the perfect blend of fascination and revulsion]
        ANGLE: [specific story concept that's both captivating and disturbing]
        TABOOS: [which norms/boundaries this violates]
        ELEMENTS: [specific mundane horror, surreal, intimate, or existential elements to include]
        TONE: {selected_tone.split(' ')[0]}
        """
        
        evaluation_response = client.chat.completions.create(
            model="gpt-4o",  # Use the more capable model for pushing boundaries
            messages=[
                {"role": "system", "content": """You are a visionary editor who identifies stories with the perfect blend of fascination and revulsion.
                You specialize in finding topics that can be transformed into content readers can't look away from despite being deeply disturbed.
                
                Your expertise includes identifying opportunities for:
                - Mundane horror that transforms everyday settings into something profoundly unsettling
                - Surreal and bizarre elements that still feel disturbingly plausible
                - Intimate, voyeuristic details that feel invasive yet captivating
                - Visceral specifics that create physical discomfort while maintaining reader fascination
                - Scenarios that trigger existential dread or questions about reality and humanity
                
                You're drawn to content that is simultaneously titillating and revolting, intimate and horrifying, bizarrely captivating and deeply wrong.
                Your goal is to create content readers will never forget no matter how much they might wish to - stories that haunt them long after reading."""},
                {"role": "user", "content": evaluation_prompt}
            ],
            max_tokens=500,
            temperature=0.9
        )
        
        evaluation = evaluation_response.choices[0].message.content.strip()
        print(f"Trend evaluation results:\n{evaluation}")
        
        # Parse the evaluation to get the selected trend
        selected_num = None
        selected_topic = None
        story_angle = None
        story_tone = None
        taboos = None
        elements = None
        
        for line in evaluation.split('\n'):
            if line.startswith('SELECTED:'):
                try:
                    selected_num = int(line.split(':')[1].strip()) - 1  # Convert to 0-indexed
                except:
                    pass
            elif line.startswith('TOPIC:'):
                selected_topic = line.split(':', 1)[1].strip()
            elif line.startswith('ANGLE:'):
                story_angle = line.split(':', 1)[1].strip()
            elif line.startswith('TONE:'):
                story_tone = line.split(':', 1)[1].strip()
            elif line.startswith('TABOOS:'):
                taboos = line.split(':', 1)[1].strip()
            elif line.startswith('ELEMENTS:'):
                elements = line.split(':', 1)[1].strip()
        
        # Use the selected trend if found, otherwise use the top trend
        if selected_num is not None and selected_num < len(top_trends):
            selected_trend = top_trends[selected_num]
        else:
            selected_trend = top_trends[0]
            
        # If we got a better topic description from the evaluation, use it
        if selected_topic:
            selected_trend['topic'] = selected_topic
            
        # Add the story angle, tone, taboos and elements to the trend
        if story_angle:
            selected_trend['angle'] = story_angle
            
        if story_tone:
            selected_trend['tone'] = story_tone
            
        if taboos:
            selected_trend['taboos'] = taboos
            
        if elements:
            selected_trend['elements'] = elements
        
        return selected_trend
        
    except Exception as e:
        print(f"Error evaluating trend potential: {e}")
        # Fall back to the top trend by score
        return trends[0] if trends else None

def get_trend_context(topic, story_angle=None, story_tone=None):
    """
    Get additional context about a trending topic
    
    Args:
        topic: The topic to search for
        story_angle: Optional suggested story angle
        story_tone: Optional tone for the story (horrifying, twisted, humiliating, etc.)
        
    Returns:
        str: A narrative setup for the story
    """
    try:
        # Check if the topic has enough substance
        if len(topic.split()) < 2 or len(topic) < 5:
            return None
        
        # Default tone if none provided
        if not story_tone:
            story_tone = "disturbing"
        
        # Generate a deeply unsettling narrative setup based on the topic and angle
        context_prompt = f"""
        You are creating a narrative setup for CringeWorthy, where readers come to experience visceral discomfort
        mixed with morbid fascination - content they can't look away from despite being deeply disturbed.
        
        Using the topic '{topic}'
        {f"and concept '{story_angle}'" if story_angle else ""}, 
        create a narrative scenario that is {story_tone} with elements that are both repulsive and captivating.
        
        WRITING PRINCIPLES - FOLLOW STEPHEN KING'S ADVICE:
        - Use strong, precise verbs instead of adjective strings
        - Let actions carry the horror rather than descriptions
        - Create discomfort through specific details rather than elaborate modifiers
        - Focus on what characters DO rather than lengthy descriptions of what they ARE
        - Write with active voice rather than passive constructions
        
        Your scenario MUST:
        1. Be aggressively {story_tone} - push this aspect to its most uncomfortable extreme
        2. Set in a specific location with named individuals
        3. Include mundane settings with deeply disturbing undertones
        4. Feature intimate details that feel invasive yet fascinating
        5. Create a scenario with surreal or bizarre elements that still feels unsettlingly real
        6. Include specific visceral details that make readers physically recoil yet keep reading
        7. Start with "CANNOT-LOOK-AWAY SCENARIO:"
        
        ESSENTIAL ELEMENTS TO INCLUDE:
        - A mix of the familiar and the deeply wrong to create mundane horror
        - Intimate details that feel voyeuristic and inappropriate 
        - Surreal or bizarre elements that challenge perception or reality
        - Existential implications that create lingering dread
        - Visceral specifics that trigger physical disgust responses
        - Characters performing actions that violate deep social taboos
        - A situation so specific yet strange it feels like a nightmare made real
        - Elements that are simultaneously titillating and revolting
        
        CRITICAL: Make it detailed, specific, and realistic enough that readers cannot dismiss it,
        yet disturbing enough that they question why they're still reading. Create the perfect blend 
        of fascination and revulsion that defines CringeWorthy content.
        
        Limit to 4-6 sentences of concentrated, visceral discomfort.
        """
        
        context_response = client.chat.completions.create(
            model="gpt-4o",  # Use the best model for creative, nuanced content
            messages=[
                {"role": "system", "content": f"""You are a master storyteller who crafts scenarios using powerful verbs and precise details.
                You specialize in content that repulses yet captivates - creating narratives readers can't escape despite their discomfort.
                Your strength is {story_tone} content that combines fascination with revulsion through concrete actions.
                
                Following Stephen King's writing advice, you:
                - Rely on strong, precise verbs rather than adjective strings
                - Let actions carry the horror rather than descriptions
                - Create discomfort through specific details rather than elaborate modifiers
                - Focus on what characters DO rather than lengthy descriptions of what they ARE
                - Write with active voice and muscular prose
                
                Your narratives transform ordinary settings, invade private moments,
                distort perception, and violate taboos through concrete actions and powerful verbs.
                
                Never hold back or sanitize - create narratives readers will never forget, despite wishing they could."""},
                {"role": "user", "content": context_prompt}
            ],
            max_tokens=300,
            temperature=0.95
        )
        
        context = context_response.choices[0].message.content.strip()
        return context
        
    except Exception as e:
        print(f"Error getting trend context: {e}")
        return None

def generate_trending_story(section="recent", use_sample=False):
    """
    Generates a story based on trending topics from the rtrends/cringe data
    
    Args:
        section: The section to generate content for (shame, recent, lore)
        use_sample: Whether to use sample content instead of OpenAI
        
    Returns:
        str: The path to the generated file
    """
    # Load trending topics
    trend_candidates = load_trending_topics(num_topics=15, min_score=5.0)
    
    if not trend_candidates:
        print("No trend candidates found, using default topic")
        trend_topic = "cringe"
        clean_tag = "TRENDING"
        trend_context = None
    else:
        # Evaluate trends to find the one with the best story potential
        best_trend = evaluate_trend_potential(trend_candidates, max_trends=7)
        
        if not best_trend:
            print("No suitable trend found, using default topic")
            trend_topic = "cringe"
            clean_tag = "TRENDING"
            trend_context = None
        else:
            # Get topic, suggested angle, tone, taboos, and additional elements
            trend_topic = best_trend["topic"]
            story_angle = best_trend.get("angle")
            story_tone = best_trend.get("tone", "disturbing")
            taboos = best_trend.get("taboos", "social norms around appropriate behavior")
            elements = best_trend.get("elements", "mundane horror, surreal aspects, intimate details")
            clean_tag = trend_topic.split(" ")[0].upper()  # Use the first word as a tag
            
            print(f"Selected trending topic: '{trend_topic}'")
            if story_angle:
                print(f"Story angle: '{story_angle}'")
            if story_tone:
                print(f"Story tone: {story_tone}")
            if taboos:
                print(f"Taboos to violate: {taboos}")
            if elements:
                print(f"Key elements to include: {elements}")
            
            # Get additional context for the trend
            trend_context = get_trend_context(trend_topic, story_angle, story_tone)
            if trend_context:
                print(f"Generated context: {trend_context}")
                
                # Add context to the topic for the generator prompt with all guidance
                full_topic = f"{trend_topic} {trend_context} TONE:{story_tone} VIOLATE_TABOOS:{taboos} INCLUDE_ELEMENTS:{elements}"
            else:
                full_topic = f"{trend_topic} TONE:{story_tone} VIOLATE_TABOOS:{taboos} INCLUDE_ELEMENTS:{elements}"
            
            # Use the topic with context
            trend_topic = full_topic
    
    print(f"Generating {section} article with trending topic: '{trend_topic}'")
    
    # Generate the article
    if use_sample:
        return generate_sample_content(section, trend_topic, override_tag=clean_tag)
    else:
        try:
            return generate_article(section, trend_topic, override_tag=clean_tag)
        except Exception as e:
            print(f"Failed to generate article: {e}")
            return generate_sample_content(section, trend_topic, override_tag=clean_tag)

if __name__ == "__main__":
    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--trending":
        # Generate content based on trending topics
        sections = ["shame", "recent", "lore"]
        for section in sections:
            print(f"\nGenerating trending content for {section} section...")
            generate_trending_story(section)
    else:
        # Generate standard content for each section
        sections = ["shame", "recent", "lore"]
        for section in sections:
            print(f"\nGenerating content for {section} section...")
            try:
                generate_article(section, "cringe")
            except Exception as e:
                print(f"Failed to generate article for {section}: {e}")
                generate_sample_content(section, "cringe")
    
    print("\nContent generation complete!")