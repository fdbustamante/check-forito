from dataclasses import dataclass, field


@dataclass
class Post:
    post_id: int
    body: str
    reply_to: str
    url: str = ''
    page: int = 0
    hrefs: list = field(default_factory=list)
    images: list = field(default_factory=list)
    reply_images: list = field(default_factory=list)
