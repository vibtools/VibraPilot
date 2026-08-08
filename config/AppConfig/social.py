"""Public social/community presence shown by VibraPilot.

Only public profiles linked from the official Vib Tools website are configured.
Secrets, OAuth credentials, access tokens and webhook credentials must never be
stored in this module.
"""

SOCIAL_LINKS = (
    {
        "platform": "GitHub",
        "display_name": "Vib Tools",
        "url": "https://github.com/vibtools",
        "enabled": True,
    },
    {
        "platform": "X",
        "display_name": "Vib Tools",
        "url": "https://x.com/vibtools",
        "enabled": True,
    },
    {
        "platform": "Facebook",
        "display_name": "Vib Tools",
        "url": "https://www.facebook.com/vib.tools",
        "enabled": True,
    },
    {
        "platform": "Instagram",
        "display_name": "Vib Tools",
        "url": "https://www.instagram.com/vibtools",
        "enabled": True,
    },
    {
        "platform": "Reddit",
        "display_name": "Vib Tools",
        "url": "https://www.reddit.com/user/VibTools/",
        "enabled": True,
    },
    {
        "platform": "TikTok",
        "display_name": "Vib Tools",
        "url": "https://www.tiktok.com/@vibtools",
        "enabled": True,
    },
    {
        "platform": "GitLab",
        "display_name": "Vib Tools",
        "url": "https://gitlab.com/vibtools",
        "enabled": True,
    },
)
