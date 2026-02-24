from __future__ import annotations

from collections.abc import Callable


MAX_CHAIN_DEPTH = 8


class MalFranchiseResolver:
    def __init__(self, node_loader: Callable[[list[int]], dict[int, dict[str, object]]]) -> None:
        self._node_loader = node_loader
        self._nodes_by_mal_id: dict[int, dict[str, object]] = {}
        self._missing_mal_ids: set[int] = set()

    def resolve_entrypoint(self, mal_id: int) -> int:
        chain = self._collect_prequel_sequel_chain(mal_id)
        if not chain:
            return mal_id

        best_id = mal_id
        best_score: tuple[int, int, int, int, int] | None = None
        for candidate_id in chain:
            details = self._get_node(candidate_id)
            candidate_score = self._entrypoint_priority(details)
            if best_score is None or candidate_score > best_score:
                best_score = candidate_score
                best_id = candidate_id

        return best_id

    def _collect_prequel_sequel_chain(self, start_mal_id: int) -> set[int]:
        seen: set[int] = set()
        stack: list[tuple[int, int]] = [(start_mal_id, 0)]

        while stack:
            current_id, depth = stack.pop()
            if current_id in seen:
                continue
            seen.add(current_id)
            if depth >= MAX_CHAIN_DEPTH:
                continue

            for related_id in self._related_ids(current_id):
                if related_id not in seen:
                    stack.append((related_id, depth + 1))

        return seen

    def _related_ids(self, mal_id: int) -> list[int]:
        node = self._get_node(mal_id)
        related = node.get("related_prequel_sequel_mal_ids")
        if not isinstance(related, list):
            return []
        return [value for value in related if isinstance(value, int)]

    def _get_node(self, mal_id: int) -> dict[str, object]:
        if mal_id in self._nodes_by_mal_id:
            return self._nodes_by_mal_id[mal_id]
        if mal_id in self._missing_mal_ids:
            return {}

        loaded = self._node_loader([mal_id])
        self._nodes_by_mal_id.update(loaded)
        if mal_id not in self._nodes_by_mal_id:
            self._missing_mal_ids.add(mal_id)
            return {}
        return self._nodes_by_mal_id[mal_id]

    def _entrypoint_priority(self, details: dict[str, object]) -> tuple[int, int, int, int, int]:
        raw_type = details.get("anime_type")
        anime_type = getattr(raw_type, "value", raw_type)
        anime_type = str(anime_type or "").strip().lower()

        popularity = details.get("provider_popularity_rank")
        members = details.get("provider_member_count")
        year = details.get("start_year")
        mal_id = details.get("provider_anime_id")

        type_rank_map = {
            "tv": 6,
            "ona": 4,
            "ova": 3,
            "movie": 2,
            "special": 1,
            "music": 0,
        }
        type_rank = type_rank_map.get(anime_type, 0)

        # Prefer earlier entries in a franchise chain so sequels collapse to the
        # franchise starting point (e.g. season 3 -> season 1) when relation
        # links are available.
        if isinstance(year, int) and year > 1900:
            year_rank = -year
        else:
            year_rank = -10**9

        # Lower MAL popularity rank is better, so invert it.
        if isinstance(popularity, int) and popularity > 0:
            popularity_rank = -popularity
        else:
            popularity_rank = -10**9

        if isinstance(members, int) and members > 0:
            members_rank = members
        else:
            members_rank = -1

        # Final deterministic tiebreaker: prefer lower MAL id (typically older entry).
        mal_id_rank = -mal_id if isinstance(mal_id, int) and mal_id > 0 else -10**9

        return (type_rank, year_rank, popularity_rank, members_rank, mal_id_rank)
