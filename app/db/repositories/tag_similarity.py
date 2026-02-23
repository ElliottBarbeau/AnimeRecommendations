from sqlalchemy import select, func

from app.db.models.tag_similarity import TagSimilarity


def get_max_related_similarity(
    db,
    liked_tags: list[str],
    unknown_tag: str,
    min_cooccurrence_count: int = 2,
):
    if not liked_tags:
        return None

    return db.execute(
        select(func.max(TagSimilarity.jaccard_score))
        .where(
            TagSimilarity.source_tag.in_(liked_tags),
            TagSimilarity.related_tag == unknown_tag,
            TagSimilarity.cooccurrence_count >= min_cooccurrence_count,
        )
    ).scalar_one_or_none()


def get_max_related_similarity_for_unknown_tags(
    db,
    liked_tags: list[str],
    unknown_tags: list[str],
    min_cooccurrence_count: int = 2,
):
    if not liked_tags or not unknown_tags:
        return {}

    rows = db.execute(
        select(
            TagSimilarity.related_tag,
            func.max(TagSimilarity.jaccard_score),
        )
        .where(
            TagSimilarity.source_tag.in_(liked_tags),
            TagSimilarity.related_tag.in_(unknown_tags),
            TagSimilarity.cooccurrence_count >= min_cooccurrence_count,
        )
        .group_by(TagSimilarity.related_tag)
    ).all()

    return {related_tag: max_score for related_tag, max_score in rows}


def get_similarity_scores_for_tag_pairs(
    db,
    source_tags: list[str],
    related_tags: list[str],
    min_cooccurrence_count: int = 2,
):
    if not source_tags or not related_tags:
        return {}

    rows = db.execute(
        select(
            TagSimilarity.source_tag,
            TagSimilarity.related_tag,
            TagSimilarity.jaccard_score,
        )
        .where(
            TagSimilarity.source_tag.in_(source_tags),
            TagSimilarity.related_tag.in_(related_tags),
            TagSimilarity.cooccurrence_count >= min_cooccurrence_count,
        )
    ).all()

    return {
        (source_tag, related_tag): float(jaccard_score)
        for source_tag, related_tag, jaccard_score in rows
    }
