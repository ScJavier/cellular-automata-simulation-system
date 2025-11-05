-- schema_setup.sql
-- Ejecutado automáticamente por PostgreSQL al iniciar el contenedor

CREATE SCHEMA IF NOT EXISTS raw_data;

CREATE TABLE IF NOT EXISTS raw_data.experiments (
    experiment_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    board_size INTEGER NOT NULL,
    num_steps INTEGER NOT NULL,
    initial_config TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC,
    status VARCHAR(50) DEFAULT 'RUNNING',
    rules_notation VARCHAR(50) NOT NULL,
    survival_rules VARCHAR(20),
    birth_rules VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS raw_data.generation_trace (
    trace_id BIGSERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    generation_num INTEGER NOT NULL,
    capture_time TIMESTAMP WITH TIME ZONE NOT NULL,
    board_state TEXT NOT NULL,
    live_cells_count INTEGER,
    
    CONSTRAINT fk_experiment
        FOREIGN KEY (experiment_id) 
        REFERENCES raw_data.experiments (experiment_id)
        ON DELETE CASCADE,
    
    CONSTRAINT uq_generation_in_experiment
        UNIQUE (experiment_id, generation_num)
);