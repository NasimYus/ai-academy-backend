"""Presenters mapping Blog ORM rows to API schemas (legacy Blog brief/details).

Relationships (author/category) are eager-loaded by the repository.
"""

import re

from app.models.blog import Blog
from app.models.comment import Comment
from app.schemas.blog import BlogBrief, BlogDetail
from app.schemas.review import CommentRead
from app.schemas.user import UserBrief


def truncate(text: str, length: int = 160, with_tail: bool = True) -> str:
    """Word-boundary truncate (parity of legacy helper `truncate`)."""
    if len(text) <= length:
        return text
    head = re.match(rf"^(.{{1,{length}}})(\s.*|$)", text, re.S)
    cut = head.group(1) if head else text[:length]
    return f"{cut} ..." if with_tail else cut


def comment_tree(comments: list[Comment]) -> list[CommentRead]:
    """Group flat comments into top-level entries with one level of replies."""
    nodes: dict[int, CommentRead] = {}
    for c in comments:
        nodes[c.id] = CommentRead(
            id=c.id,
            user=UserBrief.model_validate(c.user) if c.user else None,
            comment=c.comment,
            created_at=c.created_at,
            replies=[],
        )
    roots: list[CommentRead] = []
    for c in comments:
        if c.reply_id and c.reply_id in nodes:
            nodes[c.reply_id].replies.append(nodes[c.id])
        else:
            roots.append(nodes[c.id])
    return roots


def to_brief(blog: Blog, comment_count: int) -> BlogBrief:
    return BlogBrief(
        id=blog.id,
        title=blog.title,
        image=blog.image,
        description=truncate(blog.description, 160),
        created_at=blog.created_at,
        author=UserBrief.model_validate(blog.author) if blog.author else None,
        comment_count=comment_count,
        category=blog.category.title if blog.category else None,
    )


def to_detail(blog: Blog, comments: list[Comment]) -> BlogDetail:
    return BlogDetail(
        **to_brief(blog, len(comments)).model_dump(),
        content=blog.content,
        comments=comment_tree(comments),
    )
