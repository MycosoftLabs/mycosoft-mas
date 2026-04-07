-- Migration 025: Palace Topology
-- Created: April 7, 2026
-- Adds spatial memory organization (wings/rooms/tunnels) to MYCA memory palace

-- Palace wings (top-level domain containers)
CREATE TABLE IF NOT EXISTS mindex.palace_wings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    source_type TEXT DEFAULT 'custom',
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Palace rooms (topics within wings)
CREATE TABLE IF NOT EXISTS mindex.palace_rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wing_id UUID REFERENCES mindex.palace_wings(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    drawer_count INTEGER DEFAULT 0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(wing_id, name)
);

-- Palace tunnels (cross-wing connections)
CREATE TABLE IF NOT EXISTS mindex.palace_tunnels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_name TEXT NOT NULL,
    wing_a UUID REFERENCES mindex.palace_wings(id) ON DELETE CASCADE,
    wing_b UUID REFERENCES mindex.palace_wings(id) ON DELETE CASCADE,
    strength FLOAT DEFAULT 1.0,
    discovered_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(room_name, wing_a, wing_b)
);

-- Add palace metadata columns to existing memory_entries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mindex' AND table_name = 'memory_entries'
        AND column_name = 'wing'
    ) THEN
        ALTER TABLE mindex.memory_entries
            ADD COLUMN wing TEXT,
            ADD COLUMN room TEXT,
            ADD COLUMN hall TEXT,
            ADD COLUMN is_closet BOOLEAN DEFAULT false,
            ADD COLUMN closet_source_id UUID;
    END IF;
END $$;

-- Indexes for palace queries
CREATE INDEX IF NOT EXISTS idx_memory_wing_room ON mindex.memory_entries(wing, room);
CREATE INDEX IF NOT EXISTS idx_memory_hall ON mindex.memory_entries(hall);
CREATE INDEX IF NOT EXISTS idx_memory_is_closet ON mindex.memory_entries(is_closet) WHERE is_closet = true;
CREATE INDEX IF NOT EXISTS idx_palace_rooms_wing ON mindex.palace_rooms(wing_id);
CREATE INDEX IF NOT EXISTS idx_palace_tunnels_wings ON mindex.palace_tunnels(wing_a, wing_b);
