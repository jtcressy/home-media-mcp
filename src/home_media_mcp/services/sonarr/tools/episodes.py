"""Sonarr episode management tools."""

from typing import Annotated, Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import full_detail, grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_episodes(
    series_id: Annotated[int, "The Sonarr series ID"],
    season_number: Annotated[int | None, "Filter to a specific season number"] = None,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List episodes for a series, optionally filtered by season.

    Returns summary information for each episode. Use describe_episode
    with an ID for full details.
    """
    api = sonarr.EpisodeApi(client)
    kwargs: dict[str, Any] = {"series_id": series_id}
    if season_number is not None:
        kwargs["season_number"] = season_number
    episodes = await sonarr_api_call(api.list_episode, **kwargs)
    filtered = grep_filter(episodes, grep)
    return summarize_list(filtered, summary_fn=_sonarr_episode_summary)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_episode(
    id: Annotated[int, "The Sonarr episode ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get full details for a specific episode by ID."""
    api = sonarr.EpisodeApi(client)
    try:
        result = await sonarr_api_call(api.get_episode_by_id, id=id)
    except sonarr.NotFoundException:
        return {"error": "not_found", "message": f"Episode with ID {id} not found."}
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_monitor_episodes(
    episode_ids: Annotated[list[int], "List of episode IDs to update"],
    monitored: Annotated[bool, "Whether episodes should be monitored"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Set the monitored status for one or more episodes.

    Pass a list of episode IDs and whether they should be monitored.
    """
    api = sonarr.EpisodeApi(client)
    resource = sonarr.EpisodesMonitorResource(
        episode_ids=episode_ids, monitored=monitored
    )
    await sonarr_api_call(api.put_episode_monitor, episodes_monitor_resource=resource)
    return {
        "success": True,
        "message": f"{'Monitored' if monitored else 'Unmonitored'} {len(episode_ids)} episode(s).",
    }


def _sonarr_episode_summary(items: list) -> dict[str, Any]:
    """Generate aggregate stats for episode list summary."""
    monitored = sum(1 for e in items if getattr(e, "monitored", False))
    has_file = sum(1 for e in items if getattr(e, "has_file", False))
    return {
        "monitored": monitored,
        "unmonitored": len(items) - monitored,
        "downloaded": has_file,
        "missing": len(items) - has_file,
    }
