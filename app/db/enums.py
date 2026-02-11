import enum

class Provider(enum.StrEnum):
    MAL = "mal"
    ANILIST = "anilist"

class Status(enum.StrEnum):
    COMPLETED = "completed"
    AIRING = "airing"
    ANNOUNCED = "announced"

class AnimeType(enum.StrEnum):
    OVA = "ova"
    TV = "tv"
    ONA = "ona"
    MOVIE = "movie"
    SPECIAL = "special"
    MUSIC = "music"
    UNKNOWN = "unknown"