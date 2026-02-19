import enum

class Provider(enum.StrEnum):
    MAL = "mal"
    ANILIST = "anilist"

class AnimeStatus(enum.StrEnum):
    COMPLETED = "completed"
    AIRING = "airing"
    ANNOUNCED = "announced"

class EntryStatus(enum.StrEnum):
    WATCHED = "watched"
    WATCHING = "watching"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
    PLAN_TO_WATCH = "plan_to_watch"

class AnimeType(enum.StrEnum):
    TV = "tv"
    OVA = "ova"
    ONA = "ona"
    MOVIE = "movie"
    SPECIAL = "special"
    MUSIC = "music"
    UNKNOWN = "unknown"