--
-- PostgreSQL database dump
--

\restrict I9GoJwT37IgqmHA1e3CWj8atcU1qANSa0iRHOTtWapGrYXscRQZtK04wkAqOvnM

-- Dumped from database version 17.9 (Debian 17.9-1.pgdg12+1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: app; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA app;


--
-- Name: cortex; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA cortex;


--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA extensions;


--
-- Name: house; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA house;


--
-- Name: scribe; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA scribe;


--
-- Name: test_app; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA test_app;


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: chats; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.chats (
    id text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    data jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: TABLE chats; Type: COMMENT; Schema: app; Owner: -
--

COMMENT ON TABLE app.chats IS 'Chat metadata for Alpha-App. Replaces Redis alpha:chat:* hashes.';


--
-- Name: COLUMN chats.id; Type: COMMENT; Schema: app; Owner: -
--

COMMENT ON COLUMN app.chats.id IS 'URL-safe nanoid (12 chars, ~72 bits of entropy)';


--
-- Name: COLUMN chats.updated_at; Type: COMMENT; Schema: app; Owner: -
--

COMMENT ON COLUMN app.chats.updated_at IS 'Last activity timestamp. Used for sidebar ordering.';


--
-- Name: COLUMN chats.data; Type: COMMENT; Schema: app; Owner: -
--

COMMENT ON COLUMN app.chats.data IS 'Flexible JSONB blob: session_uuid, title, created_at, token_count, context_window, etc.';


--
-- Name: events; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.events (
    id bigint NOT NULL,
    chat_id text NOT NULL,
    event jsonb NOT NULL,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    seq integer
);


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: app; Owner: -
--

CREATE SEQUENCE app.events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: app; Owner: -
--

ALTER SEQUENCE app.events_id_seq OWNED BY app.events.id;


--
-- Name: jobs; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.jobs (
    id text NOT NULL,
    job_type text NOT NULL,
    fire_at timestamp with time zone NOT NULL,
    kwargs jsonb DEFAULT '{}'::jsonb
);


--
-- Name: messages; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.messages (
    chat_id text NOT NULL,
    ordinal integer NOT NULL,
    role text NOT NULL,
    data jsonb NOT NULL
);


--
-- Name: reflection_flags; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.reflection_flags (
    id bigint NOT NULL,
    chat_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    note text NOT NULL,
    claimed boolean DEFAULT false NOT NULL
);


--
-- Name: reflection_flags_id_seq; Type: SEQUENCE; Schema: app; Owner: -
--

CREATE SEQUENCE app.reflection_flags_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reflection_flags_id_seq; Type: SEQUENCE OWNED BY; Schema: app; Owner: -
--

ALTER SEQUENCE app.reflection_flags_id_seq OWNED BY app.reflection_flags.id;


--
-- Name: solitude_program; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.solitude_program (
    id bigint NOT NULL,
    fire_at time without time zone NOT NULL,
    prompt text NOT NULL,
    recurring boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: solitude_program_id_seq; Type: SEQUENCE; Schema: app; Owner: -
--

CREATE SEQUENCE app.solitude_program_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solitude_program_id_seq; Type: SEQUENCE OWNED BY; Schema: app; Owner: -
--

ALTER SEQUENCE app.solitude_program_id_seq OWNED BY app.solitude_program.id;


--
-- Name: state; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.state (
    id integer DEFAULT 1 NOT NULL,
    data jsonb DEFAULT '{}'::jsonb NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT state_single_row CHECK ((id = 1))
);


--
-- Name: to_self_letter; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.to_self_letter (
    id integer DEFAULT 1 NOT NULL,
    letter text NOT NULL,
    written_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT to_self_single_row CHECK ((id = 1))
);


--
-- Name: today_summary; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.today_summary (
    id integer DEFAULT 1 NOT NULL,
    summary text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT single_row CHECK ((id = 1))
);


--
-- Name: capsules; Type: TABLE; Schema: cortex; Owner: -
--

CREATE TABLE cortex.capsules (
    id bigint NOT NULL,
    kind text NOT NULL,
    chat_id text,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT capsules_kind_check CHECK ((kind = ANY (ARRAY['day'::text, 'night'::text])))
);


--
-- Name: capsules_id_seq; Type: SEQUENCE; Schema: cortex; Owner: -
--

CREATE SEQUENCE cortex.capsules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: capsules_id_seq; Type: SEQUENCE OWNED BY; Schema: cortex; Owner: -
--

ALTER SEQUENCE cortex.capsules_id_seq OWNED BY cortex.capsules.id;


--
-- Name: context; Type: TABLE; Schema: cortex; Owner: -
--

CREATE TABLE cortex.context (
    id bigint NOT NULL,
    text text NOT NULL,
    tokens integer NOT NULL,
    embedding extensions.vector(2560),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: context_id_seq; Type: SEQUENCE; Schema: cortex; Owner: -
--

CREATE SEQUENCE cortex.context_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: context_id_seq; Type: SEQUENCE OWNED BY; Schema: cortex; Owner: -
--

ALTER SEQUENCE cortex.context_id_seq OWNED BY cortex.context.id;


--
-- Name: diary; Type: TABLE; Schema: cortex; Owner: -
--

CREATE TABLE cortex.diary (
    id bigint NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: diary_id_seq; Type: SEQUENCE; Schema: cortex; Owner: -
--

CREATE SEQUENCE cortex.diary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: diary_id_seq; Type: SEQUENCE OWNED BY; Schema: cortex; Owner: -
--

ALTER SEQUENCE cortex.diary_id_seq OWNED BY cortex.diary.id;


--
-- Name: memories; Type: TABLE; Schema: cortex; Owner: -
--

CREATE TABLE cortex.memories (
    id integer NOT NULL,
    content text NOT NULL,
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content)) STORED,
    embedding extensions.vector(768),
    forgotten boolean DEFAULT false,
    metadata jsonb DEFAULT '{}'::jsonb,
    embedding_qwen extensions.vector(2560),
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT content_not_empty CHECK ((char_length(content) > 0))
);


--
-- Name: memories_id_seq; Type: SEQUENCE; Schema: cortex; Owner: -
--

CREATE SEQUENCE cortex.memories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: memories_id_seq; Type: SEQUENCE OWNED BY; Schema: cortex; Owner: -
--

ALTER SEQUENCE cortex.memories_id_seq OWNED BY cortex.memories.id;


--
-- Name: summaries; Type: TABLE; Schema: cortex; Owner: -
--

CREATE TABLE cortex.summaries (
    id integer NOT NULL,
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    summary text NOT NULL,
    memory_count integer,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE summaries; Type: COMMENT; Schema: cortex; Owner: -
--

COMMENT ON TABLE cortex.summaries IS 'Capsule summaries: Alpha reflecting on time periods';


--
-- Name: COLUMN summaries.period_start; Type: COMMENT; Schema: cortex; Owner: -
--

COMMENT ON COLUMN cortex.summaries.period_start IS 'Start of the summarized period (inclusive)';


--
-- Name: COLUMN summaries.period_end; Type: COMMENT; Schema: cortex; Owner: -
--

COMMENT ON COLUMN cortex.summaries.period_end IS 'End of the summarized period (exclusive)';


--
-- Name: COLUMN summaries.summary; Type: COMMENT; Schema: cortex; Owner: -
--

COMMENT ON COLUMN cortex.summaries.summary IS 'Alpha''s reflection on this period, in her voice';


--
-- Name: COLUMN summaries.memory_count; Type: COMMENT; Schema: cortex; Owner: -
--

COMMENT ON COLUMN cortex.summaries.memory_count IS 'Number of memories included in the summary';


--
-- Name: summaries_id_seq; Type: SEQUENCE; Schema: cortex; Owner: -
--

CREATE SEQUENCE cortex.summaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: summaries_id_seq; Type: SEQUENCE OWNED BY; Schema: cortex; Owner: -
--

ALTER SEQUENCE cortex.summaries_id_seq OWNED BY cortex.summaries.id;


--
-- Name: memories; Type: TABLE; Schema: house; Owner: -
--

CREATE TABLE house.memories (
    id integer NOT NULL,
    content text NOT NULL,
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content)) STORED,
    embedding extensions.vector(768),
    metadata jsonb DEFAULT '{}'::jsonb,
    forgotten boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: memories_id_seq; Type: SEQUENCE; Schema: house; Owner: -
--

CREATE SEQUENCE house.memories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: memories_id_seq; Type: SEQUENCE OWNED BY; Schema: house; Owner: -
--

ALTER SEQUENCE house.memories_id_seq OWNED BY house.memories.id;


--
-- Name: messages; Type: TABLE; Schema: house; Owner: -
--

CREATE TABLE house.messages (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    role text NOT NULL,
    sender text,
    content text NOT NULL,
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content)) STORED,
    embedding extensions.vector(768),
    session_id text
);


--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: house; Owner: -
--

CREATE SEQUENCE house.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: house; Owner: -
--

ALTER SEQUENCE house.messages_id_seq OWNED BY house.messages.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: messages; Type: TABLE; Schema: scribe; Owner: -
--

CREATE TABLE scribe.messages (
    id bigint NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    embedding extensions.vector(768),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content)) STORED,
    session_id text,
    CONSTRAINT messages_role_check CHECK ((role = ANY (ARRAY['human'::text, 'assistant'::text])))
);


--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: scribe; Owner: -
--

CREATE SEQUENCE scribe.messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: scribe; Owner: -
--

ALTER SEQUENCE scribe.messages_id_seq OWNED BY scribe.messages.id;


--
-- Name: messages_pacific; Type: VIEW; Schema: scribe; Owner: -
--

CREATE VIEW scribe.messages_pacific AS
 SELECT id,
    ("timestamp" AT TIME ZONE 'America/Los_Angeles'::text) AS timestamp_pt,
    role,
    content,
    "left"(content, 100) AS preview
   FROM scribe.messages
  ORDER BY "timestamp";


--
-- Name: VIEW messages_pacific; Type: COMMENT; Schema: scribe; Owner: -
--

COMMENT ON VIEW scribe.messages_pacific IS 'Messages with timestamps in Pacific time for human reading';


--
-- Name: chats; Type: TABLE; Schema: test_app; Owner: -
--

CREATE TABLE test_app.chats (
    id text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    data jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: events id; Type: DEFAULT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.events ALTER COLUMN id SET DEFAULT nextval('app.events_id_seq'::regclass);


--
-- Name: reflection_flags id; Type: DEFAULT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.reflection_flags ALTER COLUMN id SET DEFAULT nextval('app.reflection_flags_id_seq'::regclass);


--
-- Name: solitude_program id; Type: DEFAULT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.solitude_program ALTER COLUMN id SET DEFAULT nextval('app.solitude_program_id_seq'::regclass);


--
-- Name: capsules id; Type: DEFAULT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.capsules ALTER COLUMN id SET DEFAULT nextval('cortex.capsules_id_seq'::regclass);


--
-- Name: context id; Type: DEFAULT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.context ALTER COLUMN id SET DEFAULT nextval('cortex.context_id_seq'::regclass);


--
-- Name: diary id; Type: DEFAULT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.diary ALTER COLUMN id SET DEFAULT nextval('cortex.diary_id_seq'::regclass);


--
-- Name: memories id; Type: DEFAULT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.memories ALTER COLUMN id SET DEFAULT nextval('cortex.memories_id_seq'::regclass);


--
-- Name: summaries id; Type: DEFAULT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.summaries ALTER COLUMN id SET DEFAULT nextval('cortex.summaries_id_seq'::regclass);


--
-- Name: memories id; Type: DEFAULT; Schema: house; Owner: -
--

ALTER TABLE ONLY house.memories ALTER COLUMN id SET DEFAULT nextval('house.memories_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: house; Owner: -
--

ALTER TABLE ONLY house.messages ALTER COLUMN id SET DEFAULT nextval('house.messages_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: scribe; Owner: -
--

ALTER TABLE ONLY scribe.messages ALTER COLUMN id SET DEFAULT nextval('scribe.messages_id_seq'::regclass);


--
-- Name: chats chats_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.chats
    ADD CONSTRAINT chats_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (chat_id, ordinal);


--
-- Name: reflection_flags reflection_flags_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.reflection_flags
    ADD CONSTRAINT reflection_flags_pkey PRIMARY KEY (id);


--
-- Name: solitude_program solitude_program_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.solitude_program
    ADD CONSTRAINT solitude_program_pkey PRIMARY KEY (id);


--
-- Name: state state_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.state
    ADD CONSTRAINT state_pkey PRIMARY KEY (id);


--
-- Name: to_self_letter to_self_letter_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.to_self_letter
    ADD CONSTRAINT to_self_letter_pkey PRIMARY KEY (id);


--
-- Name: today_summary today_summary_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.today_summary
    ADD CONSTRAINT today_summary_pkey PRIMARY KEY (id);


--
-- Name: capsules capsules_pkey; Type: CONSTRAINT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.capsules
    ADD CONSTRAINT capsules_pkey PRIMARY KEY (id);


--
-- Name: context context_pkey; Type: CONSTRAINT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.context
    ADD CONSTRAINT context_pkey PRIMARY KEY (id);


--
-- Name: diary diary_pkey; Type: CONSTRAINT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.diary
    ADD CONSTRAINT diary_pkey PRIMARY KEY (id);


--
-- Name: memories memories_pkey; Type: CONSTRAINT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.memories
    ADD CONSTRAINT memories_pkey PRIMARY KEY (id);


--
-- Name: summaries summaries_period_start_period_end_key; Type: CONSTRAINT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.summaries
    ADD CONSTRAINT summaries_period_start_period_end_key UNIQUE (period_start, period_end);


--
-- Name: summaries summaries_pkey; Type: CONSTRAINT; Schema: cortex; Owner: -
--

ALTER TABLE ONLY cortex.summaries
    ADD CONSTRAINT summaries_pkey PRIMARY KEY (id);


--
-- Name: memories memories_pkey; Type: CONSTRAINT; Schema: house; Owner: -
--

ALTER TABLE ONLY house.memories
    ADD CONSTRAINT memories_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: house; Owner: -
--

ALTER TABLE ONLY house.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: scribe; Owner: -
--

ALTER TABLE ONLY scribe.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: chats chats_pkey; Type: CONSTRAINT; Schema: test_app; Owner: -
--

ALTER TABLE ONLY test_app.chats
    ADD CONSTRAINT chats_pkey PRIMARY KEY (id);


--
-- Name: idx_chats_created_at; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX idx_chats_created_at ON app.chats USING btree (created_at);


--
-- Name: idx_chats_updated_at; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX idx_chats_updated_at ON app.chats USING btree (updated_at DESC);


--
-- Name: idx_events_chat_id; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX idx_events_chat_id ON app.events USING btree (chat_id);


--
-- Name: idx_events_chat_seq; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX idx_events_chat_seq ON app.events USING btree (chat_id, seq);


--
-- Name: idx_events_ts; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX idx_events_ts ON app.events USING btree (ts);


--
-- Name: idx_reflection_flags_chat_unclaimed; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX idx_reflection_flags_chat_unclaimed ON app.reflection_flags USING btree (chat_id, claimed);


--
-- Name: idx_solitude_program_fire_at; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX idx_solitude_program_fire_at ON app.solitude_program USING btree (fire_at);


--
-- Name: idx_capsules_kind_created; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_capsules_kind_created ON cortex.capsules USING btree (kind, created_at DESC);


--
-- Name: idx_context_created; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_context_created ON cortex.context USING btree (created_at DESC);


--
-- Name: idx_diary_created; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_diary_created ON cortex.diary USING btree (created_at DESC);


--
-- Name: idx_memories_created_at; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_memories_created_at ON cortex.memories USING btree (created_at);


--
-- Name: idx_memories_embedding; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_memories_embedding ON cortex.memories USING hnsw (embedding extensions.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_memories_embedding_qwen; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_memories_embedding_qwen ON cortex.memories USING hnsw (((embedding_qwen)::extensions.halfvec(2560)) extensions.halfvec_cosine_ops);


--
-- Name: idx_memories_metadata; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_memories_metadata ON cortex.memories USING gin (metadata);


--
-- Name: idx_memories_not_forgotten; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_memories_not_forgotten ON cortex.memories USING btree (id) WHERE (NOT forgotten);


--
-- Name: idx_memories_tsv; Type: INDEX; Schema: cortex; Owner: -
--

CREATE INDEX idx_memories_tsv ON cortex.memories USING gin (content_tsv);


--
-- Name: idx_house_memories_forgotten; Type: INDEX; Schema: house; Owner: -
--

CREATE INDEX idx_house_memories_forgotten ON house.memories USING btree (forgotten);


--
-- Name: idx_house_memories_tsv; Type: INDEX; Schema: house; Owner: -
--

CREATE INDEX idx_house_memories_tsv ON house.memories USING gin (content_tsv);


--
-- Name: idx_house_messages_dedup; Type: INDEX; Schema: house; Owner: -
--

CREATE UNIQUE INDEX idx_house_messages_dedup ON house.messages USING btree ("timestamp", role, md5(content));


--
-- Name: idx_house_messages_role; Type: INDEX; Schema: house; Owner: -
--

CREATE INDEX idx_house_messages_role ON house.messages USING btree (role);


--
-- Name: idx_house_messages_sender; Type: INDEX; Schema: house; Owner: -
--

CREATE INDEX idx_house_messages_sender ON house.messages USING btree (sender);


--
-- Name: idx_house_messages_session; Type: INDEX; Schema: house; Owner: -
--

CREATE INDEX idx_house_messages_session ON house.messages USING btree (session_id);


--
-- Name: idx_house_messages_timestamp; Type: INDEX; Schema: house; Owner: -
--

CREATE INDEX idx_house_messages_timestamp ON house.messages USING btree ("timestamp");


--
-- Name: idx_house_messages_tsv; Type: INDEX; Schema: house; Owner: -
--

CREATE INDEX idx_house_messages_tsv ON house.messages USING gin (content_tsv);


--
-- Name: idx_scribe_messages_dedup; Type: INDEX; Schema: scribe; Owner: -
--

CREATE UNIQUE INDEX idx_scribe_messages_dedup ON scribe.messages USING btree ("timestamp", role, md5(content));


--
-- Name: idx_scribe_messages_embedding; Type: INDEX; Schema: scribe; Owner: -
--

CREATE INDEX idx_scribe_messages_embedding ON scribe.messages USING hnsw (embedding extensions.vector_cosine_ops);


--
-- Name: idx_scribe_messages_session; Type: INDEX; Schema: scribe; Owner: -
--

CREATE INDEX idx_scribe_messages_session ON scribe.messages USING btree (session_id);


--
-- Name: idx_scribe_messages_timestamp; Type: INDEX; Schema: scribe; Owner: -
--

CREATE INDEX idx_scribe_messages_timestamp ON scribe.messages USING btree ("timestamp");


--
-- Name: idx_scribe_messages_tsv; Type: INDEX; Schema: scribe; Owner: -
--

CREATE INDEX idx_scribe_messages_tsv ON scribe.messages USING gin (tsv);


--
-- Name: idx_test_chats_updated_at; Type: INDEX; Schema: test_app; Owner: -
--

CREATE INDEX idx_test_chats_updated_at ON test_app.chats USING btree (updated_at DESC);


--
-- Name: events events_chat_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.events
    ADD CONSTRAINT events_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES app.chats(id);


--
-- PostgreSQL database dump complete
--

\unrestrict I9GoJwT37IgqmHA1e3CWj8atcU1qANSa0iRHOTtWapGrYXscRQZtK04wkAqOvnM

