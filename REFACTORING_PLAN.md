# MTG MCP Server Refactoring Plan

## Overview

This document outlines structural improvements to make the MTG MCP Server more maintainable, type-safe, and production-ready. These improvements preserve all existing functionality while addressing code quality and architectural concerns.

## Current Issues Identified

### 1. Configuration Management
- **Problem**: Magic numbers scattered throughout codebase (75 batch size, Command Zone targets)
- **Impact**: Hard to maintain, test different configurations, or deploy with different settings
- **Files Affected**: `tools/scryfall_server.py`, `tools/analysis_server.py`

### 2. Type Safety Issues
- **Problem**: 21 mypy errors including missing Optional types, incorrect annotations
- **Impact**: Poor IDE support, potential runtime errors, harder to maintain
- **Files Affected**: `tools/utils.py`, `tools/analysis_server.py`

### 3. Cache Architecture
- **Problem**: Global dictionaries with no size limits, TTL, or persistence
- **Impact**: Memory could grow indefinitely, no cache invalidation strategy
- **Files Affected**: `tools/utils.py`

### 4. Error Handling Inconsistencies
- **Problem**: Different patterns across files (print vs return None vs raise)
- **Impact**: Inconsistent user experience, debugging difficulties
- **Files Affected**: All tool files

### 5. Missing Domain Models
- **Problem**: Using raw dictionaries for structured data
- **Impact**: No type safety for card data, harder to understand data flow
- **Files Affected**: All tool files

---

## Refactoring Plan

### Phase 1: Foundation (High Priority) 🔴

#### Task 1.1: Fix Type Annotations
**Estimated Time**: 2-3 hours

**Files to Update**:
- `tools/analysis_server.py` - Fix Optional parameter types
- `tools/utils.py` - Fix cache type annotations
- Add proper type imports

**Changes**:
```python
# Before
async def analyze_commander_deck(
    ramp: List[str] = None,
    card_advantage: List[str] = None,
    # ...
) -> str:

# After  
from typing import Optional, List

async def analyze_commander_deck(
    ramp: Optional[List[str]] = None,
    card_advantage: Optional[List[str]] = None,
    # ...
) -> str:
```

**Acceptance Criteria**:
- [ ] `uv run mypy tools/ --ignore-missing-imports` passes with 0 errors
- [ ] All existing tests still pass
- [ ] IDE provides proper type hints and autocomplete

#### Task 1.2: Create Configuration Module
**Estimated Time**: 2-3 hours

**New File**: `config.py`

**Structure**:
```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class ScryfallConfig:
    api_base: str = "https://api.scryfall.com"
    batch_size: int = 75
    request_timeout: int = 30
    max_retries: int = 3

@dataclass 
class CommandZoneConfig:
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
    max_card_cache_size: int = 10000
    max_search_cache_size: int = 1000
    ttl_seconds: int = 3600
    enable_persistence: bool = False

@dataclass
class ServerConfig:
    scryfall: ScryfallConfig = ScryfallConfig()
    command_zone: CommandZoneConfig = CommandZoneConfig()
    cache: CacheConfig = CacheConfig()
```

**Files to Update**:
- `tools/scryfall_server.py` - Import and use `config.scryfall.batch_size`
- `tools/analysis_server.py` - Import and use `config.command_zone.*`
- `tools/utils.py` - Import and use `config.scryfall.api_base`

**Acceptance Criteria**:
- [ ] No magic numbers remain in tool files
- [ ] Configuration is centralized and easily modifiable
- [ ] All tests pass with new configuration system

### Phase 2: Cache Architecture (High Priority) 🔴

#### Task 2.1: Implement Proper Cache Classes
**Estimated Time**: 3-4 hours

**New File**: `cache.py`

**Structure**:
```python
from typing import Dict, Any, Optional, Generic, TypeVar
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

T = TypeVar('T')

class CacheInterface(ABC, Generic[T]):
    @abstractmethod
    def get(self, key: str) -> Optional[T]: ...
    
    @abstractmethod
    def set(self, key: str, value: T) -> None: ...
    
    @abstractmethod
    def clear(self) -> None: ...

class TTLCache(CacheInterface[T]):
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self._cache: Dict[str, T] = {}
        self._timestamps: Dict[str, datetime] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[T]:
        if self._is_expired(key):
            self._remove(key)
            return None
        return self._cache.get(key)
    
    def set(self, key: str, value: T) -> None:
        self._cleanup_if_needed()
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
    
    def _is_expired(self, key: str) -> bool:
        if key not in self._timestamps:
            return True
        return datetime.now() - self._timestamps[key] > self.ttl
    
    def _cleanup_if_needed(self) -> None:
        if len(self._cache) >= self.max_size:
            # Remove oldest entries
            oldest_keys = sorted(
                self._timestamps.keys(),
                key=lambda k: self._timestamps[k]
            )[:self.max_size // 4]  # Remove 25% when full
            for key in oldest_keys:
                self._remove(key)
    
    def _remove(self, key: str) -> None:
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

# Global cache instances
card_cache: TTLCache[Dict[str, Any]] = TTLCache(max_size=10000)
search_cache: TTLCache[Dict[str, Any]] = TTLCache(max_size=1000)
```

**Files to Update**:
- `tools/utils.py` - Replace global dicts with TTLCache instances
- Update all cache usage to use `.get()` and `.set()` methods

**Acceptance Criteria**:
- [ ] Cache has configurable size limits and TTL
- [ ] Memory usage is bounded
- [ ] Cache performance is maintained or improved
- [ ] All tests pass

#### Task 2.2: Add Cache Metrics and Monitoring
**Estimated Time**: 1-2 hours

**Enhancements**:
- Add hit/miss ratio tracking
- Add cache size monitoring
- Optional cache statistics endpoint

### Phase 3: Error Handling (Medium Priority) 🟡

#### Task 3.1: Create Error Handling Module
**Estimated Time**: 2-3 hours

**New File**: `errors.py`

**Structure**:
```python
import logging
from enum import Enum
from typing import Optional, Any
from contextlib import asynccontextmanager

class ErrorLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MTGServerError(Exception):
    """Base exception for MTG Server errors"""
    pass

class ScryfallAPIError(MTGServerError):
    """Scryfall API related errors"""
    pass

class CacheError(MTGServerError):
    """Cache related errors"""
    pass

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@asynccontextmanager
async def handle_api_errors(context: str):
    """Context manager for consistent API error handling"""
    try:
        yield
    except httpx.HTTPError as e:
        logging.error(f"HTTP error in {context}: {e}")
        raise ScryfallAPIError(f"API request failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in {context}: {e}")
        raise MTGServerError(f"Operation failed: {e}")

def log_performance(func_name: str, duration: float, cache_hit: bool = False) -> None:
    """Log performance metrics"""
    cache_status = "HIT" if cache_hit else "MISS"
    logging.info(f"{func_name} completed in {duration:.3f}s [CACHE {cache_status}]")
```

**Files to Update**:
- All tool files to use consistent error handling
- Replace print statements with proper logging
- Wrap API calls with error context managers

**Acceptance Criteria**:
- [ ] Consistent error handling across all modules
- [ ] Proper logging instead of print statements
- [ ] Error context is preserved and helpful
- [ ] All tests pass

### Phase 4: Domain Models (Medium Priority) 🟡

#### Task 4.1: Create Card and Deck Models
**Estimated Time**: 2-3 hours

**New File**: `models.py`

**Structure**:
```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class CardType(Enum):
    CREATURE = "Creature"
    INSTANT = "Instant"
    SORCERY = "Sorcery"
    ARTIFACT = "Artifact"
    ENCHANTMENT = "Enchantment"
    PLANESWALKER = "Planeswalker"
    LAND = "Land"
    BATTLE = "Battle"

class CommandZoneCategory(Enum):
    RAMP = "ramp"
    CARD_ADVANTAGE = "card_advantage"
    TARGETED_DISRUPTION = "targeted_disruption"
    MASS_DISRUPTION = "mass_disruption"
    LANDS = "lands"
    PLAN_CARDS = "plan_cards"

@dataclass
class Card:
    name: str
    mana_cost: Optional[str] = None
    type_line: Optional[str] = None
    oracle_text: Optional[str] = None
    cmc: Optional[float] = None
    color_identity: Optional[List[str]] = None
    prices: Optional[Dict[str, str]] = None
    
    @property
    def primary_types(self) -> List[CardType]:
        """Extract primary card types from type line"""
        if not self.type_line:
            return []
        types = []
        for card_type in CardType:
            if card_type.value.lower() in self.type_line.lower():
                types.append(card_type)
        return types
    
    @classmethod
    def from_scryfall_data(cls, data: Dict[str, Any]) -> 'Card':
        """Create Card instance from Scryfall API response"""
        return cls(
            name=data.get("name", ""),
            mana_cost=data.get("mana_cost"),
            type_line=data.get("type_line"),
            oracle_text=data.get("oracle_text"),
            cmc=data.get("cmc"),
            color_identity=data.get("color_identity"),
            prices=data.get("prices")
        )

@dataclass
class CommanderDeckAnalysis:
    categories: Dict[CommandZoneCategory, List[str]]
    total_cards: int
    balance_score: float
    efficiency_notes: List[str]
    problem_categories: List[str]
    
    @property
    def is_balanced(self) -> bool:
        """Check if deck meets minimum Command Zone requirements"""
        return self.balance_score >= 0.8

@dataclass
class SearchResult:
    cards: List[Card]
    total_found: int
    query: str
    cached: bool = False
```

**Files to Update**:
- `tools/utils.py` - Use Card model instead of raw dicts
- `tools/analysis_server.py` - Use CommanderDeckAnalysis model
- `tools/scryfall_server.py` - Use Card and SearchResult models

**Acceptance Criteria**:
- [ ] Type safety for all card data operations
- [ ] Clear data structures for complex operations
- [ ] Easy conversion between API responses and models
- [ ] All tests pass

### Phase 5: Testing and Documentation (Low Priority) 🟢

#### Task 5.1: Add Integration Tests for New Components
**Estimated Time**: 2-3 hours

**New Files**:
- `tests/test_config.py`
- `tests/test_cache.py` 
- `tests/test_errors.py`
- `tests/test_models.py`

#### Task 5.2: Update Documentation
**Estimated Time**: 1-2 hours

**Files to Update**:
- `CLAUDE.md` - Document new architecture
- `README.md` - Update setup and usage instructions
- Add docstrings to new modules

---

## Implementation Strategy

### Session 1: Foundation
- Complete Phase 1 (type annotations + configuration)
- Verify all tests pass
- Update CI if needed

### Session 2: Cache Architecture  
- Complete Phase 2 (cache implementation)
- Performance testing
- Memory usage validation

### Session 3: Polish
- Complete Phase 3 (error handling)
- Complete Phase 4 (domain models) 
- Complete Phase 5 (testing + docs)

## Risk Assessment

### Low Risk ✅
- Type annotations (compile-time only)
- Configuration module (pure addition)
- Error handling improvements

### Medium Risk ⚠️
- Cache architecture changes (affects performance)
- Domain models (changes data flow)

### Mitigation Strategies
- Maintain existing public APIs during refactoring
- Run full test suite after each phase
- Performance benchmarking for cache changes
- Feature flags for new error handling

## Success Criteria

- [ ] All mypy type checking passes
- [ ] All existing tests continue to pass
- [ ] Performance is maintained or improved
- [ ] Memory usage is bounded and predictable
- [ ] Code is more maintainable and readable
- [ ] New features can be added more easily

---

## Notes for Next Session

1. Start with Task 1.1 (type annotations) as it has the highest impact
2. Consider adding performance benchmarks before major cache changes
3. Keep backward compatibility during refactoring
4. Update CLAUDE.md to reflect new architecture decisions