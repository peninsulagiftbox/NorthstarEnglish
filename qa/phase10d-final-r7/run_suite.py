#!/usr/bin/env python3
"""Run one integration suite in its own fresh R7 database container."""

import json
import shutil
import sys

from run import q, OUT, PRIVATE, ROOT

SUITES = {
    "normalization": "KnowledgeNormalizationIntegrationTest",
    "quiz_review": "QuizReviewIntegrationTest",
    "audio": "AudioIntegrationTest,AudioIntervalsTest",
    "quiz_atomic": "QuizAtomicIntegrationTest",
    "full": None,
    "full2": None,
    "full3": None,
    "full4": None,
    "full5": "!KnowledgeSourcesIntegrationTest",
    "full6": "KnowledgeSourcesIntegrationTest",
}

UPDATE_TABLES = ("study_resume", "user_setting", "command_receipt", "study_stage", "exercise_draft",
                 "review_item", "vocabulary_favorite", "reading_progress", "writing_draft",
                 "personal_recording", "practice_progress", "quiz_progress", "concept_review_card")
INSERT_TABLES = ("exercise_attempt", "learning_evidence", "study_event", "review_source", "reading_answer",
                 "writing_revision", "recording_observation", "quiz_run", "quiz_answer", "quiz_run_item",
                 "review_result", "attempt_knowledge", "concept_review_source", "concept_review_result")
KNOWLEDGE_TABLES = ("knowledge_concept", "knowledge_concept_revision", "knowledge_occurrence",
                    "exercise_sentence", "exercise_knowledge", "legacy_knowledge_link")
KNOWLEDGE_UPDATE_TABLES = ("knowledge_projection",)


def configure(case):
    assert case in SUITES
    q.OUT = OUT / ("suite_" + case)
    q.OUT.mkdir(exist_ok=True)
    q.PRIVATE = PRIVATE / ("suite_" + case)
    q.PRIVATE.mkdir(exist_ok=True)
    q.NAME = "northstar-qa-final-r7-suite-" + case.replace("_", "-") + "-20261104"
    q.API_PORT = {"normalization": 8210, "quiz_review": 8211, "audio": 8212, "quiz_atomic": 8213,
                  "full": 8215, "full2": 8220, "full3": 8221, "full4": 8222,
                  "full5": 8223, "full6": 8224}[case]
    q.WEB_PORT = 3196


def main(case, action):
    configure(case)
    if action == "create":
        shutil.copy2(OUT / "qa-r7-final-candidate.sha256", q.OUT / "qa-final-candidate-manifest.sha256")
        q.create()
        print(json.dumps(q.identity()))
    elif action == "test":
        env = q.env()
        if case == "audio" or case.startswith("full"):
            path = ROOT / ".local/phase10c1/audio/manifest.json"
            assert path.is_file()
            env["NORTHSTAR_AUDIO_FIXTURES"] = str(path)
        if case.startswith("full"):
            schema = q.SCHEMA
            grants = [f"REVOKE ALL PRIVILEGES ON `{schema}`.* FROM 'northstar_app'@'%'",
                      f"GRANT SELECT ON `{schema}`.* TO 'northstar_app'@'%'"]
            grants += [f"GRANT INSERT,UPDATE ON `{schema}`.`{table}` TO 'northstar_app'@'%'" for table in UPDATE_TABLES]
            grants += [f"GRANT INSERT ON `{schema}`.`{table}` TO 'northstar_app'@'%'" for table in INSERT_TABLES]
            grants += [f"GRANT INSERT ON `{schema}`.`{table}` TO 'northstar_app'@'%'" for table in KNOWLEDGE_TABLES]
            grants += [f"GRANT INSERT,UPDATE ON `{schema}`.`{table}` TO 'northstar_app'@'%'" for table in KNOWLEDGE_UPDATE_TABLES]
            q.sql("; ".join(grants) + ";", label="r7-" + case + "-app-grants")
            command = ["bash", ROOT / "apps/api/mvnw", "-f", ROOT / "apps/api/pom.xml", "test"]
            if SUITES[case]:
                command += ["-Dtest=" + SUITES[case]]
            result = q.run("r7-" + case, command, env=env, check=False, timeout=3600)
        else:
            result = q.run("r7-" + case, ["bash", q.SOURCE / "apps/api/mvnw", "-f",
                                          q.SOURCE / "apps/api/pom.xml", "test",
                                          "-Dtest=" + SUITES[case]], env=env, check=False, timeout=900)
        if result.returncode:
            raise RuntimeError(case + " failed; original log retained")
    else:
        raise ValueError(action)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
