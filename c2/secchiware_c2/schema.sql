DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS execution;
DROP INDEX IF EXISTS active_environments;
DROP TABLE IF EXISTS session;

CREATE TABLE session
(
	id_session INTEGER PRIMARY KEY,
	session_start TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
	session_end TEXT,
	env_ip TEXT NOT NULL,
	env_port INTEGER NOT NULL,
	env_platform TEXT NOT NULL,
	env_node TEXT NOT NULL,
	env_os_system TEXT NOT NULL,
	env_os_release TEXT NOT NULL,
	env_os_version TEXT NOT NULL,
	env_hw_machine TEXT NOT NULL,
	env_hw_processor TEXT NOT NULL,
	env_py_build_no TEXT NOT NULL,
	env_py_build_date TEXT NOT NULL,
	env_py_compiler TEXT NOT NULL,
	env_py_implementation TEXT NOT NULL,
	env_py_version TEXT NOT NULL
);

CREATE TABLE execution
(
	id_execution INTEGER PRIMARY KEY,
	fk_session INTEGER NOT NULL,
    timestamp_registered TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CONSTRAINT execution_session
        FOREIGN KEY (fk_session)
        REFERENCES session(id_session)
        ON DELETE CASCADE
);

CREATE TABLE report
(
	id_report INTEGER PRIMARY KEY,
	fk_execution INTEGER NOT NULL,
	test_name TEXT NOT NULL,
	test_description TEXT NOT NULL,
	timestamp_start TEXT NOT NULL,
	timestamp_end TEXT NOT NULL,
	result_code INTEGER NOT NULL,
	additional_info TEXT,
	CONSTRAINT report_execution
	    FOREIGN KEY (fk_execution)
	    REFERENCES execution(id_execution)
	    ON DELETE CASCADE
);

CREATE INDEX active_environments
ON session(env_ip, env_port)
WHERE session_end IS NULL;
            
