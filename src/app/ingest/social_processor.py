"""Social Media Processor - Parse exports from various platforms.

Handles Twitter/X archives, LinkedIn exports, Facebook data,
and other social media platforms for personal AI training.
"""

from pathlib import Path
from typing import Optional, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import json
import csv
import hashlib


@dataclass
class SocialPost:
    """A single social media post."""
    
    platform: str
    content: str
    timestamp: Optional[datetime] = None
    post_type: str = "post"  # post, reply, repost, etc.
    engagement: dict = field(default_factory=dict)  # likes, shares, etc.
    media_urls: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    url: Optional[str] = None
    
    @property
    def id(self) -> str:
        """Generate unique ID for this post."""
        content_hash = hashlib.md5(
            f"{self.platform}:{self.content[:100]}:{self.timestamp}".encode()
        ).hexdigest()
        return content_hash
    
    def to_text(self) -> str:
        """Convert post to text for embedding."""
        parts = [f"[{self.platform.upper()}]"]
        
        if self.timestamp:
            parts.append(f"({self.timestamp.strftime('%Y-%m-%d')})")
        
        parts.append(self.content)
        
        if self.hashtags:
            parts.append(f"Tags: {', '.join(self.hashtags)}")
        
        return " ".join(parts)


@dataclass
class SocialProfile:
    """Aggregated social media profile data."""
    
    platform: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    posts: list[SocialPost] = field(default_factory=list)
    
    @property
    def post_count(self) -> int:
        return len(self.posts)


class SocialMediaProcessor:
    """Process social media exports for personal AI training.
    
    Supports Twitter/X archives, LinkedIn exports, and generic CSV/JSON.
    
    Example:
        >>> processor = SocialMediaProcessor()
        >>> profile = processor.process_twitter_archive("twitter-archive/")
        >>> for post in profile.posts:
        ...     print(post.content)
    """
    
    def __init__(self) -> None:
        """Initialize the social media processor."""
        pass
    
    def process_twitter_archive(self, archive_path: str | Path) -> SocialProfile:
        """Process a Twitter/X data archive.
        
        Args:
            archive_path: Path to the extracted Twitter archive.
        
        Returns:
            SocialProfile: Parsed Twitter profile and posts.
        """
        path = Path(archive_path)
        
        profile = SocialProfile(platform="twitter", username="")
        
        # Look for tweets.js or tweet.js
        tweets_file = None
        for candidate in ["data/tweets.js", "data/tweet.js", "tweets.js"]:
            if (path / candidate).exists():
                tweets_file = path / candidate
                break
        
        if tweets_file:
            profile.posts = list(self._parse_twitter_js(tweets_file))
        
        # Try to get profile info
        profile_file = path / "data" / "account.js"
        if profile_file.exists():
            self._parse_twitter_account(profile_file, profile)
        
        return profile
    
    def _parse_twitter_js(self, file_path: Path) -> Iterator[SocialPost]:
        """Parse Twitter's JavaScript data file.
        
        Args:
            file_path: Path to tweets.js file.
        
        Yields:
            SocialPost: Parsed tweets.
        """
        content = file_path.read_text(encoding="utf-8")
        
        # Twitter exports have "window.YTD.tweets.part0 = [...]" format
        # Find the JSON array
        start_idx = content.find("[")
        if start_idx == -1:
            return
        
        try:
            data = json.loads(content[start_idx:])
        except json.JSONDecodeError:
            return
        
        for item in data:
            tweet = item.get("tweet", item)
            
            post = SocialPost(
                platform="twitter",
                content=tweet.get("full_text", tweet.get("text", "")),
                post_type="tweet",
            )
            
            # Parse timestamp
            created_at = tweet.get("created_at")
            if created_at:
                try:
                    post.timestamp = datetime.strptime(
                        created_at, "%a %b %d %H:%M:%S %z %Y"
                    )
                except ValueError:
                    pass
            
            # Extract hashtags
            entities = tweet.get("entities", {})
            hashtags = entities.get("hashtags", [])
            post.hashtags = [h.get("text", "") for h in hashtags]
            
            # Extract mentions
            mentions = entities.get("user_mentions", [])
            post.mentions = [m.get("screen_name", "") for m in mentions]
            
            yield post
    
    def _parse_twitter_account(self, file_path: Path, profile: SocialProfile) -> None:
        """Parse Twitter account.js for profile info."""
        content = file_path.read_text(encoding="utf-8")
        start_idx = content.find("[")
        if start_idx == -1:
            return
        
        try:
            data = json.loads(content[start_idx:])
            if data:
                account = data[0].get("account", {})
                profile.username = account.get("username", "")
                profile.display_name = account.get("accountDisplayName", "")
        except (json.JSONDecodeError, IndexError, KeyError):
            pass
    
    def process_linkedin_export(self, export_path: str | Path) -> SocialProfile:
        """Process a LinkedIn data export.
        
        Args:
            export_path: Path to the LinkedIn export directory.
        
        Returns:
            SocialProfile: Parsed LinkedIn profile and posts.
        """
        path = Path(export_path)
        profile = SocialProfile(platform="linkedin", username="")
        
        # LinkedIn exports posts in Shares.csv
        shares_file = path / "Shares.csv"
        if shares_file.exists():
            profile.posts = list(self._parse_linkedin_csv(shares_file))
        
        # Get profile info
        profile_file = path / "Profile.csv"
        if profile_file.exists():
            self._parse_linkedin_profile(profile_file, profile)
        
        return profile
    
    def _parse_linkedin_csv(self, file_path: Path) -> Iterator[SocialPost]:
        """Parse LinkedIn shares CSV."""
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                content = row.get("ShareCommentary", row.get("Text", ""))
                if not content:
                    continue
                
                post = SocialPost(
                    platform="linkedin",
                    content=content,
                    post_type="share",
                )
                
                date_str = row.get("Date", "")
                if date_str:
                    try:
                        post.timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        pass
                
                yield post
    
    def _parse_linkedin_profile(self, file_path: Path, profile: SocialProfile) -> None:
        """Parse LinkedIn profile CSV."""
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                profile.display_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                profile.bio = row.get("Summary", "")
                break
    
    def process_generic_json(
        self,
        file_path: str | Path,
        platform: str = "unknown"
    ) -> SocialProfile:
        """Process a generic JSON export.
        
        Args:
            file_path: Path to JSON file.
            platform: Platform name.
        
        Returns:
            SocialProfile: Parsed profile.
        """
        path = Path(file_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        
        profile = SocialProfile(platform=platform, username="")
        
        # Handle list of posts
        posts_data = data if isinstance(data, list) else data.get("posts", [])
        
        for item in posts_data:
            content = item.get("content") or item.get("text") or item.get("body", "")
            if content:
                profile.posts.append(SocialPost(
                    platform=platform,
                    content=content,
                ))
        
        return profile


def process_social_export(path: str, platform: str = "auto") -> SocialProfile:
    """Process a social media export.
    
    Args:
        path: Path to the export.
        platform: Platform type or "auto" to detect.
    
    Returns:
        SocialProfile: Parsed profile.
    """
    processor = SocialMediaProcessor()
    path_obj = Path(path)
    
    if platform == "auto":
        # Auto-detect platform
        if (path_obj / "data" / "tweets.js").exists():
            platform = "twitter"
        elif (path_obj / "Shares.csv").exists():
            platform = "linkedin"
        else:
            platform = "generic"
    
    if platform == "twitter":
        return processor.process_twitter_archive(path)
    elif platform == "linkedin":
        return processor.process_linkedin_export(path)
    else:
        return processor.process_generic_json(path)
