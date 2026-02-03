-- Graph Memory Persistence - February 3, 2026

CREATE TABLE IF NOT EXISTS memory.graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID REFERENCES memory.entries(id) ON DELETE CASCADE,
    node_type VARCHAR(100) NOT NULL,
    node_label VARCHAR(255),
    properties JSONB DEFAULT '{}',
    importance_score FLOAT DEFAULT 1.0,
    decay_rate FLOAT DEFAULT 0.01,
    last_reinforced_at TIMESTAMPTZ DEFAULT NOW(),
    position JSONB DEFAULT '{"x": 0, "y": 0, "z": 0}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_entry ON memory.graph_nodes(entry_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON memory.graph_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_importance ON memory.graph_nodes(importance_score DESC);

CREATE TABLE IF NOT EXISTS memory.graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id UUID NOT NULL REFERENCES memory.graph_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES memory.graph_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    relationship_label VARCHAR(255),
    weight FLOAT DEFAULT 1.0 CHECK (weight >= 0),
    bidirectional BOOLEAN DEFAULT FALSE,
    properties JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 1.0,
    decay_rate FLOAT DEFAULT 0.01,
    last_traversed_at TIMESTAMPTZ,
    traversal_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(from_node_id, to_node_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_from ON memory.graph_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_to ON memory.graph_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON memory.graph_edges(relationship_type);

CREATE TABLE IF NOT EXISTS memory.graph_traversals (
    id SERIAL PRIMARY KEY,
    query_id UUID,
    query_text TEXT,
    path_nodes UUID[] NOT NULL,
    path_edges UUID[] NOT NULL,
    success BOOLEAN,
    result_relevance FLOAT,
    traversal_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.graph_communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_name VARCHAR(255),
    community_type VARCHAR(50),
    member_node_ids UUID[] NOT NULL,
    cohesion_score FLOAT,
    size INTEGER,
    properties JSONB DEFAULT '{}',
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION memory.add_graph_node(p_entry_id UUID, p_node_type VARCHAR, p_node_label VARCHAR DEFAULT NULL, p_properties JSONB DEFAULT '{}') RETURNS UUID AS $$ DECLARE v_node_id UUID; BEGIN INSERT INTO memory.graph_nodes (entry_id, node_type, node_label, properties) VALUES (p_entry_id, p_node_type, p_node_label, p_properties) ON CONFLICT DO NOTHING RETURNING id INTO v_node_id; RETURN v_node_id; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION memory.add_graph_edge(p_from_node_id UUID, p_to_node_id UUID, p_relationship_type VARCHAR, p_weight FLOAT DEFAULT 1.0, p_bidirectional BOOLEAN DEFAULT FALSE, p_properties JSONB DEFAULT '{}') RETURNS UUID AS $$ DECLARE v_edge_id UUID; BEGIN INSERT INTO memory.graph_edges (from_node_id, to_node_id, relationship_type, weight, bidirectional, properties) VALUES (p_from_node_id, p_to_node_id, p_relationship_type, p_weight, p_bidirectional, p_properties) ON CONFLICT (from_node_id, to_node_id, relationship_type) DO UPDATE SET weight = EXCLUDED.weight, properties = memory.graph_edges.properties || EXCLUDED.properties RETURNING id INTO v_edge_id; IF p_bidirectional THEN INSERT INTO memory.graph_edges (from_node_id, to_node_id, relationship_type, weight, bidirectional, properties) VALUES (p_to_node_id, p_from_node_id, p_relationship_type, p_weight, TRUE, p_properties) ON CONFLICT DO NOTHING; END IF; RETURN v_edge_id; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION memory.decay_graph_nodes(p_age_hours INTEGER DEFAULT 24) RETURNS INTEGER AS $$ DECLARE updated_count INTEGER; BEGIN UPDATE memory.graph_nodes SET importance_score = importance_score * (1 - decay_rate), updated_at = NOW() WHERE last_reinforced_at < NOW() - (p_age_hours || ' hours')::INTERVAL AND importance_score > 0.01; GET DIAGNOSTICS updated_count = ROW_COUNT; RETURN updated_count; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION memory.reinforce_node(p_node_id UUID) RETURNS VOID AS $$ BEGIN UPDATE memory.graph_nodes SET importance_score = LEAST(importance_score * 1.1, 10.0), last_reinforced_at = NOW() WHERE id = p_node_id; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE VIEW memory.node_degree_stats AS SELECT n.id as node_id, n.node_type, n.importance_score, COUNT(DISTINCT e_out.id) as out_degree, COUNT(DISTINCT e_in.id) as in_degree FROM memory.graph_nodes n LEFT JOIN memory.graph_edges e_out ON e_out.from_node_id = n.id LEFT JOIN memory.graph_edges e_in ON e_in.to_node_id = n.id GROUP BY n.id, n.node_type, n.importance_score;

COMMENT ON TABLE memory.graph_nodes IS 'Nodes in the knowledge graph with importance tracking';
COMMENT ON TABLE memory.graph_edges IS 'Edges connecting graph nodes with traversal statistics';
