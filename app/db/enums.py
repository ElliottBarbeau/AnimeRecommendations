import enum

class Provider(enum.StrEnum):
    MAL = "mal"
    ANILIST = "anilist"

class AnimeStatus(enum.StrEnum):
    COMPLETED = "completed"
    AIRING = "airing"
    ANNOUNCED = "announced"

class EntryStatus(enum.StrEnum):
    WATCHING = "watching"
    WATCHED = "watched"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
    PLAN_TO_WATCH = "plan_to_watch"

class AnimeType(enum.StrEnum):
    OVA = "ova"
    TV = "tv"
    ONA = "ona"
    MOVIE = "movie"
    SPECIAL = "special"
    MUSIC = "music"
    UNKNOWN = "unknown"