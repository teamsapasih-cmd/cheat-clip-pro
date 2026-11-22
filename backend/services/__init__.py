"""Lazy service exports.

Importing a focused service (for example, retention or persistence) must not
eagerly load the full AI, downloader, renderer, and system dependency graph.
Public names remain available for backwards compatibility.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

_SERVICE_EXPORTS = {
    "KNOWN_FLASH_MODELS": ("backend.services.ai_service", "KNOWN_FLASH_MODELS"),
    "get_flash_models_for_key": ("backend.services.ai_service", "get_flash_models_for_key"),
    "list_available_gemini_models": ("backend.services.ai_service", "list_available_gemini_models"),
    "parse_gemini_model_sort_key": ("backend.services.ai_service", "parse_gemini_model_sort_key"),
    "raw_clip_download_jobs": ("backend.services.download_service", "raw_clip_download_jobs"),
    "raw_download_jobs": ("backend.services.download_service", "raw_download_jobs"),
    "run_raw_clip_download_job": ("backend.services.download_service", "run_raw_clip_download_job"),
    "run_raw_download_job": ("backend.services.download_service", "run_raw_download_job"),
    "BATCH_REQUESTS": ("backend.services.render_service", "BATCH_REQUESTS"),
    "RENDER_BATCHES": ("backend.services.render_service", "RENDER_BATCHES"),
    "process_batch_rendering": ("backend.services.render_service", "process_batch_rendering"),
    "process_batch_retry": ("backend.services.render_service", "process_batch_retry"),
    "render_single_batch_clip": ("backend.services.render_service", "render_single_batch_clip"),
    "update_batch_summary_and_zip": ("backend.services.render_service", "update_batch_summary_and_zip"),
    "auto_cleanup_expired_files": ("backend.services.system_service", "auto_cleanup_expired_files"),
    "clear_temp_files": ("backend.services.system_service", "clear_temp_files"),
    "get_current_git_info": ("backend.services.system_service", "get_current_git_info"),
    "get_dir_size_and_count": ("backend.services.system_service", "get_dir_size_and_count"),
    "get_temp_storage_summary": ("backend.services.system_service", "get_temp_storage_summary"),
    "run_git_command": ("backend.services.system_service", "run_git_command"),
    "trigger_detached_restart": ("backend.services.system_service", "trigger_detached_restart"),
    "check_single_supadata_key": ("backend.services.youtube_service", "check_single_supadata_key"),
    "download_youtube_audio_file": ("backend.services.youtube_service", "download_youtube_audio_file"),
    "fetch_transcript": ("backend.services.youtube_service", "fetch_transcript"),
    "fetch_transcript_cli": ("backend.services.youtube_service", "fetch_transcript_cli"),
    "fetch_transcript_supadata": ("backend.services.youtube_service", "fetch_transcript_supadata"),
    "fetch_transcript_ytdlp": ("backend.services.youtube_service", "fetch_transcript_ytdlp"),
    "fetch_video_metadata": ("backend.services.youtube_service", "fetch_video_metadata"),
    "get_supadata_keys": ("backend.services.youtube_service", "get_supadata_keys"),
    "get_supadata_usage_data": ("backend.services.youtube_service", "get_supadata_usage_data"),
    "get_youtube_oembed_title": ("backend.services.youtube_service", "get_youtube_oembed_title"),
    "normalize_transcript": ("backend.services.youtube_service", "normalize_transcript"),
}

__all__ = list(_SERVICE_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _SERVICE_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
