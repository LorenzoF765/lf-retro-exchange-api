# HATEOAS link generation for a gaming platform API. Coded by Lorenzo Franco with copilot assisting in adding these comments afterwards.

from urllib.parse import urlencode

def link(href: str, method: str | None = None) -> dict:
    """Create a link dict with optional HTTP method."""
    d = {"href": href}
    if method:
        d["method"] = method
    return d

def user_links(user_id: int, is_self: bool) -> dict:
    """Generate HATEOAS links for a user resource based on viewer permissions."""
    links = {
        "self": link(f"/api/users/{user_id}"),
        "games": link(f"/api/games?ownerId={user_id}"),
        "search_games": link("/api/games"),
    }
    if is_self:
        # When the viewer is the same user, expose update and create endpoints.
        links["update"] = link(f"/api/users/{user_id}", "PUT")
        links["create_game"] = link("/api/games", "POST")
    return links

def game_links(game_id: int, owner_id: int, can_modify: bool) -> dict:
    """Generate HATEOAS links for a game resource, including modify operations if allowed."""
    links = {
        "self": link(f"/api/games/{game_id}"),
        "owner": link(f"/api/users/{owner_id}"),
        "collection": link("/api/games"),
        "search": link("/api/games"),
    }
    if can_modify:
        links["update"] = link(f"/api/games/{game_id}", "PUT")
        links["delete"] = link(f"/api/games/{game_id}", "DELETE")
    return links

def games_collection_links(page: int, page_size: int, total: int, query_params: dict, can_create: bool) -> dict:
    """Build pagination links (self, next, prev) and an optional create link."""
    def url_for(p: int) -> str:
        qp = dict(query_params)
        qp["page"] = p
        qp["pageSize"] = page_size
        return "/api/games?" + urlencode(qp)

    links = {"self": link(url_for(page))}

    # Compute last page and conditionally include next/prev links.
    max_page = max(1, (total + page_size - 1) // page_size)
    if page < max_page:
        links["next"] = link(url_for(page + 1))
    if page > 1:
        links["prev"] = link(url_for(page - 1))
    if can_create:
        links["create"] = link("/api/games", "POST")
    return links
