"""Playback timing shared by the election source and broadcaster."""

NORMAL_REPLAY_SECONDS = 600
REPLAY_INTERVALS = 30
PLAYBACK_SPEEDS = {"1", "4", "6"}


def seconds_between_snapshots(speed: str) -> float:
    return NORMAL_REPLAY_SECONDS / REPLAY_INTERVALS / int(speed)
