"""Configuration module for MTG MCP Server."""

from dataclasses import dataclass, field

@dataclass
class ScryfallConfig:
    """Configuration for Scryfall API interactions."""
    api_base: str = "https://api.scryfall.com"
    batch_size: int = 75
    request_timeout: int = 30
    max_retries: int = 3

@dataclass 
class CommandZoneConfig:
    """Configuration for Command Zone deckbuilding template."""
    ramp_target: int = 10
    ramp_optimal: int = 12
    card_advantage_target: int = 12
    card_advantage_optimal: int = 15
    targeted_disruption_target: int = 12
    mass_disruption_target: int = 6
    lands_target: int = 38
    plan_cards_target: int = 30

@dataclass
class CacheConfig:
    """Configuration for caching behavior."""
    max_card_cache_size: int = 10000
    max_search_cache_size: int = 1000
    ttl_seconds: int = 3600
    enable_persistence: bool = False

@dataclass
class ServerConfig:
    """Main server configuration combining all subsystem configs."""
    scryfall: ScryfallConfig = field(default_factory=ScryfallConfig)
    command_zone: CommandZoneConfig = field(default_factory=CommandZoneConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

# Global configuration instance
config = ServerConfig()